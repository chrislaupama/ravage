# game/

Gameplay rules shared by client and server: movement, combat, weapons, pickups and game modes, starting with RAVAGE DUEL.

`ssqc/` is the server game code in QuakeC, compiled by fteqcc into `qwprogs.dat` (`cmake --build build --target game-data`). It runs a free-for-all Duel match:

| File | What it does |
|---|---|
| `client.qc` | Spawning (the spawn point farthest from other players), respawning, mega health decay |
| `weapons.qc` | Six weapons: shotgun, machine gun, rocket launcher, grenade launcher, lightning gun, railgun. Impulses 1 to 6 select a weapon, 10 and 12 cycle. Hitscan weapons use the server's lag compensation. |
| `items.qc` | Weapon, ammo, health and armor pickups, each returning after a fixed delay (weapons 15 s, ammo 20 s, armor 25 s, health 30 s, mega health 35 s) |
| `combat.qc` | Damage, armor absorption, knockback, splash damage blocked by walls |
| `anims.qc` | Player animations: stand, run, shoot, pain and five deaths |
| `triggers.qc` | Jump pads (`trigger_push`) and teleporters |
| `rules.qc` | The Duel match: warmup, ready-up, countdown, `fraglimit` and `timelimit`, overtime, forfeits, intermission and map change. Spectators. |
| `matchstats.qc` | Match recording (an MVD demo per match) and post-match statistics: shots and hits by weapon, damage dealt and taken, frags, deaths and pickups |
| `selftest.qc`, `matchtest.qc` | Map self-test and two-client match test, used by `tests/` |

A Duel server has two player slots (the game sets `maxclients 2`). Anyone else who connects joins as a spectator, through the RAVAGE engine's `sv_fullspectate`. A match goes:

1. **Warmup.** Players play freely. Each presses F3 (or types `ready` in the console) when ready, and `notready` takes it back.
2. **Countdown.** Once both are ready, five seconds in which nobody can fire. The announcer calls "get ready", three, two, one and "fight!" (the client HUD plays these, in `hud.qc`). It stops if a player leaves or un-readies.
3. **Play.** Frags, pickups and projectiles reset and both players respawn. The `timelimit` clock (minutes) starts now, and `fraglimit` ends the match early.
4. **Overtime.** If time runs out with the scores tied, the next frag wins.
5. **Intermission.** The scoreboard says who won, with both players' match statistics. If a player leaves mid-match, the other wins by forfeit.

### Recordings and statistics

The server records every match, from the start of play to a few seconds into the scoreboard, as `demos/<map>_<player>-<player>_<date>-<time>.mvd` in the game folder (`base/`). Watch one with `playdemo demos/<name>.mvd` in the client console; the view follows a player and shows their HUD. The demo carries a copy of the client game code (`sv_demo_write_csqc`), so it still plays after the game changes. `set rv_record 0` turns recording off.

Statistics are counted on the server from game events, only while the match is on (warmup doesn't count):

- **Accuracy by weapon.** A shot is one trigger pull: a shotgun blast or a rocket is one shot, and hits if any of it damages the opponent. Each lightning gun tick is a shot.
- **Damage dealt and taken,** counting health and armor actually lost. Self damage counts as taken, not dealt.
- **Frags and deaths,** with a suicide taking a frag away.
- **Pickups:** health and armor picked up, and mega healths.

At the end of the match they go to every client for the scoreboard, and to `data/matches/<name>.json`, named like the demo. That file is meant for tools and, later, RAVAGE LEAGUE.

`set rv_warmup 0` skips warmup and the countdown: the match runs from the map start.

Movement is the engine's QuakeWorld player physics, unchanged. Combat and pickup numbers are QuakeWorld-style starting points, written fresh for RAVAGE, and will be tuned in playtesting. `assets.qc` lists the models and sounds, made by `tools/assets/`. The player model has one animation per action, and `.frame` picks it. Clients play it from when `.frame` changes, so the server only switches between them. The self-test checks the animation names match `anims.qc`.

`csqc/` is the client game code, compiled into `csprogs.dat`. The server sends it to each client, where it draws the 3D view, the first-person weapon (playing its fire animation after each shot) and the HUD (health, armor, ammo, the weapon bar, both players' frags and the match clock or warmup status, plus the scoreboard and match statistics at the end of a match, in `matchstats.qc`). It also turns F3 into `ready`. The engine's own Quake status bar and view weapon are compiled out, so the HUD reads everything from stats the server registers in `world.qc` (`Stats_Register`). `PlayerStat` in `defs.qc` reads them, from the player the view follows when playing back a demo.

`shared/` holds definitions both sides use: weapon numbers, names and models, and the stat numbers.

`ssqc/engine_defs.qc` lists the engine's builtins, fields and constants. It is generated, not hand-written: run `pr_dumpplatform -Tqw -O ravagedefs` in the client console and copy `base/src/ravagedefs.qc` over it after engine updates. `csqc/engine_defs.qc` is the client's equivalent, from `pr_dumpplatform -Tcs -O ravagecsdefs`.
