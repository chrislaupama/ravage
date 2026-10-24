# tests/

Automated tests, run with `ctest --test-dir build`.

| Test | What it checks |
|---|---|
| `smoke.sh` | The client (headless renderer) and the dedicated server start with no game data, report the RAVAGE build config, and quit cleanly. |
| `map_pipeline.sh` | Every entity in the TrenchBroom FGD has a spawn function. Every map in `content/maps` compiles to BSP2 with ericw-tools and loads on the dedicated server, where the game code's self-test checks spawn points and pickup placement. Skipped (exit 77) when ericw-tools isn't installed, except on CI. |

Next up is the full server and client test (step 5). See [docs/plan.md](../docs/plan.md).
