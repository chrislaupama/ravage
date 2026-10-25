/*
	Two-client match test, used by tests/match.sh.

	Enabled with "set rv_matchtest 1" on the server. Two real clients
	connect: "target" stands still and "runner" holds +forward. Once both
	are in, the test checks, in order:

	1. ready-up:   in warmup, both players type "ready"; after the countdown
	               the match starts with frags reset
	2. spawns:     both players spawned at different deathmatch spawn points
	3. collision:  the runner moved, and no player ever ended up inside
	               the world or outside the arena
	4. pickups:    the target picks up mega health and the rocket launcher
	5. combat:     the runner's railgun shot kills the target and scores
	6. respawn:    the target respawns at a deathmatch spawn point
	7. hud:        the target's client HUD shows the respawn loadout (checked
	               by tests/match.sh in the client's log)
	8. overtime:   with time up and the scores tied the match goes to
	               overtime, and the next frag ends it
	9. stats:      the post-match statistics counted the shots, hits,
	               damage, frags, deaths and pickups above, and none from
	               warmup (tests/match.sh checks the saved file and the
	               demo)

	Each check prints "RAVAGE matchtest: ok <name>" or "FAIL <name>: why".
	The server quits when all checks have run.
*/

float mt_phase;
float mt_phase_time;
float mt_errors;
float mt_errors_before;	// mt_errors when the current check started
float mt_started;
entity mt_runner;
entity mt_target;
entity mt_item;

void(string name) MatchTest_Ok =
{
	print("RAVAGE matchtest: ok ", name, "\n");
};

void(string name, string why) MatchTest_Fail =
{
	print("RAVAGE matchtest: FAIL ", name, ": ", why, "\n");
	mt_errors = mt_errors + 1;
};

void(float phase) MatchTest_Next =
{
	mt_phase = phase;
	mt_phase_time = time;
};

void() MatchTest_Finish =
{
	if (mt_errors)
		print("RAVAGE matchtest: FAIL (", ftos(mt_errors), " errors)\n");
	else
		print("RAVAGE matchtest: PASS\n");
	localcmd("quit\n");
	mt_phase = 99;
};

entity(string name) MatchTest_FindPlayer =
{
	local entity p;

	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
		if (p.netname == name && p.health > 0)
			return p;
	return world;
};

// A player may never be inside solid world geometry or below the floor.
void() MatchTest_CheckCollision =
{
	local entity p;

	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		if (p.health <= 0)
			continue;
		tracebox(p.origin, VEC_HULL_MIN, VEC_HULL_MAX, p.origin, MOVE_NOMONSTERS, p);
		if (trace_startsolid || pointcontents(p.origin) == CONTENT_SOLID)
		{
			MatchTest_Fail("collision", strcat(p.netname, " is inside the world at ", vtos(p.origin)));
			MatchTest_Finish();
			return;
		}
		if (p.origin_z < world.mins_z || p.origin_x < world.mins_x || p.origin_x > world.maxs_x
			|| p.origin_y < world.mins_y || p.origin_y > world.maxs_y)
		{
			MatchTest_Fail("collision", strcat(p.netname, " left the arena at ", vtos(p.origin)));
			MatchTest_Finish();
			return;
		}
	}
};

void() MatchTest_Frame =
{
	local entity oldself;
	local vector src;

	if (!cvar("rv_matchtest") || mt_phase == 99)
		return;
	if (!mt_started)
	{
		mt_started = TRUE;
		MatchTest_Next(0);
	}
	if (time - mt_phase_time > 30)
	{
		MatchTest_Fail(ftos(mt_phase), "timed out");
		MatchTest_Finish();
		return;
	}
	if (mt_phase > 0)
		MatchTest_CheckCollision();
	if (mt_phase == 99)
		return;

	switch (mt_phase)
	{
	case 0:	// wait for both clients, then have them ready up
		mt_runner = MatchTest_FindPlayer("runner");
		mt_target = MatchTest_FindPlayer("target");
		if (!mt_runner || !mt_target)
			return;
		if (rv_match_state != MATCH_WARMUP)
		{
			MatchTest_Fail("ready-up", "the match did not start in warmup");
			MatchTest_Finish();
			return;
		}
		// A warmup frag, which the match start must clear.
		mt_runner.frags = 3;
		stuffcmd(mt_runner, "cmd ready\n");
		stuffcmd(mt_target, "cmd ready\n");
		MatchTest_Next(10);
		return;

	case 10:	// countdown, then the match
		if (rv_match_state != MATCH_PLAYING)
			return;
		if (time - mt_phase_time < MATCH_COUNTDOWN_TIME)
			MatchTest_Fail("ready-up", "the match started before the countdown ended");
		else if (mt_runner.frags != 0)
			MatchTest_Fail("ready-up", "frags were not reset at the match start");
		else
			MatchTest_Ok("ready-up");
		mt_runner = MatchTest_FindPlayer("runner");
		mt_target = MatchTest_FindPlayer("target");
		if (!mt_runner.rv_spawn_index || !mt_target.rv_spawn_index)
			MatchTest_Fail("spawns", "a player did not use an info_player_deathmatch");
		else if (mt_runner.rv_spawn_index == mt_target.rv_spawn_index)
			MatchTest_Fail("spawns", "both players used the same spawn point");
		else
			MatchTest_Ok("spawns");
		MatchTest_Next(1);
		return;

	case 1:	// let the runner run into the level for three seconds
		if (time - mt_phase_time < 3)
			return;
		if (vlen(mt_runner.origin - mt_runner.rv_spawn_origin) < 100)
			MatchTest_Fail("collision", strcat("runner did not move: ", vtos(mt_runner.origin)));
		else
			MatchTest_Ok("collision");
		mt_target.health = 100;
		mt_errors_before = mt_errors;
		mt_item = find(world, classname, "item_health_mega");
		setorigin(mt_target, mt_item.origin + '0 0 25');
		MatchTest_Next(2);
		return;

	case 2:	// mega health
		if (mt_item.solid == SOLID_TRIGGER && time - mt_phase_time < 2)
			return;
		if (mt_item.solid == SOLID_TRIGGER)
			MatchTest_Fail("pickups", "mega health was not picked up");
		else if (mt_target.health < 199)
			MatchTest_Fail("pickups", strcat("mega health gave ", ftos(mt_target.health), " health"));
		mt_item = find(world, classname, "weapon_rocketlauncher");
		setorigin(mt_target, mt_item.origin + '0 0 25');
		MatchTest_Next(3);
		return;

	case 3:	// rocket launcher
		if (mt_item.solid == SOLID_TRIGGER && time - mt_phase_time < 2)
			return;
		if (!(mt_target.items & IT_ROCKET) || mt_target.weapon != WEP_ROCKET || mt_target.ammo_rockets < 10)
			MatchTest_Fail("pickups", "rocket launcher was not picked up and selected");
		else if (mt_errors == mt_errors_before)
			MatchTest_Ok("pickups");
		// Stand both players on open floor with a clear line between them,
		// and let lag compensation catch up with the move.
		mt_target.health = 100;
		mt_target.armorvalue = 0;
		setorigin(mt_target, '0 -300 25');
		MatchTest_Next(4);
		return;

	case 4:	// railgun shot from the runner
		if (time - mt_phase_time < 1)
			return;
		oldself = self;
		self = mt_runner;
		setorigin(self, mt_target.origin - '300 0 0');
		self.items = self.items | IT_RAILGUN;
		self.ammo_slugs = 10;
		self.attack_finished = 0;
		src = self.origin + self.view_ofs;
		self.v_angle = vectoangles(mt_target.origin - src);	// makevectors() turns this back into the same direction
		W_Fire(WEP_RAILGUN);
		self = oldself;
		if (mt_target.health > 0)
			MatchTest_Fail("combat", strcat("target survived with ", ftos(mt_target.health), " health"));
		else if (mt_runner.frags != 1)
			MatchTest_Fail("combat", strcat("runner has ", ftos(mt_runner.frags), " frags, expected 1"));
		else
			MatchTest_Ok("combat");
		MatchTest_Next(5);
		return;

	case 5:	// automatic respawn
		if (mt_target.health <= 0)
			return;
		if (!mt_target.rv_spawn_index)
			MatchTest_Fail("respawn", "target respawned away from a spawn point");
		else
			MatchTest_Ok("respawn");
		// Have the target's client print what its HUD shows, which
		// tests/match.sh checks against the respawn loadout.
		stuffcmd(mt_target, "rv_hudtest\n");
		MatchTest_Next(6);
		return;

	case 6:	// give the client a moment to answer
		if (time - mt_phase_time < 1)
			return;
		// Level the scores with a frag for the target, and run the clock
		// out.
		Rules_Frag(mt_target, mt_runner);
		rv_match_time = time;
		MatchTest_Next(7);
		return;

	case 7:	// overtime, ended by the next frag
		if (rv_match_state != MATCH_OVERTIME)
		{
			MatchTest_Fail("overtime", strcat("match state is ", ftos(rv_match_state), " with the scores tied"));
			MatchTest_Finish();
			return;
		}
		Rules_Frag(mt_runner, mt_target);
		MatchTest_Next(8);
		return;

	case 8:
		if (rv_match_state != MATCH_OVER)
		{
			MatchTest_Fail("overtime", "the match did not end on the overtime frag");
			MatchTest_Finish();
			return;
		}
		MatchTest_Ok("overtime");
		// The match statistics, counted since ready-up: the runner's
		// railgun shot and the overtime frag, the target's mega health.
		if (mt_runner.rv_stat[MS_SHOTS + WEP_RAILGUN - 1] != 1 || mt_runner.rv_stat[MS_HITS + WEP_RAILGUN - 1] != 1)
			MatchTest_Fail("stats", "the runner's railgun shot was not counted as one shot and one hit");
		else if (mt_runner.rv_stat[MS_DAMAGE_DEALT] != 100 || mt_target.rv_stat[MS_DAMAGE_TAKEN] != 100)
			MatchTest_Fail("stats", strcat("damage dealt ", ftos(mt_runner.rv_stat[MS_DAMAGE_DEALT]), " and taken ",
				ftos(mt_target.rv_stat[MS_DAMAGE_TAKEN]), ", expected 100"));
		else if (mt_runner.rv_stat[MS_FRAGS] != 2 || mt_target.rv_stat[MS_DEATHS] != 2
			|| mt_target.rv_stat[MS_FRAGS] != 1 || mt_runner.rv_stat[MS_DEATHS] != 1)
			MatchTest_Fail("stats", "frags and deaths were not counted from the match start");
		else if (mt_target.rv_stat[MS_MEGAS] != 1 || mt_target.rv_stat[MS_HEALTH] != 100)
			MatchTest_Fail("stats", strcat("target picked up ", ftos(mt_target.rv_stat[MS_HEALTH]), " health, expected one mega health"));
		else
			MatchTest_Ok("stats");
		MatchTest_Next(9);
		return;

	case 9:	// the demo stops a few seconds into the scoreboard
		if (stats_recording)
			return;
		MatchTest_Finish();
		return;
	}
};
