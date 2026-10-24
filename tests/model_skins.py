#!/usr/bin/env python3
"""Check every model in <content>/models has the skins it names.

Used by tests/assets.sh. An IQM mesh names its skin as its material, an
MD3 surface as its shader; the engine loads <skin>.png.

  model_skins.py <content-dir>
"""

import glob
import os
import struct
import sys


def c_string(data, offset):
    return data[offset:data.index(b'\0', offset)].decode()


def skins(path):
    data = open(path, 'rb').read()
    if path.endswith('.iqm'):
        _, ofs_text, count, ofs_meshes = struct.unpack_from('<4I', data, 28)
        return [c_string(data, ofs_text + struct.unpack_from('<I', data, ofs_meshes + 24 * m + 4)[0])
                for m in range(count)]
    count, = struct.unpack_from('<I', data, 84)
    surface, = struct.unpack_from('<I', data, 100)
    names = []
    for _ in range(count):
        names.append(c_string(data, surface + struct.unpack_from('<I', data, surface + 92)[0]))
        surface += struct.unpack_from('<I', data, surface + 104)[0]
    return names


def main():
    content = sys.argv[1]
    fail = 0
    for path in sorted(glob.glob(os.path.join(content, 'models', '*.iqm')) +
                       glob.glob(os.path.join(content, 'models', '*.md3'))):
        for skin in skins(path):
            if not os.path.exists(os.path.join(content, skin + '.png')):
                print('FAIL %s names skin %s.png, which is missing' % (os.path.relpath(path, content), skin))
                fail = 1
    sys.exit(fail)


if __name__ == '__main__':
    main()
