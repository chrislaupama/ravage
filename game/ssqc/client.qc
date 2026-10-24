/*
	Client connection, spawning and the per-player frame.
*/

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
	// The engine keeps the entity, so stop it counting as a player.
	self.classname = "";
	self.solid = SOLID_NOT;
	self.takedamage = DAMAGE_NO;
	setmodel(self, "");
};

void() ClientKill =
{
	if (self.health > 0 && !rv_intermission)
		T_Damage(self, self, self, 1000);
};

// Duel spawn rule: pick the spawn point farthest from every other living
// player. Ties go to the first in map order, so spawns are deterministic.
entity() SelectSpawnPoint =
{
	local entity spot, best, p;
	local float best_dist, dist, index, best_index;

	best = world;
	best_dist = -1;
	best_index = 0;
	index = 0;
	for (spot = find(world, classname, "info_player_deathmatch"); spot; spot = find(spot, classname, "info_player_deathmatch"))
	{
		index = index + 1;
		dist = 100000;
		for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
			if (p != self && p.health > 0)
				dist = min(dist, vlen(p.origin - spot.origin));
		if (dist > best_dist)
		{
			best = spot;
			best_dist = dist;
			best_index = index;
		}
	}
	if (!best)
	{
		best = find(world, classname, "info_player_start");
		best_index = 0;
	}
	if (!best)
		error("map has no info_player_deathmatch or info_player_start\n");
	self.rv_spawn_index = best_index;
	return best;
};

void() PutClientInServer =
{
	local entity spot;

	spot = SelectSpawnPoint();

	self.classname = "player";
	self.health = 100;
	self.max_health = 100;
	self.armorvalue = 0;
	self.armortype = 0;
	self.takedamage = DAMAGE_AIM;
	self.deadflag = DEAD_NO;
	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_WALK;
	self.flags = FL_CLIENT;
	self.velocity = '0 0 0';
	self.view_ofs = '0 0 22';
	self.angles = self.v_angle = spot.angles;
	self.fixangle = TRUE;
	self.attack_finished = time + 0.3;
	self.teleport_time = 0;

	// Starting loadout: machine gun only.
	self.items = IT_MACHINEGUN;
	self.ammo_shells = self.ammo_bullets = self.ammo_rockets = 0;
	self.ammo_grenades = self.ammo_cells = self.ammo_slugs = 0;
	self.ammo_bullets = 100;
	self.weapon = WEP_MACHINEGUN;
	W_UpdateCurrentAmmo();

	setmodel(self, MDL_PLAYER);
	self.frame = ANIM_STAND;
	setsize(self, VEC_HULL_MIN, VEC_HULL_MAX);
	setorigin(self, spot.origin + '0 0 1');
	self.rv_spawn_origin = self.origin;
};

void() PlayerPreThink =
{
	if (rv_intermission)
	{
		Rules_IntermissionThink();
		return;
	}
	// Dead players respawn on attack or jump after a second, or by
	// themselves after five.
	if (self.deadflag)
	{
		if (time >= self.rv_respawn_time + 4 || (time >= self.rv_respawn_time && (self.button0 || self.button2)))
			PutClientInServer();
	}
};

void() PlayerPostThink =
{
	if (rv_intermission || self.deadflag)
		return;

	// Nobody fires during the countdown.
	if (rv_match_state != MATCH_COUNTDOWN)
		W_Frame();
	Player_Animate();

	// Health over 100 ticks down by one per second.
	if (self.health > self.max_health && time >= self.rv_mega_decay)
	{
		self.health = self.health - 1;
		self.rv_mega_decay = time + 1;
	}
};
