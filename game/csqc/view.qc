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
	view_weapon = spawn();
	view_weapon.renderflags = RF_VIEWMODEL | RF_DEPTHHACK;
};

// Adds the held weapon to the scene. It kicks back for a moment after
// each shot.
void() View_AddWeapon =
{
	local float wep, kick;

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
	kick = 1 - (time - getstatf(STAT_RV_FIRE_TIME)) * 8;
	view_weapon.origin = [-3 * max(kick, 0), 0, 0];
	addentity(view_weapon);
};

// Frame benchmark ("rv_framebench <frames>"): like the engine's
// timerefresh, it turns the view a full circle, but each frame is a whole
// game frame, so the HUD, the first-person weapon and the client game code
// are timed too. tools/bench-map.sh runs it.
float bench_frames;
float bench_frame;
__double bench_start;

void(float frames) View_StartBench =
{
	bench_frames = max(frames, 1);
	bench_frame = 0;
	bench_start = gettimed(1);	// real time, unlike cltime
};

void() View_BenchFrame =
{
	local float seconds;

	setproperty(VF_ANGLES_Y, bench_frame / bench_frames * 360);
	bench_frame = bench_frame + 1;
	if (bench_frame < bench_frames)
		return;
	seconds = gettimed(1) - bench_start;
	print(sprintf("RAVAGE framebench: %d frames in %.2f seconds (%.1f fps)\n", bench_frames, seconds, bench_frames / max(seconds, 0.001)));
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
	View_AddWeapon();
	renderscene();
};
