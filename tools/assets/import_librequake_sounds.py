#!/usr/bin/env python3
"""Import sounds from LibreQuake.

Copies the LibreQuake sounds RAVAGE uses into content/sound, unchanged.
LibreQuake's sounds are BSD-3 licensed, but its asset list
(docs/.etherpad-backups/LQ_Assets.txt) only names an author for some of
them, so only those are used; make_sounds.py synthesises the rest. Each
entry below gives the author the list names.

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
    'items/weapon.wav': ('weapons/guncock.wav', 'Markie Music'),
    'items/ammo.wav': ('items/r_item1.wav', 'Markie Music'),
    'items/health.wav': ('items/health1.wav', 'Markie Music'),
    'items/mega.wav': ('items/r_item2.wav', 'Markie Music'),
    'items/armor.wav': ('items/armor1.wav', 'Markie Music'),
    'items/respawn.wav': ('items/itembk2.wav', 'Markie Music'),
    'weapons/grenadelauncher.wav': ('weapons/grenade.wav', 'Markie Music'),
    'weapons/bounce.wav': ('weapons/bounce.wav', 'Markie Music, MissLavender and Diplodocus'),
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
