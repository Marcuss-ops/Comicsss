#include "stdafx.h"
#include "MinecraftServer.h"
#include "DerivedServerLevel.h"
#include "ServerLevel.h"
#include "ServerLevelListener.h"
#include "PlayerList.h"
#include "ServerConnection.h"
#include "ProgressRenderer.h"
#include "Settings.h"
#include "ServerChunkCache.h"
#include "PlayerChunkMap.h"
#include "..\Minecraft.World\net.minecraft.world.level.h"
#include "..\Minecraft.World\net.minecraft.world.level.dimension.h"
#include "..\Minecraft.World\net.minecraft.world.level.storage.h"
#include "..\Minecraft.World\net.minecraft.world.h"
#include "..\Minecraft.World\BiomeSource.h"
#include "..\Minecraft.World\System.h"
#include "..\Minecraft.World\StringHelpers.h"
#include "..\Minecraft.World\ThreadName.h"
#include "..\Minecraft.World\ConsoleSaveFileOriginal.h"
#ifdef SPLIT_SAVES
#include "..\Minecraft.World\ConsoleSaveFileSplit.h"
#endif
#ifdef _WINDOWS64
#include "Windows64\Network\WinsockNetLayer.h"
#endif
#include "..\Minecraft.World\Socket.h"
#include "..\Minecraft.World\IntCache.h"
#include "..\Minecraft.World\AABB.h"
#include "..\Minecraft.World\Vec3.h"
#include "..\Minecraft.World\compression.h"
#include "..\Minecraft.World\Tile.h"
#include "..\Minecraft.World\CompressedTileStorage.h"
#include "..\Minecraft.World\SparseLightStorage.h"
#include "..\Minecraft.World\SparseDataStorage.h"
#include "PS3\PS3Extras\ShutdownManager.h"
// Mod hooks
#include "..\Minecraft.Server\Console\Mods\ModIntegration.h"
#include "..\Minecraft.Server\Console\Mods\ModManager.h"
#include "ServerChunkCache.h"
#include "ServerConsoleCommandsHelpers.h"

bool MinecraftServer::initServer(int64_t seed, NetworkGameInitData *initData, DWORD initSettings, bool findSeed)
{
	printf("[initServer] ENTRY, seed=%lld, initData=%p\n", seed, initData); fflush(stdout);
	// 4J - removed
#if 0
	commands = new ConsoleCommands(this);

	Thread t = new Thread() {
		public void run() {
			BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
			String line = null;
			try {
				while (!stopped && running && (line = br.readLine()) != null) {
					handleConsoleInput(line, MinecraftServer.this);
				}
			} catch (IOException e) {
				e.printStackTrace();
			}
		}
	};
	t.setDaemon(true);
	t.start();


	LogConfigurator.initLogger();
	logger.info("Starting minecraft server version " + VERSION);

	if (Runtime.getRuntime().maxMemory() / 1024 / 1024 < 512) {
		logger.warning("**** NOT ENOUGH RAM!");
		logger.warning("To start the server with more ram, launch it as \"java -Xmx1024M -Xms1024M -jar minecraft_server.jar\"");
	}

	logger.info("Loading properties");
#endif
	settings = new Settings(new File(L"server.properties"));
	printf("[initServer] Settings loaded from server.properties\n"); fflush(stdout);
	// Dedicated-only: spawn-protection radius in blocks; 0 disables protection.
	printf("[initServer] Reading spawn-protection\n"); fflush(stdout);
	m_spawnProtectionRadius = GetDedicatedServerInt(settings, L"spawn-protection", 0);
	if (m_spawnProtectionRadius < 0) m_spawnProtectionRadius = 0;
	if (m_spawnProtectionRadius > 256) m_spawnProtectionRadius = 256;

	printf("[initServer] Setting game host options\n"); fflush(stdout);
	app.SetGameHostOption(eGameHostOption_Difficulty, GetDedicatedServerInt(settings, L"difficulty", app.GetGameHostOption(eGameHostOption_Difficulty)));
	app.SetGameHostOption(eGameHostOption_GameType, GetDedicatedServerInt(settings, L"gamemode", app.GetGameHostOption(eGameHostOption_GameType)));
	app.SetGameHostOption(eGameHostOption_Structures, GetDedicatedServerBool(settings, L"generate-structures", app.GetGameHostOption(eGameHostOption_Structures) > 0) ? 1 : 0);
	app.SetGameHostOption(eGameHostOption_BonusChest, GetDedicatedServerBool(settings, L"bonus-chest", app.GetGameHostOption(eGameHostOption_BonusChest) > 0) ? 1 : 0);
	app.SetGameHostOption(eGameHostOption_PvP, GetDedicatedServerBool(settings, L"pvp", app.GetGameHostOption(eGameHostOption_PvP) > 0) ? 1 : 0);
	app.SetGameHostOption(eGameHostOption_TrustPlayers, GetDedicatedServerBool(settings, L"trust-players", app.GetGameHostOption(eGameHostOption_TrustPlayers) > 0) ? 1 : 0);
	app.SetGameHostOption(eGameHostOption_FireSpreads, GetDedicatedServerBool(settings, L"fire-spreads", app.GetGameHostOption(eGameHostOption_FireSpreads) > 0) ? 1 : 0);
	app.SetGameHostOption(eGameHostOption_TNT, GetDedicatedServerBool(settings, L"tnt", app.GetGameHostOption(eGameHostOption_TNT) > 0) ? 1 : 0);
	printf("[initServer] Game host options set\n"); fflush(stdout);

	app.DebugPrintf("\n*** SERVER SETTINGS ***\n");
	app.DebugPrintf("ServerSettings: host-friends-only is %s\n",(app.GetGameHostOption(eGameHostOption_FriendsOfFriends)>0)?"on":"off");
	app.DebugPrintf("ServerSettings: game-type is %s\n",(app.GetGameHostOption(eGameHostOption_GameType)==0)?"Survival Mode":"Creative Mode");
	app.DebugPrintf("ServerSettings: pvp is %s\n",(app.GetGameHostOption(eGameHostOption_PvP)>0)?"on":"off");
	app.DebugPrintf("ServerSettings: fire spreads is %s\n",(app.GetGameHostOption(eGameHostOption_FireSpreads)>0)?"on":"off");
	app.DebugPrintf("ServerSettings: tnt explodes is %s\n",(app.GetGameHostOption(eGameHostOption_TNT)>0)?"on":"off");
	app.DebugPrintf("ServerSettings: spawn protection radius is %d\n", m_spawnProtectionRadius);
	app.DebugPrintf("\n");
	printf("[initServer] After DebugPrintf, about to call setAnimals\n"); fflush(stdout);

	// TODO 4J Stu - Init a load of settings based on data passed as params
	//settings->setBooleanAndSave( L"host-friends-only", (app.GetGameHostOption(eGameHostOption_FriendsOfFriends)>0) );

	// 4J - Unused
	//localIp = settings->getString(L"server-ip", L"");
	//onlineMode = settings->getBoolean(L"online-mode", true);
	//motd = settings->getString(L"motd", L"A Minecraft Server");
	//motd.replace('', '$');

	setAnimals(GetDedicatedServerBool(settings, L"spawn-animals", true));
	setNpcsEnabled(GetDedicatedServerBool(settings, L"spawn-npcs", true));
	setPvpAllowed(app.GetGameHostOption( eGameHostOption_PvP )>0?true:false);

	// 4J Stu - We should never have hacked clients flying when they shouldn't be like the PC version, so enable flying always
	// Fix for #46612 - TU5: Code: Multiplayer: A client can be banned for flying when accidentaly being blown by dynamite
	setFlightAllowed(GetDedicatedServerBool(settings, L"allow-flight", true));
	printf("[initServer] After setFlightAllowed, about to create ServerConnection\n"); fflush(stdout);

	// 4J Stu - Enabling flight to stop it kicking us when we use it
#if (defined _DEBUG_MENUS_ENABLED && defined _DEBUG)
	setFlightAllowed(true);
#endif

#if 1
	printf("[initServer] Creating ServerConnection\n"); fflush(stdout);
	connection = new ServerConnection(this);
	printf("[initServer] ServerConnection created, calling Socket::Initialise\n"); fflush(stdout);
	Socket::Initialise(connection);	// 4J - added
	printf("[initServer] Socket::Initialise done\n"); fflush(stdout);
#else
	// 4J - removed
	InetAddress localAddress = null;
	if (localIp.length() > 0) localAddress = InetAddress.getByName(localIp);
	port = settings.getInt("server-port", DEFAULT_MINECRAFT_PORT);

	logger.info("Starting Minecraft server on " + (localIp.length() == 0 ? "*" : localIp) + ":" + port);
	try {
		connection = new ServerConnection(this, localAddress, port);
	} catch (IOException e) {
		logger.warning("**** FAILED TO BIND TO PORT!");
		logger.log(Level.WARNING, "The exception was: " + e.toString());
		logger.warning("Perhaps a server is already running on that port?");
		return false;
	}

	if (!onlineMode) {
		logger.warning("**** SERVER IS RUNNING IN OFFLINE/INSECURE MODE!");
		logger.warning("The server will make no attempt to authenticate usernames. Beware.");
		logger.warning("While this makes the game possible to play without internet access, it also opens up the ability for hackers to connect with any username they choose.");
		logger.warning("To change this, set \"online-mode\" to \"true\" in the server.settings file.");
	}
#endif
	printf("[initServer] Calling setPlayers\n"); fflush(stdout);
	setPlayers(new PlayerList(this));
	printf("[initServer] setPlayers done\n"); fflush(stdout);
#ifdef _WINDOWS64
	{
		int maxP = getPlayerList()->getMaxPlayers();
		WinsockNetLayer::UpdateAdvertiseMaxPlayers((BYTE)(maxP > 255 ? 255 : maxP));
		printf("[initServer] UpdateAdvertiseMaxPlayers done, maxP=%d\n", maxP); fflush(stdout);
	}
#endif

	// 4J-JEV: Need to wait for levelGenerationOptions to load.
	printf("[initServer] Checking levelGenerationOptions\n"); fflush(stdout);

	while ( app.getLevelGenerationOptions() != nullptr && !app.getLevelGenerationOptions()->hasLoadedData() )
		Sleep(1);

	printf("[initServer] Past levelGenerationOptions wait\n"); fflush(stdout);
	if ( app.getLevelGenerationOptions() != nullptr && !app.getLevelGenerationOptions()->ready() )
	{
		// TODO: Stop loading, add error message.
	}

	int64_t levelNanoTime = System::nanoTime();

        wstring levelName = (initData && !initData->levelName.empty()) ? initData->levelName : GetDedicatedServerString(settings, L"level-name", L"world");
		wstring levelTypeString;
	printf("[initServer] levelName=%ls\n", levelName.c_str()); fflush(stdout);

	bool gameRuleUseFlatWorld = false;
	if(app.getLevelGenerationOptions() != nullptr)
	{
		gameRuleUseFlatWorld = app.getLevelGenerationOptions()->getuseFlatWorld();
	}
	printf("[initServer] gameRuleUseFlatWorld=%d, LevelType host option=%d\n", gameRuleUseFlatWorld, app.GetGameHostOption(eGameHostOption_LevelType)); fflush(stdout);
	wstring levelTypeStringFromProps = GetDedicatedServerString(settings, L"level-type", L"default");
	if(gameRuleUseFlatWorld || app.GetGameHostOption(eGameHostOption_LevelType)>0 || levelTypeStringFromProps == L"flat")
	{
		levelTypeString = L"flat";
	}
	else
	{
		levelTypeString = L"default";
	}
	printf("[initServer] levelTypeString=%ls\n", levelTypeString.c_str()); fflush(stdout);

	LevelType *pLevelType = LevelType::getLevelType(levelTypeString);
	printf("[initServer] pLevelType=%p\n", pLevelType); fflush(stdout);
	if (pLevelType == nullptr)
	{
		pLevelType = LevelType::lvl_normal;
	}

	printf("[initServer] Getting progressRenderer\n"); fflush(stdout);
	ProgressRenderer *mcprogress = Minecraft::GetInstance()->progressRenderer;
	printf("[initServer] progressRenderer=%p, calling progressStart\n", mcprogress); fflush(stdout);
	mcprogress->progressStart(IDS_PROGRESS_INITIALISING_SERVER);
	printf("[initServer] progressStart done\n"); fflush(stdout);

	if( findSeed )
	{
#ifdef __PSVITA__
		seed = BiomeSource::findSeed(pLevelType, &running);
#else
		seed = BiomeSource::findSeed(pLevelType);
#endif
	}

	setMaxBuildHeight(GetDedicatedServerInt(settings, L"max-build-height", Level::maxBuildHeight));
	setMaxBuildHeight(((getMaxBuildHeight() + 8) / 16) * 16);
	setMaxBuildHeight(Mth::clamp(getMaxBuildHeight(), 64, Level::maxBuildHeight));
	printf("[initServer] setMaxBuildHeight done, maxBuildHeight=%d\n", maxBuildHeight); fflush(stdout);
	//settings->setProperty(L"max-build-height", maxBuildHeight);

#if 0
	wstring levelSeedString = settings->getString(L"level-seed", L"");
	int64_t levelSeed = (new Random())->nextLong();
	if (levelSeedString.length() > 0)
	{
		long newSeed = _from_string<int64_t>(levelSeedString);
		if (newSeed != 0) {
			levelSeed = newSeed;
		}
	}
#endif
	//        logger.info("Preparing level \"" + levelName + "\"");
	printf("[initServer] About to call loadLevel with levelName=%ls, seed=%lld, pLevelType=%p\n", levelName.c_str(), seed, pLevelType); fflush(stdout);
	// Prevent the background tick path from touching partially constructed world state.
	std::lock_guard<std::recursive_mutex> startupLock(g_serverTickMutex);
	m_bLoaded = loadLevel(new McRegionLevelStorageSource(File(L".")), levelName, seed, pLevelType, initData);
	printf("[initServer] loadLevel returned %d\n", m_bLoaded); fflush(stdout);
	//        logger.info("Done (" + (System.nanoTime() - levelNanoTime) + "ns)! For help, type \"help\" or \"?\"");

	// 4J delete passed in save data now - this is only required for the tutorial which is loaded by passing data directly in rather than using the storage manager
	if( initData->saveData )
	{
		delete initData->saveData->data;
		initData->saveData->data = 0;
		initData->saveData->fileSize = 0;
	}

	// ── MOD: Initialize mod system ──
	if (m_bLoaded && levels.length > 0 && levels[0] != nullptr)
	{
		Level* level = static_cast<Level*>(levels[0]);
		ServerChunkCache* chunkCache = levels[0]->cache;

		// ── MOD: Initialize mod system (after level load)
		// Read mod config from server.properties with sensible defaults
		ServerRuntime::Mods::ModConfig modConfig;
		modConfig.cacheDir = GetDedicatedServerStringA(settings, L"mod-cache-dir", "mods/cache");
		modConfig.maxCachedChunks = GetDedicatedServerInt(settings, L"mod-max-cached-chunks", 500);
		modConfig.enableEventFlushing = GetDedicatedServerBool(settings, L"mod-event-flushing", true);
		modConfig.enableProfiling = GetDedicatedServerBool(settings, L"mod-profiling", false);
		modConfig.slowTickThresholdMs = GetDedicatedServerInt(settings, L"mod-slow-tick-ms", 100);
		ServerRuntime::Mods::ModManager::initialize(modConfig, level, levels[0], chunkCache, this);
		printf("[ModManager] Initialized: cache=%s maxChunks=%d profiling=%s\n",
			modConfig.cacheDir.c_str(), modConfig.maxCachedChunks,
			modConfig.enableProfiling ? "on" : "off");
		fflush(stdout);
	}
	// ── END MOD ──

	g_NetworkManager.ServerReady();	// 4J added
	return m_bLoaded;

}

// 4J - added - extra thread to post processing on separate thread during level creation
int MinecraftServer::runPostUpdate(void* lpParam)
{
	ShutdownManager::HasStarted(ShutdownManager::ePostProcessThread);

	MinecraftServer *server = static_cast<MinecraftServer *>(lpParam);
	Entity::useSmallIds();		// This thread can end up spawning entities as resources
	IntCache::CreateNewThreadStorage();
	AABB::CreateNewThreadStorage();
	Vec3::CreateNewThreadStorage();
	Compression::UseDefaultThreadStorage();
	Level::enableLightingCache();
	Tile::CreateNewThreadStorage();

	// Update lights for both levels until we are signalled to terminate
	do
	{
		EnterCriticalSection(&server->m_postProcessCS);
		if( server->m_postProcessRequests.size() )
		{
			MinecraftServer::postProcessRequest request = server->m_postProcessRequests.back();
			server->m_postProcessRequests.pop_back();
			LeaveCriticalSection(&server->m_postProcessCS);
			static int count = 0;
			PIXBeginNamedEvent(0,"Post processing %d ", (count++)%8);
			request.chunkSource->postProcess(request.chunkSource, request.x, request.z );
			PIXEndNamedEvent();
		}
		else
		{
			LeaveCriticalSection(&server->m_postProcessCS);
		}
		Sleep(1);
	} while (!server->m_postUpdateTerminate && ShutdownManager::ShouldRun(ShutdownManager::ePostProcessThread));
	//#ifndef __PS3__
	// One final pass through updates to make sure we're done
	EnterCriticalSection(&server->m_postProcessCS);
	int maxRequests = server->m_postProcessRequests.size();
	while(server->m_postProcessRequests.size() && ShutdownManager::ShouldRun(ShutdownManager::ePostProcessThread) )
	{
		MinecraftServer::postProcessRequest request = server->m_postProcessRequests.back();
		server->m_postProcessRequests.pop_back();
		LeaveCriticalSection(&server->m_postProcessCS);
		request.chunkSource->postProcess(request.chunkSource, request.x, request.z );
#ifdef __PS3__
#ifndef _CONTENT_PACKAGE
		if((server->m_postProcessRequests.size() % 10) == 0)
			printf("processing request %00d\n", server->m_postProcessRequests.size());
#endif
		Sleep(1);
#endif
		EnterCriticalSection(&server->m_postProcessCS);
	}
	LeaveCriticalSection(&server->m_postProcessCS);
	//#endif //__PS3__
	Tile::ReleaseThreadStorage();
	IntCache::ReleaseThreadStorage();
	AABB::ReleaseThreadStorage();
	Vec3::ReleaseThreadStorage();
	Level::destroyLightingCache();

	ShutdownManager::HasFinished(ShutdownManager::ePostProcessThread);

	return 0;
}

void	MinecraftServer::addPostProcessRequest(ChunkSource *chunkSource, int x, int z)
{
	EnterCriticalSection(&m_postProcessCS);
	m_postProcessRequests.push_back(MinecraftServer::postProcessRequest(x,z,chunkSource));
	LeaveCriticalSection(&m_postProcessCS);
}

void MinecraftServer::postProcessTerminate(ProgressRenderer *mcprogress)
{
	DWORD status = 0;

	EnterCriticalSection(&server->m_postProcessCS);
	size_t postProcessItemCount = server->m_postProcessRequests.size();
	LeaveCriticalSection(&server->m_postProcessCS);

	do
	{
		status = m_postUpdateThread->WaitForCompletion(50);
		if( status == WAIT_TIMEOUT )
		{
			EnterCriticalSection(&server->m_postProcessCS);
			size_t postProcessItemRemaining = server->m_postProcessRequests.size();
			LeaveCriticalSection(&server->m_postProcessCS);

			if( postProcessItemCount )
			{
				mcprogress->progressStagePercentage((postProcessItemCount - postProcessItemRemaining) * 100 / postProcessItemCount);
			}
			CompressedTileStorage::tick();
			SparseLightStorage::tick();
			SparseDataStorage::tick();
		}
	} while ( status == WAIT_TIMEOUT );
	delete m_postUpdateThread;
	m_postUpdateThread = nullptr;
	DeleteCriticalSection(&m_postProcessCS);
}

bool MinecraftServer::loadLevel(LevelStorageSource *storageSource, const wstring& name, int64_t levelSeed, LevelType *pLevelType, NetworkGameInitData *initData)
{
	printf("[loadLevel] ENTRY, name=%ls, seed=%lld, pLevelType=%p, initData=%p\n", name.c_str(), levelSeed, pLevelType, initData); fflush(stdout);
	//	4J - TODO - do with new save stuff
	//    if (storageSource->requiresConversion(name))
	//	{
	//		assert(false);
	//    }
	ProgressRenderer *mcprogress = Minecraft::GetInstance()->progressRenderer;
	printf("[loadLevel] Got progressRenderer=%p\n", mcprogress); fflush(stdout);

	// 4J TODO - free levels here if there are already some?
	printf("[loadLevel] Creating ServerLevelArray(3)\n"); fflush(stdout);
	levels = ServerLevelArray(3);
	printf("[loadLevel] ServerLevelArray created\n"); fflush(stdout);

	int gameTypeId = GetDedicatedServerInt(settings, L"gamemode", app.GetGameHostOption(eGameHostOption_GameType));//LevelSettings::GAMETYPE_SURVIVAL);
	printf("[loadLevel] gameTypeId=%d\n", gameTypeId); fflush(stdout);
	GameType *gameType = LevelSettings::validateGameType(gameTypeId);
	printf("[loadLevel] gameType=%p\n", gameType); fflush(stdout);
	app.DebugPrintf("Default game type: %d\n" , gameTypeId);

	printf("[loadLevel] Creating LevelSettings\n"); fflush(stdout);
	LevelSettings *levelSettings = new LevelSettings(levelSeed, gameType, app.GetGameHostOption(eGameHostOption_Structures)>0?true:false, isHardcore(), true, pLevelType, initData->xzSize, initData->hellScale);
	printf("[loadLevel] LevelSettings created=%p\n", levelSettings); fflush(stdout);
	if( app.GetGameHostOption(eGameHostOption_BonusChest ) ) levelSettings->enableStartingBonusItems();

	// 4J - temp - load existing level
	printf("[loadLevel] Creating storage, initData->saveData=%p\n", initData->saveData); fflush(stdout);
	shared_ptr<McRegionLevelStorage> storage = nullptr;
	bool levelChunksNeedConverted = false;
	if( initData->saveData != nullptr )
	{
		printf("[loadLevel] Loading from initData->saveData\n"); fflush(stdout);
		// We are loading a file from disk with the data passed in

#ifdef SPLIT_SAVES
		ConsoleSaveFileOriginal oldFormatSave( initData->saveData->saveName, initData->saveData->data, initData->saveData->fileSize, false, initData->savePlatform );
		ConsoleSaveFile* pSave = new ConsoleSaveFileSplit( &oldFormatSave );

		//ConsoleSaveFile* pSave = new ConsoleSaveFileSplit( initData->saveData->saveName, initData->saveData->data, initData->saveData->fileSize, false, initData->savePlatform );
#else
		ConsoleSaveFile* pSave = new ConsoleSaveFileOriginal( initData->saveData->saveName, initData->saveData->data, initData->saveData->fileSize, false, initData->savePlatform );
#endif
		if(pSave->isSaveEndianDifferent())
			levelChunksNeedConverted = true;
		pSave->ConvertToLocalPlatform(); // check if we need to convert this file from PS3->PS4

		storage = std::make_shared<McRegionLevelStorage>(pSave, File(L"."), name, true);
	}
	else
	{
		// We are loading a save from the storage manager
#ifdef SPLIT_SAVES
		bool bLevelGenBaseSave = false;
		LevelGenerationOptions *levelGen = app.getLevelGenerationOptions();
		if( levelGen != nullptr && levelGen->requiresBaseSave())
		{
			DWORD fileSize = 0;
			LPVOID pvSaveData = levelGen->getBaseSaveData(fileSize);
			if(pvSaveData && fileSize != 0) bLevelGenBaseSave = true;
		}
		ConsoleSaveFileSplit *newFormatSave = nullptr;
		if(bLevelGenBaseSave)
		{
			ConsoleSaveFileOriginal oldFormatSave( L"" );
			newFormatSave = new ConsoleSaveFileSplit( &oldFormatSave );
		}
		else
		{
			newFormatSave = new ConsoleSaveFileSplit( L"" );
		}

		storage = shared_ptr<McRegionLevelStorage>(new McRegionLevelStorage(newFormatSave, File(L"."), name, true));
#else
		ConsoleSaveFileOriginal* pSave = new ConsoleSaveFileOriginal(L"");

		pSave->ConvertToLocalPlatform();
		storage = std::make_shared<McRegionLevelStorage>(pSave, File(L"."), name, true);

#endif
	}
	printf("[loadLevel] Storage created=%p\n", storage.get()); fflush(stdout);

	//	McRegionLevelStorage *storage = new McRegionLevelStorage(new ConsoleSaveFile( L"" ), L"", L"", 0); // original
	//    McRegionLevelStorage *storage = new McRegionLevelStorage(File(L"."), name, true); // TODO
	printf("[loadLevel] Starting ServerLevel loop, levels.length=%u\n", levels.length); fflush(stdout);
	for (unsigned int i = 0; i < levels.length; i++)
	{
		printf("[loadLevel] Creating level %u\n", i); fflush(stdout);
		if( s_bServerHalted || !g_NetworkManager.IsInSession() )
		{
			return false;
		}

		//            String levelName = name;
		//            if (i == 1) levelName += "_nether";
		int dimension = 0;
		if (i == 1) dimension = -1;
		if (i == 2) dimension = 1;
		if (i == 0)
		{
			printf("[loadLevel] Creating ServerLevel for dimension %d\n", dimension); fflush(stdout);
			levels[i] = new ServerLevel(this, storage, name, dimension, levelSettings);
			printf("[loadLevel] ServerLevel created=%p\n", levels[i]); fflush(stdout);
			if(app.getLevelGenerationOptions() != nullptr)
			{
				LevelGenerationOptions *mapOptions = app.getLevelGenerationOptions();
				Pos *spawnPos = mapOptions->getSpawnPos();
				if( spawnPos != nullptr )
				{
					levels[i]->setSpawnPos( spawnPos );
				}

				levels[i]->getLevelData()->setHasBeenInCreative(mapOptions->isFromDLC());
			}
		}
		else {
			printf("[loadLevel] Creating DerivedServerLevel for dimension %d\n", dimension); fflush(stdout);
			levels[i] = new DerivedServerLevel(this, storage, name, dimension, levelSettings, levels[0]);
			printf("[loadLevel] DerivedServerLevel created=%p\n", levels[i]); fflush(stdout);
		}
		//        levels[i]->addListener(new ServerLevelListener(this, levels[i]));		// 4J - have moved this to the ServerLevel ctor so that it is set up in time for the first chunk to load, which might actually happen there

		// 4J Stu - We set the levels difficulty based on the minecraft options
		//levels[i]->difficulty = settings->getBoolean(L"spawn-monsters", true) ? Difficulty::EASY : Difficulty::PEACEFUL;
		printf("[loadLevel] Before GetGameHostOption for level %u\n", i); fflush(stdout);
		Minecraft *pMinecraft = Minecraft::GetInstance();
		//		m_lastSentDifficulty = pMinecraft->options->difficulty;
		levels[i]->difficulty = app.GetGameHostOption(eGameHostOption_Difficulty); //pMinecraft->options->difficulty;
		printf("[loadLevel] After GetGameHostOption, difficulty=%d\n", levels[i]->difficulty); fflush(stdout);
		app.DebugPrintf("MinecraftServer::loadLevel - Difficulty = %d\n",levels[i]->difficulty);

#if DEBUG_SERVER_DONT_SPAWN_MOBS
		levels[i]->setSpawnSettings(false, false);
#else
		levels[i]->setSpawnSettings(GetDedicatedServerBool(settings, L"spawn-monsters", true), animals);
#endif
		printf("[loadLevel] Before setGameType for level %u\n", i); fflush(stdout);
		levels[i]->getLevelData()->setGameType(gameType);

		if(app.getLevelGenerationOptions() != nullptr)
		{
			LevelGenerationOptions *mapOptions = app.getLevelGenerationOptions();
			levels[i]->getLevelData()->setHasBeenInCreative(mapOptions->getLevelHasBeenInCreative() );
		}

		players->setLevel(levels);
	}

	printf("[loadLevel] All levels created, entering post-creation phase\n"); fflush(stdout);

	if( levels[0]->isNew )
	{
		printf("[loadLevel] levels[0]->isNew is true, mcprogress=%p\n", mcprogress); fflush(stdout);
		if (mcprogress != nullptr) {
			printf("[loadLevel] About to call progressStage(GENERATING_SPAWN_AREA)\n"); fflush(stdout);
			mcprogress->progressStage(IDS_PROGRESS_GENERATING_SPAWN_AREA);
			printf("[loadLevel] progressStage(GENERATING_SPAWN_AREA) returned\n"); fflush(stdout);
		} else {
			printf("[loadLevel] mcprogress is NULL, skipping progressStage\n"); fflush(stdout);
		}
	}
	else
	{
		printf("[loadLevel] levels[0]->isNew is false, mcprogress=%p\n", mcprogress); fflush(stdout);
		if (mcprogress != nullptr) {
			printf("[loadLevel] About to call progressStage(LOADING_SPAWN_AREA)\n"); fflush(stdout);
			mcprogress->progressStage(IDS_PROGRESS_LOADING_SPAWN_AREA);
			printf("[loadLevel] progressStage(LOADING_SPAWN_AREA) returned\n"); fflush(stdout);
		} else {
			printf("[loadLevel] mcprogress is NULL, skipping progressStage\n"); fflush(stdout);
		}
	}
	printf("[loadLevel] After progressStage\n"); fflush(stdout);
	printf("[loadLevel] About to SetGameHostOption(HAS_BEEN_IN_CREATIVE)\n"); fflush(stdout);
	app.SetGameHostOption( eGameHostOption_HasBeenInCreative, gameType == GameType::CREATIVE || levels[0]->getHasBeenInCreative() );
	printf("[loadLevel] SetGameHostOption(HAS_BEEN_IN_CREATIVE) returned\n"); fflush(stdout);
	printf("[loadLevel] About to SetGameHostOption(STRUCTURES)\n"); fflush(stdout);
	app.SetGameHostOption( eGameHostOption_Structures, levels[0]->isGenerateMapFeatures() );
	printf("[loadLevel] SetGameHostOption(STRUCTURES) returned\n"); fflush(stdout);

	if( s_bServerHalted || !g_NetworkManager.IsInSession() ) return false;

	// 4J - Make a new thread to do post processing
	InitializeCriticalSection(&m_postProcessCS);

	// 4J-PB - fix for 108310 - TCR #001 BAS Game Stability: TU12: Code: Compliance: Crash after creating world on "journey" seed.
	// Stack gets very deep with some sand tower falling, so increased the stacj to 256K from 128k on other platforms (was already set to that on PS3 and Orbis)

	m_postUpdateThread = new C4JThread(runPostUpdate, this, "Post processing", 256*1024);

	m_postUpdateTerminate = false;
	m_postUpdateThread->SetProcessor(CPU_CORE_POST_PROCESSING);
	m_postUpdateThread->SetPriority(THREAD_PRIORITY_ABOVE_NORMAL);
	m_postUpdateThread->Run();

	int64_t startTime = System::currentTimeMillis();

	// 4J Stu - Added this to temporarily make starting games on vita faster
#ifdef __PSVITA__
	int r = 48;
#else
	int r = 196;
#endif

	//  4J JEV: load gameRules.
	ConsoleSavePath filepath(GAME_RULE_SAVENAME);
	ConsoleSaveFile *csf = getLevel(0)->getLevelStorage()->getSaveFile();
	if( csf->doesFileExist(filepath) )
	{
		DWORD numberOfBytesRead;
		byteArray ba_gameRules;

		FileEntry *fe = csf->createFile(filepath);

		ba_gameRules.length = fe->getFileSize();
		ba_gameRules.data = new BYTE[ ba_gameRules.length ];

		csf->setFilePointer(fe,0,nullptr,FILE_BEGIN);
		csf->readFile(fe, ba_gameRules.data, ba_gameRules.length, &numberOfBytesRead);
		assert(numberOfBytesRead == ba_gameRules.length);

		app.m_gameRules.loadGameRules(ba_gameRules.data, ba_gameRules.length);
		csf->closeHandle(fe);
	}

	int64_t lastTime = System::currentTimeMillis();
#ifdef _LARGE_WORLDS
	if(app.GetGameNewWorldSize() > levels[0]->getLevelData()->getXZSizeOld())
	{
		if(!app.GetGameNewWorldSizeUseMoat()) // check the moat settings to see if we should be overwriting the edge tiles
		{
			overwriteBordersForNewWorldSize(levels[0]);
		}
		// we're always overwriting hell edges
		int oldHellSize = levels[0]->getLevelData()->getXZHellSizeOld();
		overwriteHellBordersForNewWorldSize(levels[1], oldHellSize);
	}
#endif

	// 4J Stu - This loop is changed in 1.0.1 to only process the first level (ie the overworld), but I think we still want to do them all
	int i = 0;
	for (int i = 0; i < levels.length ; i++)
	{
		//        logger.info("Preparing start region for level " + i);
		if (i == 0 || GetDedicatedServerBool(settings, L"allow-nether", true))
		{
			ServerLevel *level = levels[i];
			if(levelChunksNeedConverted)
			{
				// 				storage->getSaveFile()->convertLevelChunks(level)
			}

#if 0
			int64_t lastStorageTickTime = System::currentTimeMillis();

			// Test code to enable full creation of levels at start up
			int halfsidelen = ( i == 0 ) ? 27 : 9;
			for( int x = -halfsidelen; x < halfsidelen; x++ )
			{
				for( int z = -halfsidelen; z < halfsidelen; z++ )
				{
					int total = halfsidelen * halfsidelen * 4;
					int pos = z + halfsidelen + ( ( x + halfsidelen ) * 2 * halfsidelen );
					mcprogress->progressStagePercentage((pos) * 100 / total);
					level->cache->create(x,z, true);	// 4J - added parameter to disable postprocessing here

					if( System::currentTimeMillis() - lastStorageTickTime > 50 )
					{
						CompressedTileStorage::tick();
						SparseLightStorage::tick();
						SparseDataStorage::tick();
						lastStorageTickTime = System::currentTimeMillis();
					}
				}
			}
#else
			int64_t lastStorageTickTime = System::currentTimeMillis();
			Pos *spawnPos = level->getSharedSpawnPos();

			int twoRPlusOne = r*2 + 1;
			int total = twoRPlusOne * twoRPlusOne;
			for (int x = -r; x <= r && running; x += 16)
			{
				for (int z = -r; z <= r && running; z += 16)
				{
					if( s_bServerHalted || !g_NetworkManager.IsInSession() )
					{
						delete spawnPos;
						m_postUpdateTerminate = true;
						postProcessTerminate(mcprogress);
						return false;
					}
					//					printf(">>>%d %d %d\n",i,x,z);
					//                    int64_t now = System::currentTimeMillis();
					//                    if (now < lastTime) lastTime = now;
					//                    if (now > lastTime + 1000)
					{
						int pos = (x + r) * twoRPlusOne + (z + 1);
						//                        setProgress(L"Preparing spawn area", (pos) * 100 / total);
						mcprogress->progressStagePercentage((pos+r) * 100 / total);
						//                        lastTime = now;
					}
					static int count = 0;
					PIXBeginNamedEvent(0,"Creating %d ", (count++)%8);
					level->cache->create((spawnPos->x + x) >> 4, (spawnPos->z + z) >> 4, true);	// 4J - added parameter to disable postprocessing here
					PIXEndNamedEvent();
					//                    while (level->updateLights() && running)
					//                        ;
					if( System::currentTimeMillis() - lastStorageTickTime > 50 )
					{
						CompressedTileStorage::tick();
						SparseLightStorage::tick();
						SparseDataStorage::tick();
						lastStorageTickTime = System::currentTimeMillis();
					}
				}
			}

			// 4J - removed this as now doing the recheckGaps call when each chunk is post-processed, so can happen on things outside of the spawn area too
#if 0
			// 4J - added this code to propagate lighting properly in the spawn area before we go sharing it with the local client or across the network
			for (int x = -r; x <= r && running; x += 16)
			{
				for (int z = -r; z <= r && running; z += 16)
				{
					PIXBeginNamedEvent(0,"Lighting gaps for %d %d",x,z);
					level->getChunkAt(spawnPos->x + x, spawnPos->z + z)->recheckGaps(true);
					PIXEndNamedEvent();
				}
			}
#endif

			delete spawnPos;
#endif
		}
	}
	//	printf("Main thread complete at %dms\n",System::currentTimeMillis() - startTime);

	// Wait for post processing, then lighting threads, to end (post-processing may make more lighting changes)
	m_postUpdateTerminate = true;

	postProcessTerminate(mcprogress);


	// stronghold position?
	if(levels[0]->dimension->id==0)
	{

		app.DebugPrintf("===================================\n");

		if(!levels[0]->getLevelData()->getHasStronghold())
		{
			int x,z;
			if(app.GetTerrainFeaturePosition(eTerrainFeature_Stronghold,&x,&z))
			{
				levels[0]->getLevelData()->setXStronghold(x);
				levels[0]->getLevelData()->setZStronghold(z);
				levels[0]->getLevelData()->setHasStronghold();

				app.DebugPrintf("=== FOUND stronghold in terrain features list\n");

			}
			else
			{
				// can't find the stronghold position in the terrain feature list. Do we have to run a post-process?
				app.DebugPrintf("=== Can't find stronghold in terrain features list\n");
			}
		}
		else
		{
			app.DebugPrintf("=== Leveldata has stronghold position\n");
		}
		app.DebugPrintf("===================================\n");
	}

	//	printf("Post processing complete at %dms\n",System::currentTimeMillis() - startTime);

	//	printf("Lighting complete at %dms\n",System::currentTimeMillis() - startTime);

	if( s_bServerHalted || !g_NetworkManager.IsInSession() ) return false;

	if( levels[1]->isNew )
	{
		levels[1]->save(true, mcprogress);
	}

	if( s_bServerHalted || !g_NetworkManager.IsInSession() ) return false;

	if( levels[2]->isNew )
	{
		levels[2]->save(true, mcprogress);
	}

	if( s_bServerHalted || !g_NetworkManager.IsInSession() ) return false;

	// 4J - added - immediately save newly created level, like single player game
	// 4J Stu - We also want to immediately save the tutorial
	if ( levels[0]->isNew )
		saveGameRules();

	if( levels[0]->isNew )
	{
		levels[0]->save(true, mcprogress);
	}

	if( s_bServerHalted || !g_NetworkManager.IsInSession() ) return false;

	if( levels[0]->isNew || levels[1]->isNew || levels[2]->isNew )
	{
#ifndef _WINDOWS64
		// On Windows64 we skip the automatic initial save so that choosing
		// "Exit without saving" on a new world does not leave an orphaned save folder.
		levels[0]->saveToDisc(mcprogress, false);
#endif
	}

	if( s_bServerHalted || !g_NetworkManager.IsInSession() ) return false;

	/*
	* int r = 24; for (int x = -r; x <= r; x++) {
	* setProgress("Preparing spawn area", (x + r) * 100 / (r + r + 1)); for (int z
	* = -r; z <= r; z++) { if (!running) return; level.cache.create((level.xSpawn
	* >> 4) + x, (level.zSpawn >> 4) + z); while (running && level.updateLights())
	* ; } }
	*/
	endProgress();

	return true;
}
