/*
	Weapons, shared by the server game code and the client HUD.
*/

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

// Bit in .items for a weapon.
float(float wep) W_ItemBit =
{
	return 1 << (wep - 1);
};

string(float wep) W_Name =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		return "Shotgun";
	case WEP_MACHINEGUN:	return "Machine Gun";
	case WEP_ROCKET:		return "Rocket Launcher";
	case WEP_GRENADE:		return "Grenade Launcher";
	case WEP_LIGHTNING:		return "Lightning Gun";
	default:				return "Railgun";
	}
};

// The pickup ("g_") and first-person ("v_") model of a weapon, and its
// firing sound. Plain constants, so the strings outlive the call.
string(float wep) W_WorldModel =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		return "models/g_shotgun.iqm";
	case WEP_MACHINEGUN:	return "models/g_machinegun.iqm";
	case WEP_ROCKET:		return "models/g_rocketlauncher.iqm";
	case WEP_GRENADE:		return "models/g_grenadelauncher.iqm";
	case WEP_LIGHTNING:		return "models/g_lightning.iqm";
	default:				return "models/g_railgun.iqm";
	}
};

string(float wep) W_ViewModel =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		return "models/v_shotgun.iqm";
	case WEP_MACHINEGUN:	return "models/v_machinegun.iqm";
	case WEP_ROCKET:		return "models/v_rocketlauncher.iqm";
	case WEP_GRENADE:		return "models/v_grenadelauncher.iqm";
	case WEP_LIGHTNING:		return "models/v_lightning.iqm";
	default:				return "models/v_railgun.iqm";
	}
};

string(float wep) W_FireSound =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		return "weapons/shotgun.wav";
	case WEP_MACHINEGUN:	return "weapons/machinegun.wav";
	case WEP_ROCKET:		return "weapons/rocketlauncher.wav";
	case WEP_GRENADE:		return "weapons/grenadelauncher.wav";
	case WEP_LIGHTNING:		return "weapons/lightning.wav";
	default:				return "weapons/railgun.wav";
	}
};
