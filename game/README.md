# game/

Gameplay rules shared by client and server: movement, combat, weapons, pickups and game modes, starting with RAVAGE DUEL.

`ssqc/` is the server game code in QuakeC, compiled by fteqcc into `qwprogs.dat` (`cmake --build build --target game-data`). It runs a free-for-all Duel match:

| File | What it does |
|---|---|
| `client.qc` | Spawning (the spawn point farthest from other players), respawning, mega health decay |
| `weapons.qc` | Six weapons: shotgun, machine gun, rocket launcher, grenade launcher, lightning gun, railgun. Impulses 1 to 6 select a weapon, 10 and 12 cycle. Hitscan weapons use the server's lag compensation. |
| `items.qc` | Weapon, ammo, health and armor pickups, each returning after a fixed delay (weapons 15 s, ammo 20 s, armor 25 s, health 30 s, mega health 35 s) |
| `combat.qc` | Damage, armor absorption, knockback, splash damage blocked by walls |
| `triggers.qc` | Jump pads (`trigger_push`) and teleporters |
| `rules.qc` | Frags, `fraglimit` and `timelimit`, intermission and map change |
| `selftest.qc`, `matchtest.qc` | Map self-test and two-client match test, used by `tests/` |

Movement is the engine's QuakeWorld player physics, unchanged. Combat and pickup numbers are QuakeWorld-style starting points, written fresh for RAVAGE, and will be tuned in playtesting. Pickups have no models yet: placeholder models, sounds and a HUD come next in step 5 of the [plan](../docs/plan.md).

`ssqc/engine_defs.qc` lists the engine's builtins, fields and constants. It is generated, not hand-written: run `pr_dumpplatform -Tqw -O ravagedefs` in the client console and copy `base/src/ravagedefs.qc` over it after engine updates.
