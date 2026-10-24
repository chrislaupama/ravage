# game/

Gameplay rules shared by client and server: movement, combat, weapons, pickups and game modes, starting with RAVAGE DUEL.

`ssqc/` is the server game code in QuakeC, compiled by fteqcc into `qwprogs.dat` (`cmake --build build --target game-data`). For now it does the minimum: it spawns players at `info_player_deathmatch` points, registers every entity the map editor can place, and runs a map self-test. Weapons, pickups and scoring come in step 5 of the [plan](../docs/plan.md).

`ssqc/engine_defs.qc` lists the engine's builtins, fields and constants. It is generated, not hand-written: run `pr_dumpplatform -Tqw -O ravagedefs` in the client console and copy `base/src/ravagedefs.qc` over it after engine updates.
