/*
	Weapons: selection, firing and projectiles.

	Hitscan traces use MOVE_LAGGED, so the server's lag compensation
	(sv_antilag) checks hits against where targets were on the shooter's
	screen.
*/

float(entity e, float wep) W_Ammo =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		return e.ammo_shells;
	case WEP_MACHINEGUN:	return e.ammo_bullets;
	case WEP_ROCKET:		return e.ammo_rockets;
	case WEP_GRENADE:		return e.ammo_grenades;
	case WEP_LIGHTNING:		return e.ammo_cells;
	default:				return e.ammo_slugs;
	}
};

void(entity e, float wep, float value) W_SetAmmo =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		e.ammo_shells = value; break;
	case WEP_MACHINEGUN:	e.ammo_bullets = value; break;
	case WEP_ROCKET:		e.ammo_rockets = value; break;
	case WEP_GRENADE:		e.ammo_grenades = value; break;
	case WEP_LIGHTNING:		e.ammo_cells = value; break;
	default:				e.ammo_slugs = value; break;
	}
};

float(float wep) W_HasAmmo =
{
	return W_Ammo(self, wep) >= 1;
};

// Seconds between shots.
float(float wep) W_RefireTime =
{
	switch (wep)
	{
	case WEP_SHOTGUN:		return 0.9;
	case WEP_MACHINEGUN:	return 0.1;
	case WEP_ROCKET:		return 0.8;
	case WEP_GRENADE:		return 0.8;
	case WEP_LIGHTNING:		return 0.05;
	default:				return 1.5;
	}
};

// Refreshes the ammo counter and the first-person model after the weapon
// or its ammo changed.
void() W_UpdateCurrentAmmo =
{
	self.currentammo = W_Ammo(self, self.weapon);
	if (!self.deadflag)
		self.weaponmodel = W_ViewModel(self.weapon);
};

float(float wep) W_CanUse =
{
	return (self.items & W_ItemBit(wep)) && W_HasAmmo(wep);
};

// Switch to the best weapon that has ammo, most powerful first.
void() W_SelectBest =
{
	local float wep;

	for (wep = WEP_RAILGUN; wep >= WEP_SHOTGUN; wep = wep - 1)
	{
		if (wep == WEP_GRENADE)	// never auto-switch to grenades
			continue;
		if (W_CanUse(wep))
		{
			self.weapon = wep;
			W_UpdateCurrentAmmo();
			return;
		}
	}
	if (W_CanUse(WEP_GRENADE))
		self.weapon = WEP_GRENADE;
	W_UpdateCurrentAmmo();
};

// Impulses 1 to 6 pick a weapon, 10 and 12 cycle through them.
void() W_Impulse =
{
	local float wep, i;

	if (self.impulse >= 1 && self.impulse <= WEP_COUNT)
	{
		if (W_CanUse(self.impulse))
			self.weapon = self.impulse;
		else
			sound(self, CHAN_ITEM, "weapons/noammo.wav", 1, ATTN_IDLE);
	}
	else if (self.impulse == 10 || self.impulse == 12)
	{
		wep = self.weapon;
		for (i = 0; i < WEP_COUNT; i = i + 1)
		{
			if (self.impulse == 10)
				wep = wep % WEP_COUNT + 1;
			else
				wep = (wep + WEP_COUNT - 2) % WEP_COUNT + 1;
			if (W_CanUse(wep))
			{
				self.weapon = wep;
				break;
			}
		}
	}
	self.impulse = 0;
	W_UpdateCurrentAmmo();
};

vector() W_Origin =
{
	return self.origin + self.view_ofs;
};

// One hitscan bullet or pellet. spread is the cone half-width.
void(float damage, float spread, float range) W_Hitscan =
{
	local vector dir, src;

	src = W_Origin();
	dir = v_forward + (random() * 2 - 1) * spread * v_right + (random() * 2 - 1) * spread * v_up;
	traceline(src, src + dir * range, MOVE_LAGGED, self);
	if (trace_fraction == 1)
		return;
	if (trace_ent.takedamage)
		T_Damage(trace_ent, self, self, damage);
	else
		te_gunshot(trace_endpos - dir * 4, 1);
};

void() Missile_Explode =
{
	sound(self, CHAN_AUTO, "weapons/explode.wav", 1, ATTN_NORM);
	T_RadiusDamage(self, self.owner, self.rv_splash_damage, self.rv_splash_radius, other);
	te_explosion(self.origin);
	remove(self);
};

void() Rocket_Touch =
{
	if (other == self.owner)
		return;
	if (pointcontents(self.origin) == CONTENT_SKY)
	{
		remove(self);
		return;
	}
	if (other.takedamage)
		T_Damage(other, self, self.owner, self.dmg);
	// Pull the blast point back off the wall so splash reaches the room.
	self.origin = self.origin - normalize(self.velocity) * 8;
	Missile_Explode();
};

void() Grenade_Touch =
{
	if (other == self.owner)
		return;
	if (other.takedamage == DAMAGE_AIM)
	{
		Missile_Explode();
		return;
	}
	if (self.velocity == '0 0 0')
		self.avelocity = '0 0 0';
	else
		sound(self, CHAN_BODY, "weapons/bounce.wav", 1, ATTN_NORM);
};

entity(float speed, string model_name) W_SpawnMissile =
{
	local entity missile;

	missile = spawn();
	setmodel(missile, model_name);
	missile.owner = self;
	missile.solid = SOLID_BBOX;
	missile.velocity = v_forward * speed;
	missile.angles = vectoangles(missile.velocity);
	setsize(missile, '0 0 0', '0 0 0');
	setorigin(missile, W_Origin() + v_forward * 8 + '0 0 -8');
	newmis = missile;	// runs this frame, which hides latency
	return missile;
};

void() W_FireRocket =
{
	local entity missile;

	missile = W_SpawnMissile(1000, MDL_ROCKET);
	missile.classname = "rocket";
	missile.movetype = MOVETYPE_FLYMISSILE;
	missile.dmg = 100;
	missile.rv_splash_damage = 120;
	missile.rv_splash_radius = 120;
	missile.touch = Rocket_Touch;
	missile.think = SUB_Remove;
	missile.nextthink = time + 5;
};

void() W_FireGrenade =
{
	local entity missile;

	missile = W_SpawnMissile(700, MDL_GRENADE);
	missile.classname = "grenade";
	missile.movetype = MOVETYPE_BOUNCE;
	missile.velocity_z = missile.velocity_z + 200;
	missile.avelocity = '300 300 300';
	missile.rv_splash_damage = 100;
	missile.rv_splash_radius = 150;
	missile.touch = Grenade_Touch;
	missile.think = Missile_Explode;
	missile.nextthink = time + 2.5;
};

void() W_FireLightning =
{
	local vector src;

	src = W_Origin();
	traceline(src, src + v_forward * 768, MOVE_LAGGED, self);
	if (trace_ent.takedamage)
		T_Damage(trace_ent, self, self, 8);
};

void() W_FireRailgun =
{
	local vector src;

	src = W_Origin();
	traceline(src, src + v_forward * 8192, MOVE_LAGGED, self);
	if (trace_ent.takedamage)
		T_Damage(trace_ent, self, self, 100);
	else if (trace_fraction < 1)
		te_gunshot(trace_endpos - v_forward * 4, 4);
};

// Fire the given weapon once, if the player has it and its ammo.
void(float wep) W_Fire =
{
	local float i;

	if (!W_CanUse(wep))
		return;
	W_SetAmmo(self, wep, W_Ammo(self, wep) - 1);
	self.attack_finished = time + W_RefireTime(wep);
	self.rv_fire_time = time;
	makevectors(self.v_angle);
	// The lightning gun hums instead of restarting its sound every shot.
	if (wep == WEP_LIGHTNING)
		sound(self, CHAN_WEAPON, W_FireSound(wep), 1, ATTN_NORM, 0, SOUNDFLAG_NOREPLACE);
	else
		sound(self, CHAN_WEAPON, W_FireSound(wep), 1, ATTN_NORM);

	switch (wep)
	{
	case WEP_SHOTGUN:
		for (i = 0; i < 12; i = i + 1)
			W_Hitscan(6, 0.08, 2048);
		break;
	case WEP_MACHINEGUN:
		W_Hitscan(8, 0.02, 8192);
		break;
	case WEP_ROCKET:
		W_FireRocket();
		break;
	case WEP_GRENADE:
		W_FireGrenade();
		break;
	case WEP_LIGHTNING:
		W_FireLightning();
		break;
	case WEP_RAILGUN:
		W_FireRailgun();
		break;
	}
	W_UpdateCurrentAmmo();
	if (!W_HasAmmo(self.weapon))
		W_SelectBest();
};

// Called every frame for each living player, after movement.
void() W_Frame =
{
	if (self.impulse)
		W_Impulse();
	if (self.button0 && time >= self.attack_finished)
		W_Fire(self.weapon);
};
