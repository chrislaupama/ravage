# Bone Circuit

**Current weapon set:** [the approved rocket finish applied across all six weapons](ingame/weapon-set/README.md).
The rocket reference is approved; the full set has been implemented and captured in-game.

Selected direction: Circuit player, prominent weapon identity colours, and a
matching pickup family. The concept sheets are visual targets; the mesh previews
show the textures actually applied to the existing LibreQuake-derived assets.
The player and pickups retain their source detail. Weapon surfaces use clean
1024-pixel material maps authored on the existing UVs. Silhouettes, rigging and
animations are preserved. The offline mesh previews are not in-game captures or exact replicas of generated geometry.
See the [actual in-game screenshots and video](ingame/README.md) for engine captures.

| Family | Approved concept | Actual model and texture preview |
|---|---|---|
| Player | [Circuit, right column](player-concept.png) | [Front, three-quarter and back](player-preview.png) |
| Weapons | [Colour-dominant Bone Circuit](weapons-concept.png) | [First-person meshes](weapons-preview.png), [world pickups](weapon-pickups-preview.png) |
| Pickups | [Health, armour and ammo](pickups-concept.png) | [All pickup meshes](pickups-preview.png) |

The player uses ivory plates, graphite fabric and a painted chest V, with cyan
visor and small status lights. Red/blue player variants in the concept sheet are
future variants; the current game's player material uses the neutral Circuit skin.

| Weapon and ammo | Identity colour |
|---|---|
| Shotgun / shells | Orange |
| Machine gun / bullets | Amber yellow |
| Rocket launcher / rockets | Red |
| Grenade launcher / grenades | Green |
| Lightning / cells | White |
| Railgun / slugs | Cyan |

Health retains green, yellow, orange and purple tiers with ivory medical crosses.
Armour retains green, yellow and red tiers with a dark V and ivory lower trim.
The shard keeps its small gold silhouette. Weapons use ivory service inserts, graphite mechanisms, steel barrels and
rubber grips, following physical part boundaries; coloured paint does not emit light. Obsolete emissive textures are
removed automatically rather than left behind to glow through the new paint.

## Rebuild and review

From the repository root, using ordinary Python (no third-party packages):

```sh
python3 tools/assets/import_librequake.py --skins-only
tests/assets.sh
```

The complete original mesh importer also finishes with this canonical skin pass.
See [source provenance](../../../tools/assets/source/README.md).

To regenerate the offline preview sheets, install Pillow and numpy in your review
environment and run:

```sh
python3 tools/assets/preview_skins.py content docs/art/bone-circuit
```

The preview tool loads the real IQM/MD3 triangles and UVs and poses the player with
its first animation frame. It uses a simple two-sided software rasterizer and
neutral lighting, not RAVAGE's renderer. Asset regeneration and model/skin-reference
checks passed locally. Actual OpenGL rendering has since been captured on this
Mac using a local SDL client build; see [in-game captures](ingame/README.md).
The documented release client builds remain Linux and Windows.

`game-data` copies these committed textures into the playable build. Rebuild game
data if an existing build still shows the old skins. No engine or gameplay changes
are required to use them.
