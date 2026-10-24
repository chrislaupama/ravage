#!/usr/bin/env python3
"""Import sounds from LibreQuake.

Copies the LibreQuake sounds RAVAGE uses into content/sound, unchanged,
picking each by the Quake sound LibreQuake replaces (Quake's shotgun
fires with guncock.wav, its rocket launcher with sgun1.wav, and so on).
LibreQuake's sounds are BSD-3 licensed. Each entry below gives the author
LibreQuake's asset list (docs/.etherpad-backups/LQ_Assets.txt) names, or
None where it names nobody. make_sounds.py synthesises the sounds
LibreQuake has no equivalent for.

Needs a LibreQuake checkout:

  import_librequake_sounds.py <librequake-dir> [content-dir]

Only the Python standard library is used. LIBREQUAKE_COMMIT in
import_librequake.py is the revision the committed files came from.
"""

import os
import shutil
import sys

SOUNDS = {
    # RAVAGE sound: (LibreQuake sound, author)
    'weapons/shotgun.wav': ('weapons/guncock.wav', 'Markie Music'),
    'weapons/machinegun.wav': ('weapons/rocket1i.wav', None),
    'weapons/rocketlauncher.wav': ('weapons/sgun1.wav', None),
    'weapons/grenadelauncher.wav': ('weapons/grenade.wav', 'Markie Music'),
    'weapons/lightning.wav': ('weapons/lhit.wav', None),
    'weapons/railgun.wav': ('weapons/shotgn2.wav', None),
    'weapons/explode.wav': ('weapons/r_exp3.wav', None),
    'weapons/bounce.wav': ('weapons/bounce.wav', 'Markie Music, MissLavender and Diplodocus'),
    'items/weapon.wav': ('weapons/pkup.wav', None),
    'items/ammo.wav': ('weapons/lock4.wav', None),
    'items/health.wav': ('items/health1.wav', 'Markie Music'),
    'items/mega.wav': ('items/r_item2.wav', 'Markie Music'),
    'items/armor.wav': ('items/armor1.wav', 'Markie Music'),
    'items/respawn.wav': ('items/itembk2.wav', 'Markie Music'),
    'player/pain.wav': ('player/pain1.wav', None),
    'player/death.wav': ('player/death1.wav', None),
    'misc/teleport.wav': ('misc/r_tele1.wav', 'Ember'),
}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    librequake = sys.argv[1]
    content = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'sound')
    for name, (lq, _) in SOUNDS.items():
        path = os.path.join(out, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copyfile(os.path.join(librequake, 'lq1', 'sound', lq), path)
    print('copied', len(SOUNDS), 'sounds to', os.path.normpath(out))


if __name__ == '__main__':
    main()
