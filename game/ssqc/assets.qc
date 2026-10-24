/*
	Models and sounds the server uses, made by tools/assets/. The player and weapon
	models are LibreQuake's (BSD-3); everything else is original.
*/

const string MDL_PLAYER = "models/player.iqm";
const string MDL_ROCKET = "models/rocket.iqm";
const string MDL_GRENADE = "models/grenade.iqm";

// Called from worldspawn: everything a match can show or play.
void() Assets_Precache =
{
	local float wep;

	precache_model(MDL_PLAYER);
	precache_model(MDL_ROCKET);
	precache_model(MDL_GRENADE);
	for (wep = WEP_SHOTGUN; wep <= WEP_COUNT; wep = wep + 1)
	{
		precache_model(W_WorldModel(wep));
		precache_model(W_ViewModel(wep));
		precache_sound(W_FireSound(wep));
	}
	precache_model("models/health_small.iqm");
	precache_model("models/health.iqm");
	precache_model("models/health_large.iqm");
	precache_model("models/health_mega.iqm");
	precache_model("models/armor_shard.iqm");
	precache_model("models/armor_light.iqm");
	precache_model("models/armor_medium.iqm");
	precache_model("models/armor_heavy.iqm");
	precache_model("models/ammo_shells.iqm");
	precache_model("models/ammo_bullets.iqm");
	precache_model("models/ammo_rockets.iqm");
	precache_model("models/ammo_grenades.iqm");
	precache_model("models/ammo_cells.iqm");
	precache_model("models/ammo_slugs.iqm");

	precache_sound("weapons/explode.wav");
	precache_sound("weapons/bounce.wav");
	precache_sound("weapons/noammo.wav");
	precache_sound("items/weapon.wav");
	precache_sound("items/ammo.wav");
	precache_sound("items/health.wav");
	precache_sound("items/mega.wav");
	precache_sound("items/armor.wav");
	precache_sound("items/respawn.wav");
	precache_sound("player/pain.wav");
	precache_sound("player/death.wav");
	precache_sound("misc/teleport.wav");
	precache_sound("misc/jumppad.wav");
};
