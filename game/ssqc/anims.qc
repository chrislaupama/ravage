/*
	Player animations. The player model (from LibreQuake, imported by
	tools/assets/import_librequake.py) has one animation per action, and
	.frame picks it. Clients play the animation from the moment .frame
	changes, so the server only switches between them.

	Keep these in step with ANIMS in import_librequake.py.
*/

const float ANIM_STAND = 0;
const float ANIM_RUN = 1;
const float ANIM_SHOOT = 2;
const float ANIM_PAIN = 3;
const float ANIM_DEATH = 4;		// the first of five death animations
const float ANIM_DEATH_COUNT = 5;
const float ANIM_SHOOT_RAPID = 9;

const float ANIM_SHOOT_TIME = 0.6;	// both are 6 frames at 10 per second
const float ANIM_PAIN_TIME = 0.6;

.float rv_pain_time;		// time the player was last hurt

// Picks a living player's animation, every frame after movement.
void() Player_Animate =
{
	local float since_shot;

	since_shot = time - self.rv_fire_time;
	if (self.weapon == WEP_MACHINEGUN || self.weapon == WEP_LIGHTNING)
	{
		// Rapid-fire weapons loop a short recoil while the trigger is held.
		if (since_shot < 0.2)
		{
			self.frame = ANIM_SHOOT_RAPID;
			return;
		}
	}
	else if (since_shot < ANIM_SHOOT_TIME)
	{
		self.frame = ANIM_SHOOT;
		return;
	}
	if (time - self.rv_pain_time < ANIM_PAIN_TIME)
		self.frame = ANIM_PAIN;
	else if (self.velocity_x * self.velocity_x + self.velocity_y * self.velocity_y > 50 * 50)
		self.frame = ANIM_RUN;
	else
		self.frame = ANIM_STAND;
};

// One of the death animations, at random. They end lying down and hold
// the last frame.
void(entity targ) Player_AnimateDeath =
{
	targ.frame = ANIM_DEATH + floor(random() * ANIM_DEATH_COUNT);
};
