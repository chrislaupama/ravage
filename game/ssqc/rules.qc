/*
	Match rules: scoring, frag and time limits, and the end-of-match
	intermission. Set fraglimit and timelimit (minutes) on the server.
*/

void(entity attacker, entity targ) Rules_Frag =
{
	if (attacker == targ || attacker.classname != "player")
	{
		targ.frags = targ.frags - 1;
		bprint(PRINT_MEDIUM, targ.netname, " died\n");
	}
	else
	{
		attacker.frags = attacker.frags + 1;
		bprint(PRINT_MEDIUM, targ.netname, " was fragged by ", attacker.netname, "\n");
	}
};

// Freeze everyone at the intermission camera and show scores.
void() Rules_StartIntermission =
{
	local entity p;

	rv_intermission = time;
	rv_intermission_exit = time + 5;
	rv_intermission_spot = find(world, classname, "info_intermission");
	if (!rv_intermission_spot)
		rv_intermission_spot = find(world, classname, "info_player_deathmatch");

	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		p.takedamage = DAMAGE_NO;
		p.solid = SOLID_NOT;
		p.movetype = MOVETYPE_NONE;
		p.modelindex = 0;
		p.velocity = '0 0 0';
		setorigin(p, rv_intermission_spot.origin);
		p.angles = p.v_angle = rv_intermission_spot.mangle;
		p.fixangle = TRUE;
		bprint(PRINT_HIGH, p.netname, ": ", ftos(p.frags), " frags\n");
	}
	// Ask clients to show the scoreboard.
	WriteByte(MSG_ALL, SVC_INTERMISSION);
	WriteCoord(MSG_ALL, rv_intermission_spot.origin_x);
	WriteCoord(MSG_ALL, rv_intermission_spot.origin_y);
	WriteCoord(MSG_ALL, rv_intermission_spot.origin_z);
	WriteAngle(MSG_ALL, rv_intermission_spot.mangle_x);
	WriteAngle(MSG_ALL, rv_intermission_spot.mangle_y);
	WriteAngle(MSG_ALL, rv_intermission_spot.mangle_z);
};

void() Rules_Frame =
{
	local entity p;
	local float fraglimit, timelimit;

	if (rv_intermission)
		return;

	fraglimit = cvar("fraglimit");
	timelimit = cvar("timelimit") * 60;
	if (timelimit && time >= timelimit)
	{
		Rules_StartIntermission();
		return;
	}
	if (fraglimit)
		for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
			if (p.frags >= fraglimit)
			{
				Rules_StartIntermission();
				return;
			}
};

// During intermission, any button after a short delay restarts the map.
void() Rules_IntermissionThink =
{
	if (time < rv_intermission_exit)
		return;
	if (self.button0 || self.button2)
		changelevel(mapname);
};
