# engine/

RAVAGE ENGINE: core technology, rendering, audio, networking and platform code.

- `fteqw/` is [FTEQW](https://github.com/fte-team/fteqw), imported with `git subtree` at upstream commit `f937b9d88f71` (2026-06-04). It keeps its own layout and license notices.
- `config_ravage.h` is the RAVAGE build config: branding, the feature set and the allowed renderers. It started as a copy of FTEQW's `engine/common/config_nocompat.h`, and every change from it is marked `RAVAGE:`.

`config_ravage.h` turns on `MD3MODELS` (off in `config_nocompat.h`) for the first-person weapons, which animate by morphing vertices.

Ironwail rendering improvements will be brought in one at a time, and only when benchmarks show a gain. See [docs/discovery.md](../docs/discovery.md).

## Changes to upstream code

Keep this list current, so local changes can be carried forward or sent upstream.

| File | Change | Why |
|---|---|---|
| `fteqw/engine/client/pr_csqc.c` | Guard `PR_Route_Shutdown` with `ENGINE_ROUTING` | Linking failed when `ENGINE_ROUTING` is off |
| `fteqw/engine/client/cl_main.c` | Guard `r_imagelist_wad` with `PACKAGE_TEXWAD` | Linking failed when `PACKAGE_TEXWAD` is off |
| `fteqw/engine/common/cvar.c` | Make the empty, `"0"` and `"1"` cvar default strings arrays | `Cvar_DefaultFree` compared string-literal addresses, which differ under MinGW with LTO, so the Windows server freed static memory and crashed with heap corruption on quit |
| `fteqw/engine/server/sv_send.c` | Raise the highest stat sent when `clientstat`/`globalstat` registers one above 31 | Without `QUAKESTATS`, stats 32 and up were never sent, so the CSQC HUD read zeros |
| `fteqw/CMakeLists.txt` | Add `FTE_MARCH_NATIVE` option around `-march=native` | Release builds crashed with an illegal instruction on CPUs older than the build machine's |

## Updating FTEQW

```
git subtree pull --prefix=engine/fteqw --squash https://github.com/fte-team/fteqw.git <commit>
```

Then rebuild, run the tests, and check the table above still applies.
