# Technical discovery: FTEQW and Ironwail

Step 2 of the [working plan](plan.md) (Phase 0 in the [vision](vision.md#phase-0-technical-discovery)). Written 2026-10-24.

## Summary

- Both engines build cleanly from source on Linux (Ubuntu 24.04, GCC 13, CMake 3.28) with packaged dependencies. FTEQW's client, dedicated server and QuakeC compiler take about 2 minutes on 4 cores; Ironwail takes about 25 seconds.
- FTEQW is a good foundation. It already has most of what the vision asks for: a headless dedicated server, QuakeWorld movement shared between client prediction and server, lag compensation, server-side demo recording, a spectator proxy (QTV), client-side QuakeC for HUD and menus, and OpenGL, Vulkan and headless renderers.
- FTEQW ships a build config meant for standalone games (`config_nocompat.h`). RAVAGE should start from a copy of it rather than from the full Quake-compatible config.
- Ironwail is a different codebase (QuakeSpasm lineage, OpenGL 4.3 only). Its code can't be transplanted into FTEQW's renderer; its techniques have to be re-implemented. For small Duel arenas the gain is uncertain, so this should wait for benchmarks.
- Two decisions need input: how strictly to follow the vision's "fixed 60 Hz" simulation (QuakeWorld doesn't work that way), and which tool to use for building maps.

## Versions examined

| Project | Commit | Date |
|---|---|---|
| [FTEQW](https://github.com/fte-team/fteqw) | `f937b9d88f71` | 2026-06-04 |
| [Ironwail](https://github.com/andrei-drexler/ironwail) | `08d578136ff4` | 2026-09-10 |

## Build results (Linux)

Packages used on top of a base Ubuntu 24.04 image:

```
libsdl2-dev libgl-dev libvulkan-dev libxrandr-dev libxcursor-dev libjpeg-dev
libvorbis-dev libgnutls28-dev libopus-dev libwayland-dev libxkbcommon-dev
libbz2-dev ninja-build
```

FTEQW:

```
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja -C build fteqw fteqw-sv fteqcc
```

Produces `fteqw` (client, 9.5 MB), `fteqw-sv` (dedicated server, 4.3 MB) and `fteqcc` (QuakeC compiler, 0.9 MB). There are 62 compiler warnings, mostly string-truncation warnings. The Bullet and ODE physics plugins were skipped because those libraries weren't installed; RAVAGE doesn't need them.

The dedicated server starts with no game data and exits cleanly with "Couldn't load a map", which is expected. It needs an original map and game code before it can run, which is step 4.

Ironwail:

```
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja -C build
```

Not checked yet: Windows builds (FTEQW supports MinGW cross-compiling and MSVC; to be confirmed in step 3 CI), and running either client, since this machine has no GPU or display.

## FTEQW architecture

About 640,000 lines of C in `engine/`:

| Folder | Lines | What it holds |
|---|---|---|
| `client/` | 212k | Input, prediction (`cl_pred.c`), entity interpolation, CSQC and menu QC, sound, menus, particles |
| `common/` | 119k | Filesystem, cvars, console, maths, network channel, **player movement (`pmove.c`)**, collision |
| `server/` | 97k | Server loop, physics, client commands, entity sending, demo recording (`sv_mvd.c`), Q2/HL/Q3 game support |
| `gl/` | 94k | OpenGL renderer and shared backend |
| `qclib/` | 72k | QuakeC virtual machine and the FTEQCC compiler |
| `d3d/`, `vk/`, `sw/` | 35k | Direct3D, Vulkan and software renderers |
| `http/`, `web/` | 9k | HTTP downloads and the browser build |

`fteqtv/` (separate folder) is the QTV proxy for relaying matches to spectators with a delay.

### How it maps onto the vision's systems

| Vision system | Where it is in FTEQW | Notes |
|---|---|---|
| Movement (4.1) | `common/pmove.c`, `pmovetst.c` | QuakeWorld movement, shared by client prediction and server. Bunny hopping, strafe jumping and rocket jumping work as in QW. `pm_*` server cvars tune it. |
| Prediction (8.6) | `client/cl_pred.c` | Predicts the local player and corrects from server snapshots. |
| Lag compensation (8.7) | `sv_antilag` in `server/sv_user.c` | Backdates hitscan traces. Modes 0 to 3, controlled by game code by default. |
| Dedicated server (8.8) | `fteqw-sv` target, `SERVERONLY` | Builds without any renderer. |
| Gameplay rules | Server QuakeC (SSQC) | Weapons, items, scoring and modes live in QuakeC, not C. |
| HUD and menus (11) | Client QuakeC (CSQC, `pr_csqc.c`) and menu QC | Lets RAVAGE build its own interface without engine changes. |
| Match recording and replays (11.5) | `server/sv_mvd.c` (MVD demos) | Server-side recording of every player's view. |
| Spectating (7.2) | Built-in spectators and `fteqtv/` | QTV supports broadcast delay. |
| Renderers (8.3) | `gl/`, `vk/`, headless | Vulkan is the likely route to macOS through MoltenVK. |

### What RAVAGE won't need

FTEQW supports a lot that a multiplayer-only standalone game doesn't use: Quake 2, Quake 3 and Half-Life game support, NetQuake protocol compatibility, `.pak` loading, Direct3D, the software renderer, Android and the browser build. Most of this can be switched off in the build config rather than deleted, which keeps it easy to pull in upstream fixes. `engine/common/config_nocompat.h` is FTEQW's own template for "total conversions that have chosen to break compatibility". It already sets the game name, protocol name, default port and allowed renderers.

**Recommendation:** in step 3, add `config_ravage.h` based on `config_nocompat.h`, keep upstream folders as they are, and remove code only when it gets in the way.

### Simulation timing

The vision asks for a fixed-timestep simulation at 60 Hz (8.5). QuakeWorld doesn't work that way. The server runs each player's movement as soon as their input packet arrives, at whatever rate the client sends, capped at about 77 per second. Everything else (projectiles, items) runs at `sv_mintic`, which defaults to 0.013 s (about 77 Hz). This is a big part of why QW movement feels responsive, and the original competitive community is built on it.

FTEQW can run fixed-interval ticks (`sv_maxtic 0`), but player movement would still be packet-driven unless that's changed in the engine. This needs a decision before Phase 2 tuning. Options are keeping QW-style timing (lowest risk, proven feel), or moving to a true fixed tick (more consistent, but a significant engine change).

## Ironwail

About 118,000 lines, derived from QuakeSpasm (the NetQuake branch, not QuakeWorld). It needs OpenGL 4.3 and doesn't run on macOS.

Its performance features, with a first estimate of how much they would help RAVAGE:

| Feature | Files | Value for RAVAGE | Notes |
|---|---|---|---|
| GPU world culling with compute shaders and indirect multi-draw | `r_world.c`, `gl_rmain.c` | Medium | Main gain is on very large, high-polygon maps. Duel arenas are small. |
| Persistent mapped buffers for streaming geometry | `gl_rmisc.c` | Medium | Cuts CPU driver overhead and helps frame-time stability. |
| Instanced model rendering | `r_alias.c` | Low | Duel has two players and a few items. |
| GPU lightmap updates | `r_brush.c` | Low | Only matters with lots of animated lighting. |
| Bindless textures | `gl_texmgr.c` | Low | Driver compatibility risk. |
| Renderer decoupled from server tick | | None | FTEQW already does this. |

FTEQW and Ironwail don't share renderer code. FTEQW renders through its own batch and shader backend (`gl/gl_backend.c`, `vk/`), so any Ironwail technique would be re-written for that backend and done separately for Vulkan. That matches section 8.3 of the vision: no wholesale transplant.

**Recommendation:** don't schedule Ironwail work yet. Build the graybox arena first, measure FTEQW's frame times against the 144 FPS at 1080p target on real hardware, and only port a technique if the profile shows the bottleneck it fixes. Benchmarks need a machine with a GPU, so they can't run on this cloud machine.

## Licensing and dependencies

- FTEQW and Ironwail engine sources are GPL version 2 "or (at your option) any later version", consistent with [licensing.md](licensing.md).
- A few FTEQW files use permissive licenses (for example the hashing code in `common/sha1.c`, `md5.c`, `sha2.c`). These are GPL-compatible and their notices must be kept.
- Libraries linked at build time: SDL2, zlib, libpng, libjpeg, FreeType, Vorbis, Opus and GnuTLS. All are GPLv2-compatible. GnuTLS is LGPL; for Windows builds it's worth deciding whether to use it or the system TLS (`net_ssl_winsspi.c`).
- id Software's QuakeWorld QuakeC game code is GPL and can be a starting reference for RAVAGE's Duel logic. Quake's maps, models, sounds and textures cannot be used.

## Gaps found

- **Map tooling.** RAVAGE needs a BSP map compiler to build its graybox arena. The usual open-source choice is [ericw-tools](https://github.com/ericwa/ericw-tools) (GPL), with TrenchBroom as the editor. FTEQW can also load Quake 3 BSP maps if a Q3-style workflow is preferred. This is needed in step 4.
- **Placeholder assets.** Player model, weapon model, sounds, fonts and HUD art all need original placeholders. FTEQW can run with very little, but a font and a player model are the minimum to test movement visually.
- **Automated tests.** Neither project has an automated test suite for movement or networking. RAVAGE will need its own, starting with a headless server and scripted client test for step 4.

## Next steps

Step 3: bring FTEQW into this repository at the commit above (keeping its history and notices), add `config_ravage.h`, build `ravage` and `ravage-sv` targets, and set up CI for Linux and Windows.
