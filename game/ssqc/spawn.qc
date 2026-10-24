/*
	Spawn points and other point entities used by the map tools.
	See tools/trenchbroom/RAVAGE/ravage.fgd for the editor definitions.
*/

const vector VEC_HULL_MIN = '-16 -16 -24';
const vector VEC_HULL_MAX = '16 16 32';

void() info_player_deathmatch =
{
};

// Fallback spawn point, used only when a map has no deathmatch spawns.
void() info_player_start =
{
};

// Camera position for the end-of-match scoreboard.
void() info_intermission =
{
};

// Destination for trigger_teleport.
void() info_teleport_destination =
{
};

// Aim point for trigger_push and other entities that target a position.
void() target_position =
{
};

// Lights are only used by the light compiler.
void() light =
{
	remove(self);
};
