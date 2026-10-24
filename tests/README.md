# tests/

Automated tests, run with `ctest --test-dir build`.

| Test | What it checks |
|---|---|
| `smoke.sh` | The client (headless renderer) and the dedicated server start with no game data, report the RAVAGE build config, and quit cleanly. |
| `map_pipeline.sh` | Every entity in the TrenchBroom FGD has a spawn function. Every map in `content/maps` compiles to BSP2 with ericw-tools and loads on the dedicated server, where the game code's self-test checks spawn points and pickup placement. Skipped (exit 77) when ericw-tools isn't installed, except on CI. |

| `match.sh` | The two-client match test. Compiles the game data, starts a headless dedicated server on `duel_graybox`, and connects two real headless clients: `target` stands still and `runner` holds forward. The game code's match test (`game/ssqc/matchtest.qc`) then checks that both players used different deathmatch spawn points, the runner moved through the level, nobody ever ended up inside the world or outside the arena, mega health and the rocket launcher are picked up, a railgun hit kills and scores a frag, and the dead player respawns at a spawn point. Finally the target's client prints the stats its HUD shows, which must match the respawn loadout. Linux only. Skipped (exit 77) without ericw-tools, except on CI. |
| `assets.sh` | The committed placeholder models, skin and sounds match what `tools/assets/` generates, and every model or sound the game code names exists. |

Run one test with `ctest --test-dir build -R match --output-on-failure`, or call the script directly: `tests/match.sh build/bin`.
