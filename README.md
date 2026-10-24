# RAVAGE

*Fast. Brutal. Relentless.*

RAVAGE is a standalone, multiplayer-only competitive arena FPS in the tradition of Quake and QuakeWorld. It runs on RAVAGE ENGINE, built from FTEQW with selected rendering improvements from Ironwail.

**Status:** pre-production. The engine builds for Linux and Windows, and the first graybox Duel arena plays as a Duel with weapons, pickups, scoring, placeholder models and sounds, and a HUD. All of it is original and runs without Quake installed. The first target is a minimal RAVAGE DUEL (1v1). See [Building RAVAGE](docs/building.md) and [Making maps](docs/mapping.md).

## Documents

- [Project vision](docs/vision.md)
- [Working plan](docs/plan.md)
- [Licensing and asset rules](docs/licensing.md)
- [Building RAVAGE](docs/building.md)
- [Making maps](docs/mapping.md)

## Repository layout

| Folder | Purpose |
|---|---|
| [engine/](engine/) | Core technology, rendering, audio, platform |
| [client/](client/) | Input, HUD, menus, prediction |
| [server/](server/) | Headless authoritative dedicated server |
| [game/](game/) | Movement, combat, weapons, pickups, game modes |
| [network/](network/) | Transport, replication, protocol |
| [content/](content/) | Original maps, models, materials, audio |
| [services/](services/) | Accounts, matchmaking, RAVAGE LEAGUE |
| [tools/](tools/) | Asset processing, profiling, build tools |
| [tests/](tests/) | Automated tests and simulation validation |
| [docs/](docs/) | Specifications, architecture, decisions |

This is the target layout. Imported upstream code may keep its own structure at first and be reorganized gradually.

## License

The engine is licensed under the GNU GPL, version 2 or later; see [LICENSE](LICENSE). RAVAGE does not include or redistribute any Quake game assets. See [docs/licensing.md](docs/licensing.md) for details.
