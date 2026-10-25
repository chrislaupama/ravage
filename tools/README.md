# tools/

Development utilities: asset processing, profiling and build tooling.

| Tool | What it does |
|---|---|
| `build-win64-deps.sh` | Cross-compiles the Windows build's libraries with MinGW-w64 |
| `fetch-ericw-tools.sh` | Downloads the pinned ericw-tools release (qbsp, vis, light) |
| `build-game-data.sh` | Compiles the server and client game code and every map, and copies models and sounds, into `build/game/base` |
| `bench-map.sh` | Rendering and whole-frame benchmark for a map, also run in CI |
| `textures/make_textures.py` | Generates the RAVAGE palette and graybox texture WAD |
| `assets/import_librequake.py` | Imports LibreQuake's player, weapons, pickups and projectiles, with their animations, and recolours their skins (needs `pip install bpy` and a LibreQuake checkout) |
| `assets/import_librequake.py --skins-only` | Rebuilds Bone Circuit textures from committed sources using only standard Python; preserves meshes and animations |
| `assets/paint_weapon_materials.py` | Authors clean 1024-pixel weapon material maps on the real UVs (artist tool: Pillow/numpy); normal skin builds use the committed maps |
| `capture-skins.py` | Captures actual in-game skin lineups or `--weapons-only` idle/firing checks using isolated game data |
| `assets/preview_skins.py` | Renders the actual IQM/MD3 meshes and textures for offline UV/material review (Pillow and numpy; not a game capture) |
| `assets/iqm.py` | The IQM and PNG writers it uses |
| `assets/make_sounds.py` | Generates the placeholder out-of-ammo and jump pad sounds |
| `assets/import_librequake_sounds.py` | Copies the LibreQuake sounds RAVAGE uses (needs a LibreQuake checkout) |
| `trenchbroom/RAVAGE/` | TrenchBroom game config, entity definitions and compile profile |

See [docs/mapping.md](../docs/mapping.md).
