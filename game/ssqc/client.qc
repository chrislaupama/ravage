/*
	Client connection and spawning.
*/

entity rv_last_spawn;

void() SetNewParms =
{
};

void() SetChangeParms =
{
};

void() ClientConnect =
{
	bprint(PRINT_HIGH, self.netname, " entered the arena\n");
};

void() ClientDisconnect =
{
	bprint(PRINT_HIGH, self.netname, " left the arena\n");
};

void() ClientKill =
{
};

// Cycle through the deathmatch spawn points, falling back to
// info_player_start when the map has none.
entity() SelectSpawnPoint =
{
	local entity spot;

	spot = find(rv_last_spawn, classname, "info_player_deathmatch");
	if (!spot)
		spot = find(world, classname, "info_player_deathmatch");
	if (!spot)
		spot = find(world, classname, "info_player_start");
	if (!spot)
		error("map has no info_player_deathmatch or info_player_start\n");
	rv_last_spawn = spot;
	return spot;
};

void() PutClientInServer =
{
	local entity spot;

	spot = SelectSpawnPoint();

	self.classname = "player";
	self.health = 100;
	self.takedamage = DAMAGE_NO;
	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_WALK;
	self.flags = FL_CLIENT;
	self.velocity = '0 0 0';
	self.view_ofs = '0 0 22';
	self.angles = spot.angles;
	self.fixangle = TRUE;
	setorigin(self, spot.origin + '0 0 1');
	setsize(self, VEC_HULL_MIN, VEC_HULL_MAX);
};

void() PlayerPreThink =
{
};

void() PlayerPostThink =
{
};
