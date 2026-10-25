// Capture-only fixture. Compiled into isolated preview game data, never gameplay.
float skin_scene;
entity(string mdl, vector pos, float yaw) Skin_Model =
{
    local entity e;
    e = spawn();
    e.classname = "skin_capture_model";
    e.movetype = MOVETYPE_NONE;
    e.solid = SOLID_NOT;
    setmodel(e, mdl);
    e.angles = [0, yaw, 0];
    e.frame = 0;
    setorigin(e, pos);
    return e;
};

void() Skin_CaptureFrame =
{
    local float scene;
    local entity e, next, p;
    scene = cvar("rv_skin_scene");
    if (!scene && !skin_scene)
        return;
    if (scene != skin_scene)
    {
        e = nextent(world);
        while (e)
        {
            next = nextent(e);
            if (e.classname == "skin_capture_model" || e.rv_is_item)
                remove(e);
            e = next;
        }
        skin_scene = scene;
        if (scene == 1)
        {
            Skin_Model(MDL_PLAYER, '-60 -140 24', 270);
            Skin_Model(MDL_PLAYER, '0 -140 24', 315);
            Skin_Model(MDL_PLAYER, '60 -140 24', 90);
        }
        else if (scene == 2)
        {
            Skin_Model("models/health_small.iqm", '-90 -140 0', 0);
            Skin_Model("models/health.iqm", '-30 -140 0', 0);
            Skin_Model("models/health_large.iqm", '30 -140 0', 0);
            Skin_Model("models/health_mega.iqm", '90 -140 0', 0);
        }
        else if (scene == 3)
        {
            Skin_Model("models/armor_shard.iqm", '-90 -140 0', 0);
            Skin_Model("models/armor_light.iqm", '-30 -140 0', 270);
            Skin_Model("models/armor_medium.iqm", '30 -140 0', 270);
            Skin_Model("models/armor_heavy.iqm", '90 -140 0', 270);
        }
        else if (scene == 4)
        {
            Skin_Model("models/ammo_shells.iqm", '-150 -140 0', 0);
            Skin_Model("models/ammo_bullets.iqm", '-90 -140 0', 0);
            Skin_Model("models/ammo_rockets.iqm", '-30 -140 0', 0);
            Skin_Model("models/ammo_grenades.iqm", '30 -140 0', 0);
            Skin_Model("models/ammo_cells.iqm", '90 -140 0', 0);
            Skin_Model("models/ammo_slugs.iqm", '150 -140 0', 0);
        }
        else if (scene == 5)
        {
            Skin_Model(W_WorldModel(1), '-150 -140 0', 15);
            Skin_Model(W_WorldModel(2), '-90 -140 0', 15);
            Skin_Model(W_WorldModel(3), '-30 -140 0', 15);
            Skin_Model(W_WorldModel(4), '30 -140 0', 15);
            Skin_Model(W_WorldModel(5), '90 -140 0', 15);
            Skin_Model(W_WorldModel(6), '150 -140 0', 15);
        }
        else if (scene == 6)
        {
            // Inspect the actual first-person MD3 at a neutral display
            // origin; its normal held pose is captured separately.
            Skin_Model(W_ViewModel(cvar("rv_skin_weapon")), '-20 -200 55', 0);
        }
        print("Skin capture scene ", ftos(scene), "\n");
    }
    for (p = find(world, classname, "player"); p; p = find(p, classname, "player"))
    {
        p.items = 63;
        p.ammo_shells = p.ammo_bullets = p.ammo_rockets = 100;
        p.ammo_grenades = p.ammo_cells = p.ammo_slugs = 100;
    }
    if (cvar("rv_skin_turn"))
        for (e = find(world, classname, "skin_capture_model"); e; e = find(e, classname, "skin_capture_model"))
            e.angles_y = e.angles_y + frametime * 18;
};
