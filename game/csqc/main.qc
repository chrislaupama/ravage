/*
	RAVAGE client game code: entry points the engine calls.
*/

void(float apilevel, string enginename, float engineversion) CSQC_Init =
{
	View_Init();
	Hud_Init();
	registercommand("rv_hudtest", "Print the stats the HUD shows (used by tests/match.sh)");
	registercommand("rv_framebench", "rv_framebench <frames> [players]: time whole frames while turning the view, optionally among running player models (used by tools/bench-map.sh)");
};

float(string cmd) CSQC_ConsoleCommand =
{
	local float wep;

	tokenize(cmd);
	if (argv(0) == "rv_framebench")
	{
		View_StartBench(stof(argv(1)), stof(argv(2)));
		return TRUE;
	}
	if (argv(0) != "rv_hudtest")
		return FALSE;
	wep = getstatf(STAT_RV_WEAPON);
	print(sprintf("RAVAGE hudtest: health=%g armor=%g weapon=%g ammo=%g\n", getstatf(STAT_RV_HEALTH),
		getstatf(STAT_RV_ARMOR), wep, getstatf(STAT_RV_AMMO + wep - 1)));
	return TRUE;
};

void(float vwidth, float vheight, float notmenu) CSQC_UpdateView =
{
	View_Draw();
	Hud_Draw([vwidth, vheight]);
	Hud_Announcer();
};

// F3 readies up (or back down) during warmup, like typing "ready".
float(float evtype, float scanx, float chary, float devid) CSQC_InputEvent =
{
	if (evtype != IE_KEYDOWN || scanx != K_F3 || getstatf(STAT_RV_MATCH_STATE) > MATCH_COUNTDOWN)
		return FALSE;
	localcmd(getstatf(STAT_RV_READY) ? "cmd notready\n" : "cmd ready\n");
	return TRUE;
};

// Declared __used by the engine definitions, so it needs a body. Input is
// left as the engine sends it.
void() CSQC_Input_Frame =
{
};
