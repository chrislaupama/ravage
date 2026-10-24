# Working plan

The near-term goal is the first milestone from the vision's Phase 1: two clients connect to a headless dedicated server and move around one original graybox arena. Playable Duel (Phase 2) follows from there.

1. **Repository setup.** Vision document, README, license and notices, and the target folder layout.
2. **Technical discovery (Phase 0).** Build FTEQW and Ironwail from source on Linux. Document FTEQW's architecture, review licensing and dependencies, identify the boundaries between networking and rendering, and list the Ironwail features worth evaluating.
3. **Engine import (Phase 1).** Bring in FTEQW as the engine base with reproducible client and dedicated server builds, CI for Linux and Windows, and campaign dependencies removed from the active product.
4. **First milestone.** A headless server that two clients can join and move around in, inside a graybox arena built only from original placeholder assets.

Rendering benchmarks and visual checks need a machine with a GPU, so they run on a developer's computer rather than in CI.
