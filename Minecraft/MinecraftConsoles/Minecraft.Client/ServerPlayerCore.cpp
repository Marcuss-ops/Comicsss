#include "stdafx.h"
#include "ServerPlayer.h"
#include "ServerPlayerGameMode.h"
#include "ServerLevel.h"
#include "MinecraftServer.h"
#include "EntityTracker.h"
#include "PlayerConnection.h"
#include "Settings.h"
#include "PlayerList.h"
#include "MultiPlayerLevel.h"

#include "..\Minecraft.World\net.minecraft.network.packet.h"
#include "..\Minecraft.World\net.minecraft.world.damagesource.h"
#include "..\Minecraft.World\net.minecraft.world.inventory.h"
#include "..\Minecraft.World\net.minecraft.world.level.h"
#include "..\Minecraft.World\net.minecraft.world.level.storage.h"
#include "..\Minecraft.World\net.minecraft.world.level.dimension.h"
#include "..\Minecraft.World\net.minecraft.world.entity.projectile.h"
#include "..\Minecraft.World\net.minecraft.world.entity.h"
#include "..\Minecraft.World\net.minecraft.world.entity.animal.h"
#include "..\Minecraft.World\net.minecraft.world.item.h"
#include "..\Minecraft.World\net.minecraft.world.item.trading.h"
#include "..\Minecraft.World\net.minecraft.world.entity.item.h"
#include "..\Minecraft.World\net.minecraft.world.level.tile.entity.h"
#include "..\Minecraft.World\net.minecraft.world.scores.h"
#include "..\Minecraft.World\net.minecraft.world.scores.criteria.h"
#include "..\Minecraft.World\net.minecraft.stats.h"
#include "..\Minecraft.World\net.minecraft.locale.h"

#include "..\Minecraft.World\Pos.h"
#include "..\Minecraft.World\Dimension.h"
#include "..\Minecraft.World\Random.h"

#include "..\Minecraft.World\LevelChunk.h"
#include "LevelRenderer.h"


ServerPlayer::ServerPlayer(MinecraftServer *server, Level *level, const wstring& name, ServerPlayerGameMode *gameMode) : Player(level, name)
{
	// 4J - added initialisers
	connection = nullptr;
	lastMoveX = lastMoveZ = 0;
	spewTimer = 0;
	lastRecordedHealthAndAbsorption = FLT_MIN;
	lastSentHealth = -99999999;
	lastSentFood = -99999999;
	lastFoodSaturationZero = true;
	lastSentExp = -99999999;
	invulnerableTime = 20 * 3;
	containerCounter = 0;
	ignoreSlotUpdateHack = false;
	latency = 0;
	wonGame = false;
	m_enteredEndExitPortal = false;
	// lastCarried = ItemInstanceArray(5);
	lastActionTime = 0;

	viewDistance = server->getPlayers()->getViewDistance();

	//    gameMode->player = this;		// 4J - removed to avoid use of shared_from_this in ctor, now set up externally
	this->gameMode = gameMode;

	Pos *spawnPos = level->getSharedSpawnPos();
	int xx = spawnPos->x;
	int zz = spawnPos->z;
	int yy = spawnPos->y;
	delete spawnPos;

	if (!level->dimension->hasCeiling && level->getLevelData()->getGameType() != GameType::ADVENTURE)
	{
		level->isFindingSpawn = true;

		int radius = max(5, server->getSpawnProtectionRadius() - 6);

		// 4J added - do additional checking that we aren't putting the player in deep water. Give up after 20 or goes just
		// in case the spawnPos is somehow in a really bad spot and we would just lock here.
		int waterDepth = 0;
		int attemptCount = 0;
		int xx2, yy2, zz2;

		int minXZ = - (level->dimension->getXZSize() * 16 ) / 2;
		int maxXZ = (level->dimension->getXZSize() * 16 ) / 2 - 1;

		bool playerNear = false;
		do
		{
			// Also check that we aren't straying outside of the map
			do
			{
				xx2 = xx + random->nextInt(radius * 2) - radius;
				zz2 = zz + random->nextInt(radius * 2) - radius;
			} while ( ( xx2 > maxXZ ) || ( xx2 < minXZ ) || ( zz2 > maxXZ ) || ( zz2 < minXZ ) );
			yy2 = level->getTopSolidBlock(xx2, zz2);

			waterDepth = 0;
			if (yy2 > 0 && yy2 < level->getMaxBuildHeight())
			{
				int yw = yy2;
				while( ( yw < 128 ) &&
					(( level->getTile(xx2,yw,zz2) == Tile::water_Id ) ||
					( level->getTile(xx2,yw,zz2) == Tile::calmWater_Id )) )
				{
					yw++;
					waterDepth++;
				}
			}
			else
			{
				// Fallback to shared spawn Y if chunk query returned an invalid height.
				yy2 = yy;
			}
			attemptCount++;
			playerNear = ( level->getNearestPlayer(xx + 0.5, yy, zz + 0.5,3) != nullptr );
		} while ( ( waterDepth > 1 ) && (!playerNear) && ( attemptCount < 20 ) );
		xx = xx2;
		yy = yy2;
		zz = zz2;

		level->isFindingSpawn = false;
	}

	this->server = server;
	footSize = 0;

	heightOffset = 0;	// 4J - this height used to be set up after moveTo, but that ends up with the y value being incorrect as it depends on this offset
	this->moveTo(xx + 0.5, yy, zz + 0.5, 0, 0);

	// 4J Handled later
	//while (!level->getCubes(this, bb).empty())
	//{
	//	setPos(x, y + 1, z);
	//}

	// m_UUID = name;

	// 4J Added
	lastBrupSendTickCount = 0;
}

ServerPlayer::~ServerPlayer()
{
	// delete [] lastCarried.data;
}

// 4J added - add bits to a flag array that is passed in, to represent those entities which have small Ids, and are in our vector of entitiesToRemove.
// If there aren't any entities to be flagged, this function does nothing. If there *are* entities to be added, uses the removedFound as an input to
// determine if the flag array has already been initialised at all - if it has been, then just adds flags to it; if it hasn't, then memsets the output
// flag array and adds to it for this ServerPlayer.
void ServerPlayer::flagEntitiesToBeRemoved(unsigned int *flags, bool *removedFound)
{
	if( entitiesToRemove.empty() )
	{
		return;
	}
	if( ( *removedFound ) == false )
	{
		*removedFound = true;
		// before this left 192 bytes uninitialized!!!!!
        memset(flags, 0, (2048 / 32) * sizeof(unsigned int));
	}

	for(int index : entitiesToRemove)
	{
		if( index < 2048 )
		{
			unsigned int i = index / 32;
			unsigned int j = index % 32;
			unsigned int uiMask = 0x80000000 >> j;

			flags[i] |= uiMask;
		}
	}
}

void ServerPlayer::readAdditionalSaveData(CompoundTag *entityTag)
{
	Player::readAdditionalSaveData(entityTag);

	if (entityTag->contains(L"playerGameType"))
	{
		// 4J Stu - We do not want to change the game mode for the player, instead we let the server override it globally
		//if (MinecraftServer::getInstance()->getForceGameType())
		//{
		//	gameMode->setGameModeForPlayer(MinecraftServer::getInstance()->getDefaultGameType());
		//}
		//else
		//{
		//	gameMode->setGameModeForPlayer(GameType::byId(entityTag->getInt(L"playerGameType")));
		//}
	}

	GameRulesInstance *grs = gameMode->getGameRules();
	if (entityTag->contains(L"GameRules") && grs != nullptr)
	{
		byteArray ba = entityTag->getByteArray(L"GameRules");
		ByteArrayInputStream bais(ba);
		DataInputStream dis(&bais);
		grs->read(&dis);
		dis.close();
		bais.close();
		//delete [] ba.data;
	}
}

void ServerPlayer::addAdditonalSaveData(CompoundTag *entityTag)
{
	Player::addAdditonalSaveData(entityTag);

	GameRulesInstance *grs = gameMode->getGameRules();
	if (grs != nullptr)
	{
		ByteArrayOutputStream baos;
		DataOutputStream dos(&baos);
		grs->write(&dos);
		entityTag->putByteArray(L"GameRules", baos.buf);
		baos.buf.data = nullptr;
		dos.close();
		baos.close();
	}

	// 4J Stu - We do not want to change the game mode for the player, instead we let the server override it globally
	//entityTag->putInt(L"playerGameType", gameMode->getGameModeForPlayer()->getId());
}

void ServerPlayer::giveExperienceLevels(int amount)
{
	Player::giveExperienceLevels(amount);
	lastSentExp = -1;
}

void ServerPlayer::initMenu()
{
	containerMenu->addSlotListener(this);
}

void ServerPlayer::setDefaultHeadHeight()
{
	heightOffset = 0;
}

float ServerPlayer::getHeadHeight()
{
	return 1.62f;
}

void ServerPlayer::tick()
{
	gameMode->tick();

	if (invulnerableTime > 0) invulnerableTime--;
	containerMenu->broadcastChanges();

	// 4J-JEV, hook for Durango event 'EnteredNewBiome'.
	Biome *newBiome = level->getBiome(x,z);
	if (newBiome != currentBiome)
	{
		awardStat(
			GenericStats::enteredBiome(newBiome->id),
			GenericStats::param_enteredBiome(newBiome->id)
			);
		currentBiome = newBiome;
	}

	if (!level->isClientSide)
	{
		if (!containerMenu->stillValid(dynamic_pointer_cast<Player>(shared_from_this())))
		{
			closeContainer();
			containerMenu = inventoryMenu;
		}
	}

	flushEntitiesToRemove();
}

// 4J Stu - Split out here so that we can call this from other places
void ServerPlayer::flushEntitiesToRemove()
{
	while (!entitiesToRemove.empty())
	{
		int sz = entitiesToRemove.size();
		int amount = min(sz, RemoveEntitiesPacket::MAX_PER_PACKET);
		intArray ids(amount);
		int pos = 0;

        auto it = entitiesToRemove.begin();
        while (it != entitiesToRemove.end() && pos < amount)
		{
			ids[pos++] = *it;
			it = entitiesToRemove.erase(it);
		}

		connection->send(std::make_shared<RemoveEntitiesPacket>(ids));
	}
}

// 4J - have split doTick into 3 bits, so that we can call the doChunkSendingTick separately, but still do the equivalent of what calling a full doTick used to do, by calling this method
void ServerPlayer::doTick(bool sendChunks, bool dontDelayChunks/*=false*/, bool ignorePortal/*=false*/)
{
	m_ignorePortal = ignorePortal;
	if( sendChunks )
	{
		updateFrameTick();
	}
	doTickA();
	if( sendChunks )
	{
		doChunkSendingTick(dontDelayChunks);
	}
	doTickB();
	m_ignorePortal = false;
}

void ServerPlayer::doTickA()
{
	Player::tick();

	for (unsigned int i = 0; i < inventory->getContainerSize(); i++)
	{
		shared_ptr<ItemInstance> ie = inventory->getItem(i);
		if (ie != nullptr)
		{
			// 4J - removed condition. These were getting lower priority than tile update packets etc. on the slow outbound queue, and so were extremely slow to send sometimes,
			// particularly at the start of a game. They don't typically seem to be massive and shouldn't be send when there isn't actually any updating to do.
			if (Item::items[ie->id]->isComplex() ) // && connection->countDelayedPackets() <= 2)
			{
				shared_ptr<Packet> packet = (dynamic_cast<ComplexItem *>(Item::items[ie->id])->getUpdatePacket(ie, level, dynamic_pointer_cast<Player>( shared_from_this() ) ) );
				if (packet != nullptr)
				{
					connection->send(packet);
				}
			}
		}
	}
}

// 4J - split off the chunk sending bit of the tick here from ::doTick so we can do this exactly once per player per server tick
void ServerPlayer::doChunkSendingTick(bool dontDelayChunks)
{
	//	printf("[%d] %s: sendChunks: %d, empty: %d\n",tickCount, connection->getNetworkPlayer()->GetUID().getOnlineID(),sendChunks,chunksToSend.empty());
	if (!chunksToSend.empty())
	{
		ChunkPos nearest = chunksToSend.front();
		bool nearestValid = false;

		// 4J - reinstated and optimised some code that was commented out in the original, to make sure that we always
		// send the nearest chunk to the player. The original uses the bukkit sorting thing to try and avoid doing this, but
		// the player can quickly wander away from the centre of the spiral of chunks that that method creates, long before transmission
		// of them is complete.
		double dist = DBL_MAX;
		for(ChunkPos chunk : chunksToSend)
		{
			if( level->isChunkFinalised(chunk.x, chunk.z) )
			{
				double newDist = chunk.distanceToSqr(x, z);
				if ( (!nearestValid) || (newDist < dist) )
				{
					nearest = chunk;
					dist = chunk.distanceToSqr(x, z);
					nearestValid = true;
				}
			}
		}

		//        if (nearest != nullptr)		// 4J - removed as we don't have references here
		if( nearestValid )
		{
			bool okToSend = false;

			//                if (dist < 32 * 32) okToSend = true;
			if( connection->isLocal() )
			{
				if( !connection->done ) okToSend = true;
			}
			else
			{
				bool canSendToPlayer = MinecraftServer::chunkPacketManagement_CanSendTo(connection->getNetworkPlayer());

//				app.DebugPrintf(">>> %d\n", canSendToPlayer);
//				if( connection->getNetworkPlayer() )
//				{
//					app.DebugPrintf("%d: canSendToPlayer %d, countDelayedPackets %d GetSendQueueSizeBytes %d done: %d\n",
//						connection->getNetworkPlayer()->GetSmallId(),
//						canSendToPlayer, connection->countDelayedPackets(),
//						g_NetworkManager.GetHostPlayer()->GetSendQueueSizeBytes( nullptr, true ),
//						connection->done);
//				}

#ifdef MINECRAFT_SERVER_BUILD
				if (dontDelayChunks || (canSendToPlayer && !connection->done))
#else
				if( dontDelayChunks ||
					(canSendToPlayer &&
#ifdef _XBOX_ONE
					// The network manager on xbox one doesn't currently split data into slow & fast queues - since we can only measure
					// both together then bytes provides a better metric than count of data items to determine if we should avoid queueing too much up
					(g_NetworkManager.GetHostPlayer()->GetSendQueueSizeBytes( nullptr, true ) < 8192 )&&
#elif defined _XBOX
					(g_NetworkManager.GetHostPlayer()->GetSendQueueSizeMessages( nullptr, true ) < 4 )&&
#else
					(connection->countDelayedPackets() < 4 )&&
					(g_NetworkManager.GetHostPlayer()->GetSendQueueSizeMessages( nullptr, true ) < 4 )&&
#endif
					//(tickCount - lastBrupSendTickCount) > (connection->getNetworkPlayer()->GetCurrentRtt()>>4) &&
					!connection->done) )
#endif
                {
                    lastBrupSendTickCount = tickCount;
                    okToSend = true;
                    MinecraftServer::chunkPacketManagement_DidSendTo(connection->getNetworkPlayer());

                    //					static unordered_map<wstring,int64_t> mapLastTime;
                    //					int64_t thisTime = System::currentTimeMillis();
                    //					int64_t lastTime = mapLastTime[connection->getNetworkPlayer()->GetUID().toString()];
                    //					app.DebugPrintf(" - OK to send (%d ms since last)\n", thisTime - lastTime);
                    //					mapLastTime[connection->getNetworkPlayer()->GetUID().toString()] = thisTime;
                }
                else
                {
                    //					app.DebugPrintf(" - <NOT OK>\n");
                }
			}

			if (okToSend)
			{
				ServerLevel *level = server->getLevel(this->level->dimension->id);
				int flagIndex = getFlagIndexForChunk(nearest,this->level->dimension->id);
				chunksToSend.remove(nearest);

				bool chunkDataSent = false;

				// Don't send the chunk to the local machine - the chunks there are mapped directly to the server chunks. We could potentially stop this process earlier on by not adding
				// to the chunksToSend list, but that would stop the tile entities being broadcast too
				if( !connection->isLocal() )  // force here to disable sharing of data
				{
					// Don't send the chunk if we've set a flag to say that we've already sent it to this machine. This stops two things
					// (1) Sending a chunk to multiple players doing split screen on one machine
					// (2) Sending a chunk that we've already sent as the player moves around. The original version of the game resends these, since it maintains
					//     a region of active chunks round each player in the "infinite" world, but in our finite world, we don't ever request that chunks be
					//     unloaded on the client and so just gradually build up more and more of the finite set of chunks as the player moves
					if( !g_NetworkManager.SystemFlagGet(connection->getNetworkPlayer(),flagIndex) )
					{
						PIXBeginNamedEvent(0,"Creation BRUP for sending\n");
						int64_t before = System::currentTimeMillis();
						const auto packet = std::make_shared<BlockRegionUpdatePacket>(nearest.x * 16, 0, nearest.z * 16, 16, Level::maxBuildHeight, 16, level);
						int64_t after = System::currentTimeMillis();
//						app.DebugPrintf(">>><<< %d ms\n",after-before);
						PIXEndNamedEvent();
						if( dontDelayChunks ) packet->shouldDelay = false;

						if( packet->shouldDelay == true )
						{
							// Other than the first packet we always want these initial chunks to be sent over
							// QNet at a lower priority
							connection->queueSend( packet );
						}
						else
						{
							connection->send( packet );
						}
						// Set flag to say we have send this block already to this system
						g_NetworkManager.SystemFlagSet(connection->getNetworkPlayer(),flagIndex);

						chunkDataSent = true;
					}
				}
				else
				{
					// For local connections, we'll need to copy the lighting data over from server to client at this point. This is to try and keep lighting as similar as possible to the java version,
					// where client & server are individually responsible for maintaining their lighting (since 1.2.3). This is really an alternative to sending the lighting data over the fake local
					// network connection at this point.

					MultiPlayerLevel *clientLevel = Minecraft::GetInstance()->getLevel(level->dimension->id);
					if( clientLevel )
					{
						LevelChunk *lc = clientLevel->getChunk( nearest.x, nearest.z );
						lc->reSyncLighting();
						lc->recalcHeightmapOnly();
						clientLevel->setTilesDirty(nearest.x * 16 + 1, 1, nearest.z * 16 + 1,
							nearest.x * 16 + 14, Level::maxBuildHeight - 2, nearest.z * 16 + 14 );
					}
				}
				// Don't send TileEntity data until we have sent the block data
				if( connection->isLocal() || chunkDataSent)
				{
					vector<shared_ptr<TileEntity> > *tes = level->getTileEntitiesInRegion(nearest.x * 16, 0, nearest.z * 16, nearest.x * 16 + 16, Level::maxBuildHeight, nearest.z * 16 + 16);
					for (unsigned int i = 0; i < tes->size(); i++)
					{
						// 4J Stu - Added delay param to ensure that these arrive after the BRUPs from above
						// Fix for #9169 - ART : Sign text is replaced with the words Awaiting approval.
						broadcast(tes->at(i), !connection->isLocal() && !dontDelayChunks);
					}
					delete tes;
				}
			}
		}
	}
}

void ServerPlayer::doTickB()
{
#ifndef _CONTENT_PACKAGE
	// check if there's a debug dimension change requested
	//if(app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad())&(1L<<eDebugSetting_GoToNether))
	//{
	//	if(level->dimension->id == 0 )
	//	{
	//		isInsidePortal=true;
	//		portalTime=1;
	//	}
	//	unsigned int uiVal=app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad());
	//	app.SetGameSettingsDebugMask(ProfileManager.GetPrimaryPad(),uiVal&~(1L<<eDebugSetting_GoToNether));
	//}
	// 	else if (app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad())&(1L<<eDebugSetting_GoToEnd))
	// 	{
	// 		if(level->dimension->id == 0 )
	// 		{
	// 			server->players->toggleDimension( dynamic_pointer_cast<ServerPlayer>( shared_from_this() ), 1 );
	// 		}
	// 		unsigned int uiVal=app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad());
	// 		app.SetGameSettingsDebugMask(ProfileManager.GetPrimaryPad(),uiVal&~(1L<<eDebugSetting_GoToEnd));
	// 	}
	//else
		if (app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad())&(1L<<eDebugSetting_GoToOverworld))
	{
		if(level->dimension->id != 0 )
		{
			isInsidePortal=true;
			portalTime=1;
		}
		unsigned int uiVal=app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad());
		app.SetGameSettingsDebugMask(ProfileManager.GetPrimaryPad(),uiVal&~(1L<<eDebugSetting_GoToOverworld));
	}
#endif

	if (getHealth() != lastSentHealth || lastSentFood != foodData.getFoodLevel() || ((foodData.getSaturationLevel() == 0) != lastFoodSaturationZero))
	{
		// 4J Stu - Added m_lastDamageSource for telemetry
		connection->send(std::make_shared<SetHealthPacket>(getHealth(), foodData.getFoodLevel(), foodData.getSaturationLevel(), m_lastDamageSource));
		lastSentHealth = getHealth();
		lastSentFood = foodData.getFoodLevel();
		lastFoodSaturationZero = foodData.getSaturationLevel() == 0;
	}

	if (getHealth() + getAbsorptionAmount() != lastRecordedHealthAndAbsorption)
	{
		lastRecordedHealthAndAbsorption = getHealth() + getAbsorptionAmount();

		vector<Objective *> *objectives = getScoreboard()->findObjectiveFor(ObjectiveCriteria::HEALTH);
		if(objectives)
		{
			vector< shared_ptr<Player> > players = vector< shared_ptr<Player> >();
			players.push_back(dynamic_pointer_cast<Player>(shared_from_this()));

			for (Objective *objective : *objectives)
			{
				getScoreboard()->getPlayerScore(getAName(), objective)->updateFor(&players);
			}
			delete objectives;
		}
	}

	if (totalExperience != lastSentExp)
	{
		lastSentExp = totalExperience;
		connection->send(std::make_shared<SetExperiencePacket>(experienceProgress, totalExperience, experienceLevel));
	}

}

shared_ptr<ItemInstance> ServerPlayer::getCarried(int slot)
{
	if (slot == 0) return inventory->getSelected();
	return inventory->armor[slot - 1];
}

void ServerPlayer::changeDimension(int i)
{
	if(!connection->hasClientTickedOnce()) return;

	if (dimension == 1 && i == 1)
	{
		app.DebugPrintf("Start win game\n");
		awardStat(GenericStats::winGame(), GenericStats::param_winGame());

		// All players on the same system as this player should also be removed from the game while the Win screen is shown
		INetworkPlayer *thisPlayer = connection->getNetworkPlayer();

		if(!wonGame)
		{
			level->removeEntity(shared_from_this());
			wonGame = true;
			m_enteredEndExitPortal = true; // We only flag this for the player in the portal
			connection->send(std::make_shared<GameEventPacket>(GameEventPacket::WIN_GAME, thisPlayer->GetUserIndex()));
			app.DebugPrintf("Sending packet to %d\n", thisPlayer->GetUserIndex());
		}
		if(thisPlayer)
		{
			for(auto& servPlayer : MinecraftServer::getInstance()->getPlayers()->players)
			{
				INetworkPlayer *checkPlayer = servPlayer->connection->getNetworkPlayer();
				if(thisPlayer != checkPlayer && checkPlayer != nullptr && thisPlayer->IsSameSystem( checkPlayer ) && !servPlayer->wonGame )
				{
					servPlayer->wonGame = true;
					servPlayer->connection->send(std::make_shared<GameEventPacket>(GameEventPacket::WIN_GAME, thisPlayer->GetUserIndex()));
					app.DebugPrintf("Sending packet to %d\n", thisPlayer->GetUserIndex());
				}
			}
		}
		app.DebugPrintf("End win game\n");
	}
	else
	{
		if (dimension == 0 && i == 1)
		{
			awardStat(GenericStats::theEnd(), GenericStats::param_theEnd());

			Pos *pos = server->getLevel(i)->getDimensionSpecificSpawn();
			if (pos != nullptr)
			{
				connection->teleport(pos->x, pos->y, pos->z, 0, 0);
				delete pos;
			}

			i = 1;
		}
		else
		{
			// 4J: Removed on the advice of the mighty King of Achievments (JV)
			// awardStat(GenericStats::portal(), GenericStats::param_portal());
		}
		server->getPlayers()->toggleDimension( dynamic_pointer_cast<ServerPlayer>(shared_from_this()), i);
		lastSentExp = -1;
		lastSentHealth = -1;
		lastSentFood = -1;
	}
}

void ServerPlayer::take(shared_ptr<Entity> e, int orgCount)
{
	Player::take(e, orgCount);
	containerMenu->broadcastChanges();
}

void ServerPlayer::ride(shared_ptr<Entity> e)
{
	Player::ride(e);
	connection->send(std::make_shared<SetEntityLinkPacket>(SetEntityLinkPacket::RIDING, shared_from_this(), riding));

	// 4J Removed this - The act of riding will be handled on the client and will change the position
	// of the player. If we also teleport it then we can end up with a repeating movements, e.g. bouncing
	// up and down after exiting a boat due to slight differences in position on the client and server
	//connection->teleport(x, y, z, yRot, xRot);
}

void ServerPlayer::checkFallDamage(double ya, bool onGround)
{
}

void ServerPlayer::doCheckFallDamage(double ya, bool onGround)
{
	Player::checkFallDamage(ya, onGround);
}

void ServerPlayer::setPlayerInput(float xxa, float yya, bool jumping, bool sneaking)
{
	if(riding != nullptr)
	{
		if (xxa >= -1 && xxa <= 1) this->xxa = xxa;
		if (yya >= -1 && yya <= 1) this->yya = yya;
		this->jumping = jumping;
		this->setSneaking(sneaking);
	}
}

void ServerPlayer::disconnect()
{
	if (rider.lock() != nullptr) rider.lock()->ride(shared_from_this() );
	if (m_isSleeping)
	{
		stopSleepInBed(true, false, false);
	}
}

void ServerPlayer::resetSentInfo()
{
	lastSentHealth = -99999999;
}
