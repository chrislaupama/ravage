# tests/

Automated tests, run with `ctest --test-dir build`.

| Test | What it checks |
|---|---|
| `smoke.sh` | The client (headless renderer) and the dedicated server start with no game data, report the RAVAGE build config, and quit cleanly. |

Next up are the map pipeline test (step 4) and the full server and client test (step 5). See [docs/plan.md](../docs/plan.md).
