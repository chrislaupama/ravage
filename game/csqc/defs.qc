/*
	Client game code settings. The client only ever runs in RAVAGE's own
	engine, so it may use FTE's extended instruction set (doubles, for
	precise timing).
*/

#pragma target fte

// The player whose view and HUD are shown: yourself, or while playing
// back a match demo (an MVD), the player the view follows.
float() PlayerWatched =
{
	if (isdemo() == 2 && player_localentnum > 0)
		return player_localentnum - 1;
	return player_localnum;
};

// A stat of that player. A match demo has every player's stats.
float(float stat) PlayerStat =
{
	if (isdemo() == 2 && player_localentnum > 0)
		return getplayerstat(player_localentnum - 1, stat, EV_FLOAT);
	return getstatf(stat);
};

// Defined after hud.qc, which uses them.
float ms_players;
void(vector pos) Hud_MatchStats;
