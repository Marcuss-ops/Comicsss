#include "stdafx.h"
#include "MinecraftServer.h"
#include "PlayerList.h"
#include "ServerLevel.h"
#include "ServerChunkCache.h"
#include "ServerConsoleCommandsHelpers.h"
#include "..\Minecraft.World\net.minecraft.world.level.h"
#include "..\Minecraft.World\GameRules.h"

// ── MISSING METHODS IMPLEMENTATION ──

void MinecraftServer::endProgress()
{
	// No-op for headless server
}

void MinecraftServer::saveAllChunks()
{
	for (unsigned int i = 0; i < levels.length; i++)
	{
		if (levels[i] != nullptr && levels[i]->cache != nullptr)
		{
			levels[i]->cache->save(true, nullptr);
		}
	}
}

void MinecraftServer::saveGameRules()
{
	byte *savedRules = nullptr;
	UINT savedRulesSize = 0;
	app.m_gameRules.saveGameRules(&savedRules, &savedRulesSize);
	if (savedRules != nullptr)
	{
		delete[] savedRules;
	}
}

#ifdef _LARGE_WORLDS
void MinecraftServer::overwriteBordersForNewWorldSize(ServerLevel* level)
{
	// No-op or minimal implementation
}

void MinecraftServer::overwriteHellBordersForNewWorldSize(ServerLevel* level, int oldHellSize)
{
	// No-op or minimal implementation
}
#endif

// ── END MISSING METHODS ──

File *MinecraftServer::getFile(const wstring& name)
{
	return new File(name);
}

void MinecraftServer::info(const wstring& string)
{
	PrintConsoleLine(L"[INFO] ", string);
}

void MinecraftServer::warn(const wstring& string)
{
	PrintConsoleLine(L"[WARN] ", string);
}

wstring MinecraftServer::getConsoleName()
{
	return L"CONSOLE";
}

ServerLevel *MinecraftServer::getLevel(int dimension)
{
	if (dimension == -1) return levels[1];
	else if (dimension == 1) return levels[2];
	else return levels[0];
}

// 4J added
void MinecraftServer::setLevel(int dimension, ServerLevel *level)
{
	if (dimension == -1) levels[1] = level;
	else if (dimension == 1) levels[2] = level;
	else levels[0] = level;
}

// 4J added - sets up a vector of flags to indicate which entities (with small Ids) have been removed from the level, but are still haven't constructed a network packet
// to tell a remote client about it. These small Ids shouldn't be re-used. Most of the time this method shouldn't actually do anything, in which case it will return false
// and nothing is set up.
bool MinecraftServer::flagEntitiesToBeRemoved(unsigned int *flags)
{
	bool removedFound = false;
	for( unsigned int i = 0; i < levels.length; i++ )
	{
		ServerLevel *level = levels[i];
		if( level )
		{
			level->flagEntitiesToBeRemoved( flags, &removedFound );
		}
	}
	return removedFound;
}
