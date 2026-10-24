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
| `assets/iqm.py` | The IQM and PNG writers it uses |
| `assets/make_sounds.py` | Generates the placeholder out-of-ammo and jump pad sounds |
| `assets/import_librequake_sounds.py` | Copies the LibreQuake sounds RAVAGE uses (needs a LibreQuake checkout) |
| `assets/import_announcer.py` | Cuts the announcer's ElevenLabs takes (MP3) into the countdown sounds (needs ffmpeg) |
| `trenchbroom/RAVAGE/` | TrenchBroom game config, entity definitions and compile profile |

See [docs/mapping.md](../docs/mapping.md).
