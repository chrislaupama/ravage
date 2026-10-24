/*
	RAVAGE server game code: world setup and the per-frame hook.
*/

void() main =
{
};

void() SUB_Remove =
{
	remove(self);
};

void() worldspawn =
{
	// Style 0 is normal, steady light. Without it the map renders black.
	lightstyle(0, "m");
	rv_intermission = 0;
};

void() StartFrame =
{
	Rules_Frame();
	SelfTest_Frame();
	MatchTest_Frame();
};
