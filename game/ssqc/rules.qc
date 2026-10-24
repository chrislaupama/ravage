/*
	Match rules: the Duel match flow, scoring, frag and time limits, and the
	end-of-match intermission. Set fraglimit and timelimit (minutes) on the
	server.

	A match runs warmup, countdown, play, overtime if needed, then the
	intermission:

	- Warmup: players play freely while they wait for an opponent. Each
	  types "ready" (or presses F3); when both players are ready the
	  countdown starts. "notready" takes it back.
	- Countdown: MATCH_COUNTDOWN_TIME seconds. Nobody can fire. If a
	  player leaves or un-readies, it's back to warmup.
	- Play: everything resets: frags, items, projectiles, and both players
	  respawn with the starting loadout. The clock counts timelimit down
	  from here, not from the map start.
	- Overtime: if time runs out with the scores tied, the next frag wins.
	- If a player leaves mid-match, the other wins by forfeit.

	Set rv_warmup 0 to skip warmup: the match then starts with the map, as
	the tests do.
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

	rv_match_state = MATCH_OVER;
	rv_match_time = 0;
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

// Reset the arena and respawn everyone: the match starts now.
void() Rules_StartMatch =
{
	local entity e, oldself;

	rv_match_state = MATCH_PLAYING;
	rv_match_start = time;
	rv_match_time = cvar("timelimit") > 0 ? time + cvar("timelimit") * 60 : 0;

	oldself = self;
	for (e = nextent(world); e; e = nextent(e))
	{
		if (e.classname == "rocket" || e.classname == "grenade")
			remove(e);
		else if (e.rv_is_item && e.model == "")
		{
			// Bring back taken pickups at once, silently.
			e.solid = SOLID_TRIGGER;
			setmodel(e, e.mdl);
			setsize(e, VEC_ITEM_MIN, VEC_ITEM_MAX);
			e.nextthink = 0;
		}
	}
	for (e = find(world, classname, "player"); e; e = find(e, classname, "player"))
	{
		e.frags = 0;
		self = e;
		PutClientInServer();
	}
	self = oldself;
	bprint(PRINT_HIGH, "FIGHT!\n");
};

// "ready" and "notready" from a player during warmup or the countdown.
void(float ready) Rules_SetReady =
{
	if (self.classname != "player" || rv_match_state > MATCH_COUNTDOWN || self.rv_ready == ready)
		return;
	self.rv_ready = ready;
	bprint(PRINT_HIGH, self.netname, ready ? " is ready\n" : " is not ready\n");
};

// Client "cmd" commands. Anything else goes to the engine.
void(string cmd) SV_ParseClientCommand =
{
	tokenize_console(cmd);
	if (argv(0) == "ready")
		Rules_SetReady(TRUE);
	else if (argv(0) == "notready")
		Rules_SetReady(FALSE);
	else
		clientcommand(self, cmd);
};

// The highest score, and whether two or more players share it.
float rules_tied;
float() Rules_TopFrags =
{
	local entity p;
	local float top;

	top = -100000;
	rules_tied = FALSE;
	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		if (p.frags == top)
			rules_tied = TRUE;
		else if (p.frags > top)
		{
			top = p.frags;
			rules_tied = FALSE;
		}
	}
	return top;
};

void() Rules_Frame =
{
	local entity p;
	local float fraglimit, top;

	rv_players = 0;
	rv_ready_count = 0;
	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		rv_players = rv_players + 1;
		if (p.rv_ready)
			rv_ready_count = rv_ready_count + 1;
	}

	switch (rv_match_state)
	{
	case MATCH_WARMUP:
		if (!autocvar_rv_warmup)
		{
			// No warmup: the match runs from the map start.
			rv_match_state = MATCH_PLAYING;
			rv_match_start = 0;
			rv_match_time = cvar("timelimit") > 0 ? cvar("timelimit") * 60 : 0;
		}
		else if (rv_players == MATCH_PLAYERS && rv_ready_count == MATCH_PLAYERS)
		{
			rv_match_state = MATCH_COUNTDOWN;
			rv_match_time = time + MATCH_COUNTDOWN_TIME;
			bprint(PRINT_HIGH, "The match starts in ", ftos(MATCH_COUNTDOWN_TIME), " seconds\n");
		}
		return;

	case MATCH_COUNTDOWN:
		if (rv_players != MATCH_PLAYERS || rv_ready_count != MATCH_PLAYERS)
		{
			rv_match_state = MATCH_WARMUP;
			rv_match_time = 0;
			bprint(PRINT_HIGH, "Countdown stopped\n");
		}
		else if (time >= rv_match_time)
			Rules_StartMatch();
		return;

	case MATCH_PLAYING:
		if (autocvar_rv_warmup && rv_players < MATCH_PLAYERS)
		{
			if (rv_players)
				bprint(PRINT_HIGH, find(world, classname, "player").netname, " wins by forfeit\n");
			Rules_StartIntermission();
			return;
		}
		top = Rules_TopFrags();
		fraglimit = cvar("fraglimit");
		if (fraglimit && top >= fraglimit)
		{
			Rules_StartIntermission();
			return;
		}
		if (rv_match_time && time >= rv_match_time)
		{
			if (rules_tied)
			{
				rv_match_state = MATCH_OVERTIME;
				rv_match_time = 0;
				bprint(PRINT_HIGH, "Overtime: the next frag wins\n");
			}
			else
				Rules_StartIntermission();
		}
		return;

	case MATCH_OVERTIME:
		Rules_TopFrags();
		if (!rules_tied || (autocvar_rv_warmup && rv_players < MATCH_PLAYERS))
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

//
// Spectators: anyone who joins once both Duel slots are taken (maxclients
// is 2), or with "spectator 1". The engine flies them around freely.
//

void() SpectatorConnect =
{
	bprint(PRINT_HIGH, self.netname, " is spectating\n");
};

void() SpectatorDisconnect =
{
	bprint(PRINT_HIGH, self.netname, " stopped spectating\n");
};

void() SpectatorThink =
{
};
