/*
	Match recording and post-match statistics.

	Every match is recorded on the server as an MVD demo, from the moment
	it starts until a few seconds into the scoreboard, in demos/ in the
	game folder. Watch one with "playdemo demos/<name>.mvd". The demo
	carries a copy of the client game code, so it still plays after the
	game changes.

	While a match is on, each player's statistics are counted from server
	events: shots and hits by weapon, damage dealt and taken, frags,
	deaths and pickups. When it ends they go to every client for the
	scoreboard (EV_MATCH_STATS in game/shared/stats.qc) and to
	data/matches/<name>.json in the game folder, named after the demo.

	A shot is one trigger pull: a shotgun blast or a rocket counts as one,
	and hits if any of it damages the opponent. Each lightning gun tick is
	a shot. Self damage counts as damage taken but not dealt.
*/

.float rv_stat[MS_COUNT];
.float rv_weapon;			// on a projectile: the WEP_ that fired it
.float rv_hit;				// on a projectile: it has already counted a hit
float stats_firing;			// WEP_ being fired right now, for hitscan hits
float stats_fire_hit;		// that shot hit the opponent
float stats_recording;		// a demo is being recorded
var float autocvar_rv_record = 1;	// 0 turns match recording off
string stats_name;			// the match's demo and stats file name

float() MatchStats_Counting =
{
	return rv_match_state == MATCH_PLAYING || rv_match_state == MATCH_OVERTIME;
};

void(entity e) MatchStats_Reset =
{
	local float i;

	for (i = 0; i < MS_COUNT; i = i + 1)
		e.rv_stat[i] = 0;
};

// Before and after the weapon code fires a shot.
void(float wep) MatchStats_FireStart =
{
	stats_firing = wep;
	stats_fire_hit = FALSE;
};

void() MatchStats_FireEnd =
{
	if (stats_firing && MatchStats_Counting())
	{
		self.rv_stat[MS_SHOTS + stats_firing - 1] = self.rv_stat[MS_SHOTS + stats_firing - 1] + 1;
		if (stats_fire_hit)
			self.rv_stat[MS_HITS + stats_firing - 1] = self.rv_stat[MS_HITS + stats_firing - 1] + 1;
	}
	stats_firing = 0;
};

// From T_Damage, with the health and armor the hit actually took.
void(entity targ, entity inflictor, entity attacker, float damage) MatchStats_Damage =
{
	if (!MatchStats_Counting() || targ.classname != "player")
		return;
	targ.rv_stat[MS_DAMAGE_TAKEN] = targ.rv_stat[MS_DAMAGE_TAKEN] + damage;
	if (attacker == targ || attacker.classname != "player")
		return;
	attacker.rv_stat[MS_DAMAGE_DEALT] = attacker.rv_stat[MS_DAMAGE_DEALT] + damage;
	if (inflictor == attacker)
		stats_fire_hit = TRUE;	// a hitscan shot: MatchStats_FireEnd counts it
	else if (inflictor.rv_weapon && !inflictor.rv_hit)
	{
		inflictor.rv_hit = TRUE;
		attacker.rv_stat[MS_HITS + inflictor.rv_weapon - 1] = attacker.rv_stat[MS_HITS + inflictor.rv_weapon - 1] + 1;
	}
};

// A projectile's shot is counted when it is fired; its hit when it lands.
void(entity missile) MatchStats_Missile =
{
	missile.rv_weapon = stats_firing;
	if (MatchStats_Counting())
		self.rv_stat[MS_SHOTS + stats_firing - 1] = self.rv_stat[MS_SHOTS + stats_firing - 1] + 1;
	stats_firing = 0;	// so MatchStats_FireEnd doesn't count it again
};

void(entity attacker, entity targ) MatchStats_Frag =
{
	if (!MatchStats_Counting())
		return;
	targ.rv_stat[MS_DEATHS] = targ.rv_stat[MS_DEATHS] + 1;
	if (attacker == targ || attacker.classname != "player")
		targ.rv_stat[MS_FRAGS] = targ.rv_stat[MS_FRAGS] - 1;
	else
		attacker.rv_stat[MS_FRAGS] = attacker.rv_stat[MS_FRAGS] + 1;
};

// From Item_Touch, with what the pickup gave.
void(entity p, entity item, float health, float armor) MatchStats_Pickup =
{
	if (!MatchStats_Counting())
		return;
	p.rv_stat[MS_HEALTH] = p.rv_stat[MS_HEALTH] + max(0, health);
	p.rv_stat[MS_ARMOR] = p.rv_stat[MS_ARMOR] + max(0, armor);
	if (item.classname == "item_health_mega")
		p.rv_stat[MS_MEGAS] = p.rv_stat[MS_MEGAS] + 1;
};

// A player name as it can go in a file name: lower case letters and
// digits only, at most 12 of them (demo names are limited to 64
// characters).
string(string name) MatchStats_FileName =
{
	local float i, c;
	local string out;

	out = "";
	name = strtolower(strdecolorize(name));
	for (i = 0; i < strlen(name) && strlen(out) < 12; i = i + 1)
	{
		c = str2chr(name, i);
		if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))
			out = strcat(out, chr2str(c));
	}
	return out == "" ? "player" : out;
};

// The match starts: clear everyone's stats and start recording.
void() MatchStats_StartMatch =
{
	local entity p;
	local string players;

	players = "";
	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		MatchStats_Reset(p);
		players = strcat(players, players == "" ? "" : "-", MatchStats_FileName(p.netname));
	}
	if (stats_name != "")
		strunzone(stats_name);
	// For example duel_graybox_runner-target_20261024-225901.
	stats_name = strzone(strcat(mapname, "_", players, "_", strftime(TRUE, "%Y%m%d-%H%M%S")));
	if (autocvar_rv_record)
	{
		localcmd("record ", stats_name, "\n");
		stats_recording = TRUE;
	}
};

void(filestream f, string key, float value, float comma) MatchStats_WriteValue =
{
	fputs(f, "      \"", key, "\": ", ftos(value), comma ? ",\n" : "\n");
};

// data/matches/<name>.json: the match and each player's statistics.
void() MatchStats_WriteFile =
{
	local filestream f;
	local entity p;
	local float wep, first;

	f = fopen(strcat("matches/", stats_name, ".json"), FILE_WRITE);
	if (f < 0)
	{
		print("RAVAGE: could not write the match statistics\n");
		return;
	}
	fputs(f, "{\n  \"map\": \"", mapname, "\",\n");
	fputs(f, "  \"date\": \"", strftime(FALSE, "%Y-%m-%dT%H:%M:%SZ"), "\",\n");
	fputs(f, "  \"duration\": ", ftos(rint(time - rv_match_start)), ",\n");
	fputs(f, "  \"demo\": \"", stats_recording ? strcat("demos/", stats_name, ".mvd") : "", "\",\n");
	fputs(f, "  \"players\": [\n");
	first = TRUE;
	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		fputs(f, first ? "" : ",\n", "    {\n      \"name\": \"", strreplace("\"", "'", p.netname), "\",\n");
		first = FALSE;
		MatchStats_WriteValue(f, "frags", p.rv_stat[MS_FRAGS], TRUE);
		MatchStats_WriteValue(f, "deaths", p.rv_stat[MS_DEATHS], TRUE);
		MatchStats_WriteValue(f, "damage_dealt", p.rv_stat[MS_DAMAGE_DEALT], TRUE);
		MatchStats_WriteValue(f, "damage_taken", p.rv_stat[MS_DAMAGE_TAKEN], TRUE);
		MatchStats_WriteValue(f, "health_picked_up", p.rv_stat[MS_HEALTH], TRUE);
		MatchStats_WriteValue(f, "armor_picked_up", p.rv_stat[MS_ARMOR], TRUE);
		MatchStats_WriteValue(f, "mega_health", p.rv_stat[MS_MEGAS], TRUE);
		fputs(f, "      \"weapons\": {\n");
		for (wep = 1; wep <= WEP_COUNT; wep = wep + 1)
			fputs(f, "        \"", W_Name(wep), "\": { \"shots\": ", ftos(p.rv_stat[MS_SHOTS + wep - 1]),
				strcat(", \"hits\": ", ftos(p.rv_stat[MS_HITS + wep - 1]), " }", wep < WEP_COUNT ? ",\n" : "\n"));
		fputs(f, "      }\n    }");
	}
	fputs(f, "\n  ]\n}\n");
	fclose(f);
	print("RAVAGE: match statistics in data/matches/", stats_name, ".json\n");
};

// The match is over: send everyone the statistics and save them.
void() MatchStats_EndMatch =
{
	local entity p;
	local float i, count, duration;

	duration = rint(time - rv_match_start);
	count = 0;
	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
		count = count + 1;
	WriteByte(MSG_MULTICAST, SVC_CGAMEPACKET);
	WriteByte(MSG_MULTICAST, EV_MATCH_STATS);
	WriteByte(MSG_MULTICAST, count);
	for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
	{
		p.rv_stat[MS_DURATION] = duration;
		WriteByte(MSG_MULTICAST, num_for_edict(p) - 1);
		for (i = 0; i < MS_COUNT; i = i + 1)
			WriteShort(MSG_MULTICAST, p.rv_stat[i]);
	}
	multicast('0 0 0', MULTICAST_ALL_R);
	MatchStats_WriteFile();
};

// A few seconds into the scoreboard, so the demo shows it.
void() MatchStats_Frame =
{
	if (stats_recording && rv_match_state == MATCH_OVER && time >= rv_intermission + 3)
	{
		localcmd("stop\n");
		stats_recording = FALSE;
	}
};
