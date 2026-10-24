/*
	Jump pads and teleporters.
*/

// Brush triggers keep their collision shape but are never drawn.
void() Trigger_Init =
{
	self.solid = SOLID_TRIGGER;
	self.movetype = MOVETYPE_NONE;
	setmodel(self, self.model);
	self.modelindex = 0;
	self.model = "";
	rv_trigger_count = rv_trigger_count + 1;
};

// Velocity that lands a jump from org at the target, peaking above both.
vector(vector org, vector dest) Push_LaunchVelocity =
{
	local float grav, height, up_time, down_time, dist;
	local vector vel, flat;

	grav = cvar("sv_gravity");
	height = max(dest_z, org_z) - org_z + 64;
	up_time = sqrt(2 * height / grav);
	down_time = sqrt(2 * (height + org_z - dest_z) / grav);
	flat = dest - org;
	flat_z = 0;
	dist = vlen(flat);
	vel = normalize(flat) * (dist / (up_time + down_time));
	vel_z = grav * up_time;
	return vel;
};

void() Push_Touch =
{
	if (other.classname != "player" || other.health <= 0)
		return;
	if (self.enemy)
		other.velocity = Push_LaunchVelocity(other.origin, self.enemy.origin);
	else
		other.velocity = self.movedir * self.speed;
	other.flags = other.flags - (other.flags & FL_ONGROUND);
	// Touch runs every frame while inside the pad; play the sound once.
	sound(other, CHAN_BODY, "misc/jumppad.wav", 1, ATTN_NORM, 0, SOUNDFLAG_NOREPLACE);
};

void() Push_FindTarget =
{
	if (self.target)
	{
		self.enemy = find(world, targetname, self.target);
		if (!self.enemy)
			print("trigger_push at ", vtos(self.absmin), " can't find target ", self.target, "\n");
	}
};

// Turns the editor's angle key into a direction (-1 up, -2 down).
void() SetMovedir =
{
	if (self.angles == '0 -1 0')
		self.movedir = '0 0 1';
	else if (self.angles == '0 -2 0')
		self.movedir = '0 0 -1';
	else
	{
		makevectors(self.angles);
		self.movedir = v_forward;
	}
	self.angles = '0 0 0';
};

void() trigger_push =
{
	Trigger_Init();
	SetMovedir();
	if (!self.speed)
		self.speed = 1000;
	self.touch = Push_Touch;
	// Targets may spawn after this entity, so look them up next frame.
	self.think = Push_FindTarget;
	self.nextthink = time + 0.1;
};

void() Teleport_Touch =
{
	local entity dest;

	if (other.classname != "player" || other.health <= 0)
		return;
	dest = find(world, targetname, self.target);
	if (!dest)
	{
		print("trigger_teleport at ", vtos(self.absmin), " has no destination\n");
		return;
	}
	sound(other, CHAN_AUTO, "misc/teleport.wav", 1, ATTN_NORM);
	makevectors(dest.angles);
	setorigin(other, dest.origin + '0 0 1');
	sound(other, CHAN_AUTO, "misc/teleport.wav", 1, ATTN_NORM);
	other.angles = dest.angles;
	other.fixangle = TRUE;
	other.velocity = v_forward * 300;
	other.teleport_time = time + 0.7;
	other.flags = other.flags - (other.flags & FL_ONGROUND);
};

void() trigger_teleport =
{
	Trigger_Init();
	self.touch = Teleport_Touch;
};
