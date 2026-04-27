#include "stdafx.h"
#include "Level.h"

#include "Dimension.h"
#include "Mth.h"
#include "Vec3.h"
#include "LevelData.h"
#include "Random.h"
#include "Tile.h"

// ---------------------------------------------------------------------------
// Time & Weather methods extracted from Level.cpp
// ---------------------------------------------------------------------------

float Level::getTimeOfDay(float a)
{
	/*
	* 4J-PB removed line below - notch committed 1.6.6 with the incorrect
	* getTimeOfDay and changed it before releasing (without
	* re-committing)... that should be the only difference // jeb
	*/
	/* if (this != nullptr) return 0.5f; */

	// 4J Added if so we can override timeOfDay without changing the time that affects ticking of things
	return dimension->getTimeOfDay(levelData->getDayTime(), a);;
}

int Level::getMoonPhase()
{
	return dimension->getMoonPhase(levelData->getDayTime());
}

float Level::getMoonBrightness()
{
	return Dimension::MOON_BRIGHTNESS_PER_PHASE[dimension->getMoonPhase(levelData->getDayTime())];
}

float Level::getSunAngle(float a)
{
	float td = getTimeOfDay(a);
	return td * PI * 2;
}

//4J - change brought forward from 1.8.2
int Level::getOldSkyDarken(float a)
{
	float td = getTimeOfDay(a);

	float br = 1 - (Mth::cos(td * PI * 2) * 2 + 0.5f);
	if (br < 0.0f) br = 0.0f;
	if (br > 1.0f) br = 1.0f;

	br = 1 - br;

	br *= 1 - (getRainLevel(a) * 5 / 16.0f);
	br *= 1 - (getThunderLevel(a) * 5 / 16.0f);
	br = 1 - br;
	return static_cast<int>(br * 11);
}

//4J - change brought forward from 1.8.2
float Level::getSkyDarken(float a)
{
	float td = getTimeOfDay(a);

	float br = 1 - (Mth::cos(td * PI * 2) * 2 + 0.2f);
	if (br < 0.0f) br = 0.0f;
	if (br > 1.0f) br = 1.0f;

	br = 1.0f - br;

	br *= 1.0f - (getRainLevel(a) * 5.0f / 16.0f);
	br *= 1.0f - (getThunderLevel(a) * 5.0f / 16.0f);
	// return ((int) (br * 13));

	return br * 0.8f + 0.2f;
}

Vec3 *Level::getSkyColor(shared_ptr<Entity> source, float a)
{
	float td = getTimeOfDay(a);

	float br = Mth::cos(td * PI * 2) * 2 + 0.5f;
	if (br < 0.0f) br = 0.0f;
	if (br > 1.0f) br = 1.0f;

	int xx = Mth::floor(source->x);
	int zz = Mth::floor(source->z);
	Biome *biome = getBiome(xx, zz);
	float temp = biome->getTemperature();
	int skyColor = biome->getSkyColor(temp);

	float r = ((skyColor >> 16) & 0xff) / 255.0f;
	float g = ((skyColor >> 8) & 0xff) / 255.0f;
	float b = ((skyColor) & 0xff) / 255.0f;
	r *= br;
	g *= br;
	b *= br;

	float rainLevel = getRainLevel(a);
	if (rainLevel > 0)
	{
		float mid = (r * 0.30f + g * 0.59f + b * 0.11f) * 0.6f;

		float ba = 1 - rainLevel * 0.75f;
		r = r * ba + mid * (1 - ba);
		g = g * ba + mid * (1 - ba);
		b = b * ba + mid * (1 - ba);
	}
	float thunderLevel = getThunderLevel(a);
	if (thunderLevel > 0)
	{
		float mid = (r * 0.30f + g * 0.59f + b * 0.11f) * 0.2f;

		float ba = 1 - thunderLevel * 0.75f;
		r = r * ba + mid * (1 - ba);
		g = g * ba + mid * (1 - ba);
		b = b * ba + mid * (1 - ba);
	}

	if (skyFlashTime > 0)
	{
		float f = (skyFlashTime - a);
		if (f > 1) f = 1;
		f = f * 0.45f;
		r = r * (1 - f) + 0.8f * f;
		g = g * (1 - f) + 0.8f * f;
		b = b * (1 - f) + 1 * f;
	}

	return Vec3::newTemp(r, g, b);
}

// getCloudColor is kept in Level.cpp as it requires client-side Minecraft::GetInstance()


Vec3 *Level::getFogColor(float a)
{
	float td = getTimeOfDay(a);
	return dimension->getFogColor(td, a);
}

float Level::getStarBrightness(float a)
{
	float td = getTimeOfDay(a);

	float br = 1 - (Mth::cos(td * PI * 2) * 2 + 0.25f);
	if (br < 0.0f) br = 0.0f;
	if (br > 1.0f) br = 1.0f;

	return br * br * 0.5f;
}

float Level::getThunderLevel(float a)
{
	return (oThunderLevel + (thunderLevel - oThunderLevel) * a) * getRainLevel(a);
}

float Level::getRainLevel(float a)
{
	return oRainLevel + (rainLevel - oRainLevel) * a;
}

void Level::setRainLevel(float rainLevel)
{
	oRainLevel = rainLevel;
	this->rainLevel = rainLevel;
}

bool Level::isThundering()
{
	return getThunderLevel(1) > 0.9;
}

bool Level::isRaining()
{
	return getRainLevel(1) > 0.2;
}

bool Level::isRainingAt(int x, int y, int z)
{
	if (!isRaining()) return false;
	if (!canSeeSky(x, y, z)) return false;
	if (getTopRainBlock(x, z) > y) return false;
	return biomeHasRain(x, z);
}

void Level::prepareWeather()
{
	if (levelData->isRaining())
	{
		rainLevel = 1;
		if (levelData->isThundering())
		{
			thunderLevel = 1;
		}
	}
}

void Level::tickWeather()
{
	if (dimension->hasCeiling) return;

#ifndef _FINAL_BUILD
	// debug setting added to disable weather
	if(app.DebugSettingsOn())
	{
		if(app.GetGameSettingsDebugMask(ProfileManager.GetPrimaryPad())&(1L<<eDebugSetting_DisableWeather))
		{
			levelData->setThundering(false);
			levelData->setThunderTime(random->nextInt(TICKS_PER_DAY * 7) + TICKS_PER_DAY / 2);
			levelData->setRaining(false);
			levelData->setRainTime(random->nextInt(TICKS_PER_DAY * 7) + TICKS_PER_DAY / 2);
		}
	}
#endif

	int thunderTime = levelData->getThunderTime();
	if (thunderTime <= 0)
	{
		if (levelData->isThundering())
		{
			levelData->setThunderTime(random->nextInt(20 * 60 * 10) + 20 * 60 * 3);
		}
		else
		{
			levelData->setThunderTime(random->nextInt(TICKS_PER_DAY * 7) + TICKS_PER_DAY / 2);
		}
	}
	else
	{
		thunderTime--;
		levelData->setThunderTime(thunderTime);
		if (thunderTime <= 0)
		{
			levelData->setThundering(!levelData->isThundering());
		}
	}

	int rainTime = levelData->getRainTime();
	if (rainTime <= 0)
	{
		if (levelData->isRaining())
		{
			levelData->setRainTime(random->nextInt(TICKS_PER_DAY / 2) + TICKS_PER_DAY / 2);
		}
		else
		{
			levelData->setRainTime(random->nextInt(TICKS_PER_DAY * 7) + TICKS_PER_DAY / 2);
		}
	}
	else
	{
		rainTime--;
		levelData->setRainTime(rainTime);
		if (rainTime <= 0)
		{
			levelData->setRaining(!levelData->isRaining());
		}
		/*		if( !levelData->isRaining() )
		{
		levelData->setRaining(true);
		}*/
	}

	oRainLevel = rainLevel;
	if (levelData->isRaining())
	{
		rainLevel += 0.01;
	}
	else
	{
		rainLevel -= 0.01;
	}
	if (rainLevel < 0) rainLevel = 0;
	if (rainLevel > 1) rainLevel = 1;

	oThunderLevel = thunderLevel;
	if (levelData->isThundering())
	{
		thunderLevel += 0.01;
	}
	else
	{
		thunderLevel -= 0.01;
	}
	if (thunderLevel < 0) thunderLevel = 0;
	if (thunderLevel > 1) thunderLevel = 1;
}

void Level::toggleDownfall()
{
	// this will trick the tickWeather method to toggle rain next tick
	levelData->setRainTime(1);
}
