/*
	RAVAGE game definitions: fields, constants and shared prototypes.

	Combat and pickup values are QuakeWorld-style starting points. They will
	be tuned for RAVAGE in playtesting.
*/

const vector VEC_HULL_MIN = '-16 -16 -24';
const vector VEC_HULL_MAX = '16 16 32';
const vector VEC_ITEM_MIN = '-16 -16 0';
const vector VEC_ITEM_MAX = '16 16 32';

// Weapon numbers, also the impulse that selects each weapon.
const float WEP_SHOTGUN = 1;
const float WEP_MACHINEGUN = 2;
const float WEP_ROCKET = 3;
const float WEP_GRENADE = 4;
const float WEP_LIGHTNING = 5;
const float WEP_RAILGUN = 6;
const float WEP_COUNT = 6;

// Bits in .items for the weapons a player holds.
const float IT_SHOTGUN = 1;
const float IT_MACHINEGUN = 2;
const float IT_ROCKET = 4;
const float IT_GRENADE = 8;
const float IT_LIGHTNING = 16;
const float IT_RAILGUN = 32;

// Ammo the engine does not already have a field for.
.float ammo_bullets;
.float ammo_grenades;
.float ammo_slugs;

// Network message targets and the intermission message, as in QuakeWorld.
const float MSG_ALL = 2;
const float SVC_INTERMISSION = 30;

const float DEAD_NO = 0;
const float DEAD_DEAD = 2;

// Map keys used by several entities.
.float speed;
.float dmg;
.float wait;
.string mdl;
.vector mangle;

// Player state.
.float attack_finished;		// time the current weapon can fire again
.float rv_respawn_time;		// earliest time a dead player can respawn
.float rv_mega_decay;		// next time health above 100 ticks down
.float rv_spawn_index;		// spawn point the player last appeared at (selftest)
.vector rv_spawn_origin;

// Pickups.
.float rv_is_item;			// set on every pickup, for the self-test
.float rv_respawn_delay;	// seconds before a taken pickup returns
.void() rv_give;			// applies the pickup to "other", returns via rv_taken
float rv_taken;				// set by rv_give when the pickup was used

// Projectiles.
.float rv_splash_damage;
.float rv_splash_radius;

// Match rules.
float rv_intermission;		// time the match ended, 0 while playing
float rv_intermission_exit;	// time players may leave the scoreboard
entity rv_intermission_spot;

float rv_trigger_count;

// Prototypes for functions defined later.
void() SelfTest_Frame;
void() MatchTest_Frame;
void(entity targ, entity inflictor, entity attacker, float damage) T_Damage;
void(entity inflictor, entity attacker, float damage, float radius, entity ignore) T_RadiusDamage;
void() W_Frame;
void() W_SelectBest;
float(float wep) W_HasAmmo;
void(float wep) W_Fire;
void() Rules_Frame;
void(entity attacker, entity targ) Rules_Frag;
void() PutClientInServer;
