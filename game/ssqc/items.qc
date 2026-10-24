/*
	Pickups and triggers.

	For now these only register themselves so the map loads cleanly and the
	self-test can check their placement. Pickup and trigger behaviour is
	added in step 5.
*/

void() Item_Placeholder =
{
	self.solid = SOLID_NOT;
	setsize(self, '-16 -16 0', '16 16 32');
	setorigin(self, self.origin);
	self.rv_is_item = TRUE;
};

void() weapon_shotgun = { Item_Placeholder(); };
void() weapon_machinegun = { Item_Placeholder(); };
void() weapon_rocketlauncher = { Item_Placeholder(); };
void() weapon_grenadelauncher = { Item_Placeholder(); };
void() weapon_lightning = { Item_Placeholder(); };
void() weapon_railgun = { Item_Placeholder(); };

void() item_ammo_shells = { Item_Placeholder(); };
void() item_ammo_bullets = { Item_Placeholder(); };
void() item_ammo_rockets = { Item_Placeholder(); };
void() item_ammo_grenades = { Item_Placeholder(); };
void() item_ammo_cells = { Item_Placeholder(); };
void() item_ammo_slugs = { Item_Placeholder(); };

void() item_health_small = { Item_Placeholder(); };
void() item_health = { Item_Placeholder(); };
void() item_health_large = { Item_Placeholder(); };
void() item_health_mega = { Item_Placeholder(); };

void() item_armor_shard = { Item_Placeholder(); };
void() item_armor_light = { Item_Placeholder(); };
void() item_armor_medium = { Item_Placeholder(); };
void() item_armor_heavy = { Item_Placeholder(); };

// Brush triggers: keep the collision shape, never draw it.
void() Trigger_Placeholder =
{
	self.solid = SOLID_TRIGGER;
	self.movetype = MOVETYPE_NONE;
	setmodel(self, self.model);
	self.modelindex = 0;
	self.model = "";
	rv_trigger_count = rv_trigger_count + 1;
};

void() trigger_push = { Trigger_Placeholder(); };
void() trigger_teleport = { Trigger_Placeholder(); };

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
