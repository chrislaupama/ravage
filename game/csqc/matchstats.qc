/*
	Post-match statistics on the scoreboard. The server sends every
	player's statistics once, when the match ends (EV_MATCH_STATS in
	game/shared/stats.qc).
*/

// ms_players (defs.qc): players in the last EV_MATCH_STATS
float ms_player[2];			// their player numbers
float ms_values[40];		// their values: player slot * MS_COUNT + MS_ number

void() MatchStats_Read =
{
	local float i, k, count, slot;

	count = readbyte();
	ms_players = min(count, 2);
	for (i = 0; i < count; i = i + 1)
	{
		slot = readbyte();
		if (i < 2)
			ms_player[i] = slot;
		for (k = 0; k < MS_COUNT; k = k + 1)
		{
			if (i < 2)
				ms_values[i * MS_COUNT + k] = readshort();
			else
				readshort();
		}
	}
	print(sprintf("Match statistics received for %g players\n", count));
	// Your own column first.
	if (ms_players == 2 && ms_player[1] == player_localnum)
	{
		ms_player[1] = ms_player[0];
		ms_player[0] = player_localnum;
		for (k = 0; k < MS_COUNT; k = k + 1)
		{
			i = ms_values[k];
			ms_values[k] = ms_values[MS_COUNT + k];
			ms_values[MS_COUNT + k] = i;
		}
	}
};

void() CSQC_Parse_Event =
{
	local float ev;

	ev = readbyte();
	if (ev == EV_MATCH_STATS)
		MatchStats_Read();
	else
		error(sprintf("unknown event %g from the server", ev));
};

// "45% (9/20)", or "-" without a shot.
string(float hits, float shots) MatchStats_Accuracy =
{
	if (!shots)
		return "-";
	return sprintf("%g%% (%g/%g)", floor(hits * 100 / shots + 0.5), hits, shots);
};

void(vector pos, string label, string a, string b) MatchStats_Row =
{
	local float u = hud_unit;

	Hud_Text(pos - [125 * u, 0], label, 7 * u, HUD_LABEL, 0);
	Hud_Text(pos + [55 * u, 0], a, 7 * u, HUD_WHITE, 1);
	if (ms_players > 1)
		Hud_Text(pos + [125 * u, 0], b, 7 * u, HUD_WHITE, 1);
};

void(vector pos, string label, float k) MatchStats_ValueRow =
{
	MatchStats_Row(pos, label, ftos(ms_values[k]), ftos(ms_values[MS_COUNT + k]));
};

// The statistics table, centred on pos_x, from pos_y down.
void(vector pos) Hud_MatchStats =
{
	local float u = hud_unit;
	local float wep, rows;

	if (!ms_players)
		return;
	rows = 7;
	for (wep = 1; wep <= WEP_COUNT; wep = wep + 1)
		if (ms_values[MS_SHOTS + wep - 1] || ms_values[MS_COUNT + MS_SHOTS + wep - 1])
			rows = rows + 1;
	// Darker than other panels: it is a lot of small text.
	drawfill(pos - [132 * u, 5 * u], [264 * u, (rows * 10 + 20) * u], HUD_PANEL, 0.85);
	Hud_Text(pos - [125 * u, 0], sprintf("MATCH STATS  %s", Hud_Clock(ms_values[MS_DURATION])), 7 * u, HUD_ACCENT, 0);
	Hud_Text(pos + [55 * u, 0], getplayerkeyvalue(ms_player[0], "name"), 7 * u, HUD_ACCENT, 1);
	if (ms_players > 1)
		Hud_Text(pos + [125 * u, 0], getplayerkeyvalue(ms_player[1], "name"), 7 * u, HUD_ACCENT, 1);
	pos_y = pos_y + 14 * u;
	MatchStats_ValueRow(pos, "Frags", MS_FRAGS);
	pos_y = pos_y + 10 * u;
	MatchStats_ValueRow(pos, "Deaths", MS_DEATHS);
	pos_y = pos_y + 10 * u;
	MatchStats_ValueRow(pos, "Damage dealt", MS_DAMAGE_DEALT);
	pos_y = pos_y + 10 * u;
	MatchStats_ValueRow(pos, "Damage taken", MS_DAMAGE_TAKEN);
	pos_y = pos_y + 10 * u;
	MatchStats_ValueRow(pos, "Health picked up", MS_HEALTH);
	pos_y = pos_y + 10 * u;
	MatchStats_ValueRow(pos, "Armor picked up", MS_ARMOR);
	pos_y = pos_y + 10 * u;
	MatchStats_ValueRow(pos, "Mega health", MS_MEGAS);
	pos_y = pos_y + 10 * u;
	// Accuracy, for each weapon either player fired.
	for (wep = 1; wep <= WEP_COUNT; wep = wep + 1)
	{
		if (!ms_values[MS_SHOTS + wep - 1] && !ms_values[MS_COUNT + MS_SHOTS + wep - 1])
			continue;
		MatchStats_Row(pos, W_Name(wep),
			MatchStats_Accuracy(ms_values[MS_HITS + wep - 1], ms_values[MS_SHOTS + wep - 1]),
			MatchStats_Accuracy(ms_values[MS_COUNT + MS_HITS + wep - 1], ms_values[MS_COUNT + MS_SHOTS + wep - 1]));
		pos_y = pos_y + 10 * u;
	}
};
