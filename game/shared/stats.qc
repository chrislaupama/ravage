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
