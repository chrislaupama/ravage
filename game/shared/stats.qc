/*
	Stats the server sends each client for its HUD and first-person view.
	The server registers them with clientstat() in Stats_Register; the
	client reads them with getstatf(). Numbers below 32 are the engine's.
*/

const float STAT_RV_HEALTH = 32;
const float STAT_RV_ARMOR = 33;
const float STAT_RV_WEAPON = 34;		// WEP_ number of the held weapon
const float STAT_RV_ITEMS = 35;			// weapons held, IT_ bits
const float STAT_RV_FIRE_TIME = 36;		// server time of the last shot, for recoil
const float STAT_RV_AMMO = 37;			// first of WEP_COUNT ammo stats, one per weapon
const float STAT_RV_READY = 43;			// this player has readied up
const float STAT_RV_MATCH_STATE = 44;	// MATCH_ state, the same for everyone
const float STAT_RV_MATCH_TIME = 45;	// server time the countdown or match clock runs out, 0 for none
const float STAT_RV_MATCH_START = 46;	// server time the match started
const float STAT_RV_READY_COUNT = 47;	// players ready, during warmup
const float STAT_RV_PLAYERS = 48;		// players in the game (not spectators)

// Duel match states (rules.qc).
const float MATCH_WARMUP = 0;		// play freely until both players are ready
const float MATCH_COUNTDOWN = 1;	// both ready: the match starts when the clock runs out
const float MATCH_PLAYING = 2;
const float MATCH_OVERTIME = 3;		// time ran out with the scores tied: next frag wins
const float MATCH_OVER = 4;			// intermission
const float MATCH_PLAYERS = 2;		// a Duel is one on one
const float MATCH_COUNTDOWN_TIME = 5;
