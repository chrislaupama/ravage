/*
	Map self-test, run a few frames after the map loads.

	Checks that every spawn point has room for a player and stands on a
	floor, and that every pickup rests on a floor. Prints a summary that
	tests/map_pipeline.sh looks for. With "set rv_selftest 1" the server
	quits after printing it.
*/

float rv_selftest_done;
float rv_selftest_frames;
float rv_selftest_errors;

void(entity e, string what) SelfTest_Fail =
{
	print("RAVAGE selftest: FAIL ", e.classname, " at ", vtos(e.origin), ": ", what, "\n");
	rv_selftest_errors = rv_selftest_errors + 1;
};

// A point is on a floor if a short trace down hits something walkable.
float(vector org, float reach) SelfTest_OnFloor =
{
	traceline(org, org - '0 0 1' * reach, MOVE_NOMONSTERS, world);
	return trace_fraction < 1 && trace_plane_normal_z > 0.7;
};

void() SelfTest_Frame =
{
	local entity e;
	local float spawns, items;

	// Wait a few frames so every entity has spawned and settled.
	rv_selftest_frames = rv_selftest_frames + 1;
	if (rv_selftest_done || rv_selftest_frames < 3)
		return;
	rv_selftest_done = TRUE;
	spawns = 0;
	items = 0;

	for (e = find(world, classname, "info_player_deathmatch"); e; e = find(e, classname, "info_player_deathmatch"))
	{
		spawns = spawns + 1;
		tracebox(e.origin + '0 0 1', VEC_HULL_MIN, VEC_HULL_MAX, e.origin + '0 0 1', MOVE_NOMONSTERS, world);
		if (trace_startsolid)
			SelfTest_Fail(e, "player would be stuck in a wall");
		else if (!SelfTest_OnFloor(e.origin + '0 0 -23', 16))
			SelfTest_Fail(e, "no floor below the spawn point");
	}

	for (e = nextent(world); e; e = nextent(e))
	{
		if (e.rv_is_item)
		{
			items = items + 1;
			if (!SelfTest_OnFloor(e.origin + '0 0 8', 16))
				SelfTest_Fail(e, "pickup is not resting on a floor");
		}
	}

	if (!spawns)
	{
		print("RAVAGE selftest: FAIL map has no info_player_deathmatch\n");
		rv_selftest_errors = rv_selftest_errors + 1;
	}

	print("RAVAGE selftest: map=", mapname, " spawns=", ftos(spawns), " items=", ftos(items));
	print(" triggers=", ftos(rv_trigger_count), " errors=", ftos(rv_selftest_errors), "\n");
	if (rv_selftest_errors)
		print("RAVAGE selftest: FAIL\n");
	else
		print("RAVAGE selftest: PASS\n");

	if (cvar("rv_selftest"))
		localcmd("quit\n");
};
