/*
	Damage, armor, knockback and death.
*/

// Splits damage between armor and health. Armor absorbs .armortype of
// each hit while it lasts.
float(entity targ, float damage) Combat_ArmorSave =
{
	local float save;

	save = ceil(damage * targ.armortype);
	if (save >= targ.armorvalue)
	{
		save = targ.armorvalue;
		targ.armortype = 0;
	}
	targ.armorvalue = targ.armorvalue - save;
	return save;
};

void(entity targ, entity attacker) Combat_Killed =
{
	targ.takedamage = DAMAGE_NO;
	targ.deadflag = DEAD_DEAD;
	targ.solid = SOLID_NOT;
	targ.movetype = MOVETYPE_TOSS;
	targ.flags = targ.flags - (targ.flags & FL_ONGROUND);
	targ.view_ofs = '0 0 -8';
	targ.velocity_z = targ.velocity_z + 200;
	targ.weaponmodel = "";
	targ.angles_x = 0;
	targ.angles_z = 80;		// placeholder death pose: fall over sideways
	targ.rv_respawn_time = time + 1;
	sound(targ, CHAN_VOICE, "player/death.wav", 1, ATTN_NORM);
	setsize(targ, '-16 -16 -24', '16 16 -8');
	Rules_Frag(attacker, targ);
};

// Applies damage from inflictor (the rocket, or the attacker itself for
// hitscan) on behalf of attacker.
void(entity targ, entity inflictor, entity attacker, float damage) T_Damage =
{
	local vector dir;
	local float take, save;

	if (!targ.takedamage || rv_intermission)
		return;

	// Knockback, including on yourself, which is what makes rocket jumps.
	if (targ.movetype == MOVETYPE_WALK)
	{
		dir = targ.origin - (inflictor.absmin + inflictor.absmax) * 0.5;
		if (dir != '0 0 0')
			targ.velocity = targ.velocity + normalize(dir) * damage * 8;
	}

	// Self damage is halved, so rocket jumps cost less.
	if (targ == attacker)
		damage = damage * 0.5;

	save = Combat_ArmorSave(targ, damage);
	take = ceil(damage - save);
	targ.dmg_take = targ.dmg_take + take;
	targ.dmg_save = targ.dmg_save + save;
	targ.dmg_inflictor = inflictor;
	targ.health = targ.health - take;

	if (targ.health <= 0)
		Combat_Killed(targ, attacker);
	else if (targ.classname == "player")
		sound(targ, CHAN_VOICE, "player/pain.wav", 1, ATTN_NORM, 0, SOUNDFLAG_NOREPLACE);
};

// Damage everything within radius of the inflictor, falling off linearly
// with distance. ignore takes no damage (the entity hit directly).
void(entity inflictor, entity attacker, float damage, float radius, entity ignore) T_RadiusDamage =
{
	local entity head;
	local vector org;
	local float points;

	for (head = findradius(inflictor.origin, radius); head; head = head.chain)
	{
		if (head == ignore || !head.takedamage)
			continue;
		org = head.origin + (head.mins + head.maxs) * 0.5;
		points = damage * (1 - vlen(inflictor.origin - org) / radius);
		if (points <= 0)
			continue;
		// Walls block splash.
		traceline(inflictor.origin, org, MOVE_NOMONSTERS, inflictor);
		if (trace_fraction < 1)
			continue;
		T_Damage(head, inflictor, attacker, points);
	}
};
