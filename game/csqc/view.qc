/*
	The 3D view and the first-person weapon.
*/

entity view_weapon;
float view_weapon_num;	// weapon whose model view_weapon shows

void() View_Init =
{
	local float wep;

	for (wep = WEP_SHOTGUN; wep <= WEP_COUNT; wep = wep + 1)
		precache_model(W_ViewModel(wep));
	precache_model("models/player.iqm");	// for the benchmark
	view_weapon = spawn();
	view_weapon.renderflags = RF_VIEWMODEL | RF_DEPTHHACK;
};

// The first-person weapons' animations, made by tools/assets/make_models.py.
const float VIEW_ANIM_IDLE = 0;
const float VIEW_ANIM_FIRE = 1;

// Adds the held weapon to the scene, playing its fire animation from the
// last shot.
void() View_AddWeapon =
{
	local float wep, since_shot;

	if (getstatf(STAT_RV_HEALTH) <= 0 || intermission)
		return;
	wep = getstatf(STAT_RV_WEAPON);
	if (wep < WEP_SHOTGUN || wep > WEP_COUNT)
		return;
	if (wep != view_weapon_num)
	{
		setmodel(view_weapon, W_ViewModel(wep));
		view_weapon_num = wep;
	}
	since_shot = time - getstatf(STAT_RV_FIRE_TIME);
	if (since_shot >= 0 && since_shot < frameduration(view_weapon.modelindex, VIEW_ANIM_FIRE))
	{
		view_weapon.frame = VIEW_ANIM_FIRE;
		view_weapon.frame1time = since_shot;
	}
	else
	{
		view_weapon.frame = VIEW_ANIM_IDLE;
		view_weapon.frame1time = 0;
	}
	addentity(view_weapon);
};

// Frame benchmark ("rv_framebench <frames> [players]"): like the engine's
// timerefresh, it turns the view a full circle, but each frame is a whole
// game frame, so the HUD, the first-person weapon and the client game code
// are timed too. With players, that many player models run in a ring
// around the view, to time skeletal animation. tools/bench-map.sh runs it.
float bench_frames;
float bench_frame;
float bench_players;
__double bench_start;
entity bench_player;

void(float frames, float players) View_StartBench =
{
	bench_frames = max(frames, 1);
	bench_frame = 0;
	bench_players = players;
	if (players && !bench_player)
	{
		bench_player = spawn();
		setmodel(bench_player, "models/player.iqm");
	}
	bench_start = gettimed(1);	// real time, unlike cltime
};

void() View_AddBenchPlayers =
{
	local float i, a;
	local vector org;

	org = getproperty(VF_ORIGIN);
	for (i = 0; i < bench_players; i = i + 1)
	{
		a = i / bench_players * 2 * M_PI;
		// setorigin, not just .origin, so the renderer knows where it is.
		setorigin(bench_player, org + [cos(a) * 160, sin(a) * 160, -22]);
		bench_player.angles = [0, a * 180 / M_PI + 90, 0];
		bench_player.frame = 1;		// run
		bench_player.frame1time = time + i * 0.1;
		addentity(bench_player);
	}
};

void() View_BenchFrame =
{
	local float seconds;

	setproperty(VF_ANGLES_Y, bench_frame / bench_frames * 360);
	bench_frame = bench_frame + 1;
	if (bench_frame < bench_frames)
		return;
	seconds = gettimed(1) - bench_start;
	print(sprintf("RAVAGE framebench: %d frames, %d players in %.2f seconds (%.1f fps)\n", bench_frames, bench_players, seconds, bench_frames / max(seconds, 0.001)));
	bench_frames = 0;
};

void() View_Draw =
{
	clearscene();
	setproperty(VF_DRAWENGINESBAR, FALSE);
	setproperty(VF_DRAWCROSSHAIR, getstatf(STAT_RV_HEALTH) > 0 && !intermission);
	if (bench_frames)
		View_BenchFrame();
	addentities(MASK_ENGINE);
	if (bench_frames && bench_players)
		View_AddBenchPlayers();
	View_AddWeapon();
	renderscene();
};
