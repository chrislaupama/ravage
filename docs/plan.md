# Working plan

The near-term goal is a standalone first milestone: a TrenchBroom-built graybox arena that compiles automatically, loads on a headless dedicated server, and lets two clients join and move around, all without Quake installed. Playable Duel (Phase 2 in the [vision](vision.md)) follows from there.

1. **Repository setup.** Done. Vision document, README, license and notices, and the target folder layout.
2. **Technical discovery (Phase 0).** Done. See [discovery.md](discovery.md).
3. **Engine import (Phase 1).** Done. Bring in FTEQW as the engine base with reproducible client and dedicated server builds for Linux and Windows, and CI. The RAVAGE build config keeps native Quake BSP loading (BSP29, BSP2 and 2PSB) and can read a locally owned Quake install as an optional development reference. It never ships one.
4. **Map pipeline.** Done. TrenchBroom becomes the official editor, with a RAVAGE `GameConfig.cfg` and FGD entity definitions. Maps in standard Quake or Valve 220 `.map` format are compiled automatically with ericw-tools (`qbsp`, `vis`, `light`). This step also adds one original graybox Duel arena and an integration test that compiles it as BSP2 and loads it. See [mapping.md](mapping.md).
5. **Standalone game and first milestone.** Done. RAVAGE game code (QuakeC) with spawn points, weapon pickups, health, armor and other multiplayer entities. GPL-licensed QuakeWorld movement, combat and weapon logic is kept or adapted where it fits. Original or appropriately licensed placeholder player and weapon models, sounds and textures are added so the game runs standalone. The step ends with an automated test that compiles the arena, loads it on a headless dedicated server, and checks spawn points, pickups, collision and two connected clients.

6. **Player and weapon models.** In review. The player is LibreQuake's model and animations (BSD-3) with a RAVAGE skin. The six weapons are RAVAGE's own futuristic designs, animated with LibreQuake's firing motion.

Rendering benchmarks run in CI with software rendering (see [mapping.md](mapping.md#benchmark)) to catch regressions.

## Engine requirements

Set on 2026-10-24. Each is mapped to the step that delivers it.

| # | Requirement | Step |
|---|---|---|
| 1 | Preserve native Quake-compatible BSP level loading in the engine. | 3 |
| 2 | TrenchBroom is the official map editor, with a RAVAGE `GameConfig.cfg` and FGD entity definitions. | 4 |
| 3 | Support standard Quake and Valve 220 `.map` sources, compile them automatically with ericw-tools (`qbsp`, `vis`, `light`), and verify BSP2 support with integration tests. | 4 |
| 4 | RAVAGE-specific spawn points, weapon pickups, health, armor and other multiplayer entities. | 5 |
| 5 | Keep or adapt GPL-licensed Quake movement, combat and weapon mechanics where appropriate, in line with their licenses. | 5 |
| 6 | Legally obtained original Quake assets may be used only as optional, local development references or placeholders. Copyrighted Quake models, textures, sounds or maps are never committed, bundled or redistributed without the rights to do so. | 3 (engine support), ongoing |
| 7 | Original or appropriately licensed redistributable placeholder player models, weapon models, sounds and textures, so RAVAGE runs standalone without Quake installed. | 5 |
| 8 | An automated test that compiles a TrenchBroom arena, loads it on a headless dedicated server, and verifies spawn points, pickups, collision and connected multiplayer clients. | 4 (compile and load), 5 (full test) |
