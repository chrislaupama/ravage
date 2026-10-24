/*
	RAVAGE server game code: world setup.

	This is the minimal game code needed to load a map, spawn players and
	check the map is sound. Weapons, pickups and scoring come in step 5.
*/

// Counters filled in by the spawn functions, checked by the self-test.
float rv_trigger_count;

// Set on pickups so the self-test can find them.
.float rv_is_item;

void() SelfTest_Frame;

void() main =
{
};

void() worldspawn =
{
	// Style 0 is normal, steady light. Without it the map renders black.
	lightstyle(0, "m");
};

void() StartFrame =
{
	SelfTest_Frame();
};
