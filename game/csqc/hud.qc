/*
	The HUD: health, armor, ammo, the weapon bar and frags. A placeholder
	layout in the engine's built-in font, scaled to the screen height.
*/

const vector HUD_PANEL = '0.05 0.06 0.08';
const vector HUD_LABEL = '0.62 0.66 0.72';
const vector HUD_WHITE = '1 1 1';
const vector HUD_LOW = '1 0.32 0.26';		// low health or no ammo
const vector HUD_OVER = '0.55 0.9 1';		// health above 100
const vector HUD_ARMOR = '1 0.82 0.3';
const vector HUD_ACCENT = '1 0.55 0.15';	// selected weapon

float hud_unit;		// one unit of HUD layout, 1/360 of the screen height

void(vector pos, vector size) Hud_Panel =
{
	drawfill(pos, size, HUD_PANEL, 0.6);
};

// Text of the given height. align 0 is left, 1 right, 0.5 centred.
void(vector pos, string text, float height, vector rgb, float align) Hud_Text =
{
	pos_x = pos_x - stringwidth(text, FALSE, [height, height]) * align;
	drawstring(pos, text, [height, height], rgb, 1);
};

// A label above a big number, as in "HEALTH 100".
void(vector pos, string label, float value, vector rgb, float align) Hud_Counter =
{
	local float u = hud_unit;

	Hud_Text(pos, label, 7 * u, HUD_LABEL, align);
	Hud_Text(pos + [0, 10 * u], ftos(value), 22 * u, rgb, align);
};

void(vector screen) Hud_Status =
{
	local float u = hud_unit;
	local float health, armor, wep, ammo;
	local vector rgb;

	health = getstatf(STAT_RV_HEALTH);
	armor = getstatf(STAT_RV_ARMOR);
	wep = getstatf(STAT_RV_WEAPON);
	ammo = getstatf(STAT_RV_AMMO + wep - 1);

	Hud_Panel([10 * u, screen_y - 50 * u], [180 * u, 40 * u]);
	rgb = HUD_WHITE;
	if (health <= 25)
		rgb = HUD_LOW;
	else if (health > 100)
		rgb = HUD_OVER;
	Hud_Counter([18 * u, screen_y - 45 * u], "HEALTH", max(health, 0), rgb, 0);
	Hud_Counter([100 * u, screen_y - 45 * u], "ARMOR", armor, armor > 0 ? HUD_ARMOR : HUD_LABEL, 0);

	if (wep >= WEP_SHOTGUN && wep <= WEP_COUNT)
	{
		Hud_Panel([screen_x - 190 * u, screen_y - 50 * u], [180 * u, 40 * u]);
		Hud_Counter([screen_x - 18 * u, screen_y - 45 * u], strtoupper(W_Name(wep)), ammo,
			ammo > 0 ? HUD_WHITE : HUD_LOW, 1);
	}
};

// One slot per weapon: its number, and its ammo if the player holds it.
void(vector screen) Hud_WeaponBar =
{
	local float u = hud_unit;
	local float wep, current, items, ammo;
	local vector pos, size;

	current = getstatf(STAT_RV_WEAPON);
	items = getstatf(STAT_RV_ITEMS);
	size = [26 * u, 24 * u];
	pos = [screen_x * 0.5 - (WEP_COUNT * 28 * u - 2 * u) * 0.5, screen_y - 34 * u];
	for (wep = WEP_SHOTGUN; wep <= WEP_COUNT; wep = wep + 1)
	{
		ammo = getstatf(STAT_RV_AMMO + wep - 1);
		if (wep == current)
			drawfill(pos, size, HUD_ACCENT, 0.75);
		else
			Hud_Panel(pos, size);
		Hud_Text(pos + [2 * u, 2 * u], ftos(wep), 7 * u, HUD_LABEL, 0);
		if (items & W_ItemBit(wep))
			Hud_Text(pos + [size_x - 2 * u, 12 * u], ftos(ammo), 9 * u, ammo > 0 ? HUD_WHITE : HUD_LOW, 1);
		pos_x = pos_x + 28 * u;
	}
};

void(vector screen) Hud_Frags =
{
	local float u = hud_unit;

	Hud_Panel([screen_x - 70 * u, 10 * u], [60 * u, 34 * u]);
	Hud_Counter([screen_x - 18 * u, 14 * u], "FRAGS", getplayerkeyfloat(player_localnum, "frags"), HUD_WHITE, 1);
};

// Every player and their frags, most first.
void(vector screen) Hud_Scoreboard =
{
	local float u = hud_unit;
	local float i, best, best_frags, frags, rows;
	local float shown[32];
	local vector pos;

	pos = [screen_x * 0.5, screen_y * 0.3];
	Hud_Text(pos, "MATCH OVER", 20 * u, HUD_ACCENT, 0.5);
	pos_y = pos_y + 34 * u;
	for (rows = 0; rows < min(maxclients, 32); rows = rows + 1)
	{
		best = -1;
		best_frags = -100000;
		for (i = 0; i < min(maxclients, 32); i = i + 1)
		{
			if (shown[i] || getplayerkeyvalue(i, "name") == "")
				continue;
			frags = getplayerkeyfloat(i, "frags");
			if (frags > best_frags)
			{
				best = i;
				best_frags = frags;
			}
		}
		if (best < 0)
			break;
		shown[best] = TRUE;
		Hud_Panel(pos - [110 * u, 2 * u], [220 * u, 16 * u]);
		Hud_Text(pos - [102 * u, 0], getplayerkeyvalue(best, "name"), 11 * u, best == player_localnum ? HUD_ACCENT : HUD_WHITE, 0);
		Hud_Text(pos + [102 * u, 0], ftos(best_frags), 11 * u, HUD_WHITE, 1);
		pos_y = pos_y + 18 * u;
	}
};

void(vector screen) Hud_Draw =
{
	hud_unit = screen_y / 360;
	if (intermission)
	{
		Hud_Scoreboard(screen);
		return;
	}
	Hud_Frags(screen);
	Hud_Status(screen);
	Hud_WeaponBar(screen);
	if (getstatf(STAT_RV_HEALTH) <= 0)
		Hud_Text([screen_x * 0.5, screen_y * 0.42], "PRESS FIRE TO RESPAWN", 10 * hud_unit, HUD_WHITE, 0.5);
};
