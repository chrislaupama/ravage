# tools/

Development utilities: asset processing, profiling and build tooling.

| Tool | What it does |
|---|---|
| `build-win64-deps.sh` | Cross-compiles the Windows build's libraries with MinGW-w64 |
| `fetch-ericw-tools.sh` | Downloads the pinned ericw-tools release (qbsp, vis, light) |
| `build-game-data.sh` | Compiles the server game code and every map into `build/game/base` |
| `bench-map.sh` | Rendering benchmark for a map (needs a GPU for meaningful numbers) |
| `textures/make_textures.py` | Generates the RAVAGE palette and graybox texture WAD |
| `trenchbroom/RAVAGE/` | TrenchBroom game config, entity definitions and compile profile |

See [docs/mapping.md](../docs/mapping.md).
