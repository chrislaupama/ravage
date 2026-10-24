/*
	Pickups: weapons, ammunition, health and armor.

	Every pickup returns after a fixed delay, so item timing is
	predictable. A map can override the delay with the "wait" key. There
	are no models yet, so pickups are invisible until placeholder models
	arrive.
*/

void() Item_Respawn =
{
	self.solid = SOLID_TRIGGER;
	self.model = self.mdl;
	setorigin(self, self.origin);
};

void() Item_Touch =
{
	if (other.classname != "player" || other.health <= 0 || rv_intermission)
		return;

	rv_taken = FALSE;
	self.rv_give();
	if (!rv_taken)
		return;

	sprint(other, PRINT_LOW, "You got ", self.netname, "\n");
	self.solid = SOLID_NOT;
	self.model = "";
	self.think = Item_Respawn;
	self.nextthink = time + self.rv_respawn_delay;
	setorigin(self, self.origin);
};

void(string name, float delay, void() give) Item_Setup =
{
	self.netname = name;
	self.rv_give = give;
	self.rv_is_item = TRUE;
	self.rv_respawn_delay = self.wait > 0 ? self.wait : delay;
	self.mdl = self.model;
	self.solid = SOLID_TRIGGER;
	self.movetype = MOVETYPE_NONE;
	self.touch = Item_Touch;
	setsize(self, VEC_ITEM_MIN, VEC_ITEM_MAX);
	setorigin(self, self.origin);
};

// Adds amount to a field without going over max. Marks the pickup taken
// if anything changed.
void(entity e, .float fld, float amount, float maximum) Give_Capped =
{
	if (e.fld >= maximum)
		return;
	e.fld = min(e.fld + amount, maximum);
	rv_taken = TRUE;
};

//
// Weapons
//

void(float wep, .float ammofld, float ammo, float maxammo) Give_Weapon =
{
	local entity oldself;
	local float had;

	had = other.items & W_ItemBit(wep);
	other.items = other.items | W_ItemBit(wep);
	other.ammofld = min(max(other.ammofld, 0) + ammo, maxammo);
	rv_taken = TRUE;

	// Switch to a newly picked up weapon, like most arena shooters.
	oldself = self;
	self = other;
	if (!had)
		self.weapon = wep;
	W_UpdateCurrentAmmo();
	self = oldself;
};

void() Give_Shotgun = { Give_Weapon(WEP_SHOTGUN, ammo_shells, 10, 100); };
void() Give_Machinegun = { Give_Weapon(WEP_MACHINEGUN, ammo_bullets, 50, 200); };
void() Give_Rocket = { Give_Weapon(WEP_ROCKET, ammo_rockets, 10, 100); };
void() Give_Grenade = { Give_Weapon(WEP_GRENADE, ammo_grenades, 10, 100); };
void() Give_Lightning = { Give_Weapon(WEP_LIGHTNING, ammo_cells, 100, 200); };
void() Give_Railgun = { Give_Weapon(WEP_RAILGUN, ammo_slugs, 10, 50); };

void() weapon_shotgun = { Item_Setup("Shotgun", 15, Give_Shotgun); };
void() weapon_machinegun = { Item_Setup("Machine Gun", 15, Give_Machinegun); };
void() weapon_rocketlauncher = { Item_Setup("Rocket Launcher", 15, Give_Rocket); };
void() weapon_grenadelauncher = { Item_Setup("Grenade Launcher", 15, Give_Grenade); };
void() weapon_lightning = { Item_Setup("Lightning Gun", 15, Give_Lightning); };
void() weapon_railgun = { Item_Setup("Railgun", 15, Give_Railgun); };

//
// Ammunition
//

void(.float fld, float amount, float maximum) Give_Ammo =
{
	local entity oldself;

	Give_Capped(other, fld, amount, maximum);
	oldself = self;
	self = other;
	W_UpdateCurrentAmmo();
	self = oldself;
};

void() Give_Shells = { Give_Ammo(ammo_shells, 10, 100); };
void() Give_Bullets = { Give_Ammo(ammo_bullets, 50, 200); };
void() Give_Rockets = { Give_Ammo(ammo_rockets, 5, 100); };
void() Give_Grenades = { Give_Ammo(ammo_grenades, 5, 100); };
void() Give_Cells = { Give_Ammo(ammo_cells, 50, 200); };
void() Give_Slugs = { Give_Ammo(ammo_slugs, 5, 50); };

void() item_ammo_shells = { Item_Setup("shells", 20, Give_Shells); };
void() item_ammo_bullets = { Item_Setup("bullets", 20, Give_Bullets); };
void() item_ammo_rockets = { Item_Setup("rockets", 20, Give_Rockets); };
void() item_ammo_grenades = { Item_Setup("grenades", 20, Give_Grenades); };
void() item_ammo_cells = { Item_Setup("cells", 20, Give_Cells); };
void() item_ammo_slugs = { Item_Setup("slugs", 20, Give_Slugs); };

//
// Health. Small health and mega health go above 100; anything over 100
// ticks down by 1 per second.
//

void() Give_HealthSmall = { Give_Capped(other, health, 5, 200); };
void() Give_Health = { Give_Capped(other, health, 25, 100); };
void() Give_HealthLarge = { Give_Capped(other, health, 50, 100); };
void() Give_HealthMega = { Give_Capped(other, health, 100, 200); };

void() item_health_small = { Item_Setup("5 health", 30, Give_HealthSmall); };
void() item_health = { Item_Setup("25 health", 30, Give_Health); };
void() item_health_large = { Item_Setup("50 health", 30, Give_HealthLarge); };
void() item_health_mega = { Item_Setup("Mega Health", 35, Give_HealthMega); };

//
// Armor. Each type absorbs a share of damage. An armor pickup replaces
// what the player wears when it offers more protection (type times amount),
// as in QuakeWorld; shards add 5 to whatever is worn.
//

void(float type, float amount) Give_Armor =
{
	if (type * amount <= other.armortype * other.armorvalue)
		return;
	other.armortype = type;
	other.armorvalue = amount;
	rv_taken = TRUE;
};

void() Give_ArmorShard =
{
	if (other.armortype == 0)
		other.armortype = 0.3;
	Give_Capped(other, armorvalue, 5, 200);
};
void() Give_ArmorLight = { Give_Armor(0.3, 100); };
void() Give_ArmorMedium = { Give_Armor(0.6, 150); };
void() Give_ArmorHeavy = { Give_Armor(0.8, 200); };

void() item_armor_shard = { Item_Setup("armor shard", 25, Give_ArmorShard); };
void() item_armor_light = { Item_Setup("Light Armor", 25, Give_ArmorLight); };
void() item_armor_medium = { Item_Setup("Medium Armor", 25, Give_ArmorMedium); };
void() item_armor_heavy = { Item_Setup("Heavy Armor", 25, Give_ArmorHeavy); };

// Brush entities that are simply part of the level.
void() func_wall =
{
	self.solid = SOLID_BSP;
	self.movetype = MOVETYPE_PUSH;
	setmodel(self, self.model);
};

void() func_illusionary =
{
	setmodel(self, self.model);
	makestatic(self);
};
