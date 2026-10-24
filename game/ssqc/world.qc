/*
	RAVAGE server game code: world setup and the per-frame hook.
*/

void() main =
{
};

void() SUB_Remove =
{
	remove(self);
};

void() Stats_Register =
{
	clientstat(STAT_RV_HEALTH, EV_FLOAT, health);
	clientstat(STAT_RV_ARMOR, EV_FLOAT, armorvalue);
	clientstat(STAT_RV_WEAPON, EV_FLOAT, weapon);
	clientstat(STAT_RV_ITEMS, EV_FLOAT, items);
	clientstat(STAT_RV_FIRE_TIME, EV_FLOAT, rv_fire_time);
	clientstat(STAT_RV_AMMO + WEP_SHOTGUN - 1, EV_FLOAT, ammo_shells);
	clientstat(STAT_RV_AMMO + WEP_MACHINEGUN - 1, EV_FLOAT, ammo_bullets);
	clientstat(STAT_RV_AMMO + WEP_ROCKET - 1, EV_FLOAT, ammo_rockets);
	clientstat(STAT_RV_AMMO + WEP_GRENADE - 1, EV_FLOAT, ammo_grenades);
	clientstat(STAT_RV_AMMO + WEP_LIGHTNING - 1, EV_FLOAT, ammo_cells);
	clientstat(STAT_RV_AMMO + WEP_RAILGUN - 1, EV_FLOAT, ammo_slugs);
};

void() worldspawn =
{
	// Style 0 is normal, steady light. Without it the map renders black.
	lightstyle(0, "m");
	Assets_Precache();
	Stats_Register();
	rv_intermission = 0;
};

void() StartFrame =
{
	Rules_Frame();
	SelfTest_Frame();
	MatchTest_Frame();
};
