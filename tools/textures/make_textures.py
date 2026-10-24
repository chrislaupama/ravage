#!/usr/bin/env python3
"""Generate RAVAGE's palette and original graybox textures.

Writes two files:

  content/gfx/palette.lmp       the RAVAGE 256-colour palette
  content/textures/ravage.wad   graybox textures as a WAD3

The palette and textures are drawn procedurally here, so they contain no
third-party artwork. Every texture uses the same RAVAGE palette. WAD3 keeps
a copy of it with each texture, which is what TrenchBroom shows. qbsp drops
those copies when it builds a BSP, so the engine draws the map with
gfx/palette.lmp instead, which is why the two must match.

Usage: make_textures.py [content-dir]    (default: the repository's content/)

Only the Python standard library is used. The output is deterministic, so
running the script again without changes gives byte-identical files.
"""

import os
import struct
import sys

# The palette is built from colour ramps, dark to light. The engine treats
# the last 32 entries (224-255) as fullbright: they glow at full brightness
# regardless of lighting.
RAMPS = {
    #           first, count, dark,            light
    'gray':    (0,   112, (12, 13, 16),    (232, 236, 242)),
    'warm':    (112, 32,  (22, 19, 16),    (216, 206, 192)),
    'orange':  (144, 32,  (64, 26, 6),     (255, 150, 60)),
    'cyan':    (176, 16,  (8, 48, 64),     (120, 220, 255)),
    'purple':  (192, 8,   (60, 20, 80),    (190, 90, 240)),
    'green':   (200, 8,   (16, 64, 32),    (90, 220, 130)),
    'yellow':  (208, 8,   (80, 70, 10),    (240, 220, 60)),
    'red':     (216, 8,   (70, 14, 14),    (240, 70, 60)),
    'glow':    (224, 16,  (200, 196, 180), (255, 252, 240)),
    'glow_orange': (240, 8, (220, 100, 20), (255, 170, 80)),
    'glow_cyan':   (248, 8, (40, 180, 230), (160, 240, 255)),
}


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def make_palette():
    pal = [None] * 256
    for first, count, dark, light in RAMPS.values():
        for i in range(count):
            pal[first + i] = lerp(dark, light, i / (count - 1))
    assert None not in pal
    return pal


def noise(x, y, seed):
    """Small deterministic hash noise in [-1, 1]."""
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 32767.5 - 1.0


def to_index(ramp, value):
    """Map a ramp name and a brightness 0..1 to a palette index."""
    first, count, _, _ = RAMPS[ramp]
    value = min(max(value, 0.0), 1.0)
    return first + round(value * (count - 1))


# Pattern functions return (ramp, value) for a texel.

def grid(size, ramp, minor, major, base, minor_v, major_v, seed, grain=0.025):
    def f(x, y):
        if x % major == 0 or y % major == 0 or x == size - 1 or y == size - 1:
            return ramp, major_v
        if x % minor == 0 or y % minor == 0:
            return ramp, minor_v
        return ramp, base + grain * noise(x, y, seed)
    return f


def wall(x, y):
    # Two 64x64 panels per row with bevelled edges and a bolt in each corner.
    px, py = x % 64, y % 64
    if px == 0 or py == 0:
        return 'gray', 0.3
    if px == 1 or py == 1:
        return 'gray', 0.8
    if px == 63 or py == 63:
        return 'gray', 0.45
    if (px in (6, 7) or px in (56, 57)) and (py in (6, 7) or py in (56, 57)):
        return 'gray', 0.38
    return 'gray', 0.66 + 0.02 * noise(x, y, 2)


def trim(x, y):
    # Dark band with a glowing accent stripe through the middle.
    if 29 <= y <= 34:
        return 'glow_orange', 0.7
    if y in (27, 28, 35, 36):
        return 'orange', 0.5
    if y in (0, 63):
        return 'gray', 0.15
    return 'gray', 0.32 + 0.02 * noise(x, y, 3)


def step(x, y):
    # Stair and ledge edge: hazard stripe along the top.
    if y < 8:
        return ('orange', 0.9) if ((x + y) // 8) % 2 == 0 else ('gray', 0.12)
    if y == 8:
        return 'gray', 0.2
    return 'gray', 0.54 + 0.02 * noise(x, y, 4)


def pillar(x, y):
    # Vertical grooves.
    gx = x % 16
    if gx == 0:
        return 'warm', 0.25
    if gx == 1:
        return 'warm', 0.75
    return 'warm', 0.55 + 0.02 * noise(x, y, 5)


def light(x, y):
    # Light fixture: glowing panel with a dark frame.
    if x < 2 or y < 2 or x > 29 or y > 29:
        return 'gray', 0.2
    return 'glow', 0.8 + 0.2 * noise(x, y, 6)


def pad(x, y):
    # Jump pad: concentric glowing rings on a dark plate.
    dx, dy = x - 31.5, y - 31.5
    r = (dx * dx + dy * dy) ** 0.5
    if r < 30 and int(r) % 8 < 4:
        return 'glow_cyan', 0.3 + 0.7 * (1 - r / 30)
    return 'gray', 0.2 + 0.02 * noise(x, y, 7)


def tool(ramp):
    # Tool textures: flat colour with a darker diagonal hatch, so they stand
    # out in the editor. They are never drawn in game.
    def f(x, y):
        return ramp, 0.4 if (x + y) % 16 < 2 else 0.9
    return f


# name, size, pattern
TEXTURES = [
    ('rv_floor', 128, grid(128, 'gray', 16, 64, 0.52, 0.44, 0.32, 1)),
    ('rv_wall', 128, wall),
    ('rv_ceiling', 128, grid(128, 'gray', 32, 64, 0.34, 0.26, 0.18, 8)),
    ('rv_trim', 64, trim),
    ('rv_step', 64, step),
    ('rv_pillar', 64, pillar),
    ('rv_light', 32, light),
    ('rv_pad', 64, pad),
    # Tool textures understood by ericw-tools and TrenchBroom.
    ('clip', 64, tool('purple')),
    ('skip', 64, tool('green')),
    ('hint', 64, tool('yellow')),
    ('trigger', 64, tool('red')),
]


def build_mips(size, pattern):
    """Return the four mip levels as bytes.

    Each smaller level averages 2x2 texels of the level above, keeping the
    ramp that covers most of the block so stripes stay crisp at a distance.
    """
    texels = [[pattern(x, y) for x in range(size)] for y in range(size)]
    mips = []
    for level in range(4):
        n = size >> level
        if level > 0:
            prev = texels
            texels = []
            for y in range(n):
                row = []
                for x in range(n):
                    block = [prev[2 * y + dy][2 * x + dx] for dy in (0, 1) for dx in (0, 1)]
                    ramps = [r for r, _ in block]
                    ramp = max(ramps, key=ramps.count)
                    values = [v for r, v in block if r == ramp]
                    row.append((ramp, sum(values) / len(values)))
                texels.append(row)
        mips.append(bytes(to_index(r, v) for row in texels for r, v in row))
    return mips


def miptex_lump(name, size, pattern, palette):
    mips = build_mips(size, pattern)
    header_size = 16 + 4 * 2 + 4 * 4
    offsets = []
    pos = header_size
    for m in mips:
        offsets.append(pos)
        pos += len(m)
    data = struct.pack('<16sII4I', name.encode('ascii'), size, size, *offsets)
    data += b''.join(mips)
    data += struct.pack('<H', 256)
    data += bytes(c for rgb in palette for c in rgb)
    data += b'\0' * (-len(data) % 4)
    return data


def write_wad(path, palette):
    lumps = []
    for name, size, pattern in TEXTURES:
        assert len(name) <= 15, name
        lumps.append((name, miptex_lump(name, size, pattern, palette)))

    body = b''
    directory = b''
    pos = 12
    for name, data in lumps:
        # filepos, disksize, size, type 0x43 (miptex), compression 0, pad, name
        directory += struct.pack('<IIIbbH16s', pos, len(data), len(data), 0x43, 0, 0,
                                 name.encode('ascii'))
        body += data
        pos += len(data)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'WAD3', len(lumps), pos))
        f.write(body)
        f.write(directory)


def main():
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    content = sys.argv[1] if len(sys.argv) > 1 else os.path.join(repo, 'content')
    palette = make_palette()

    os.makedirs(os.path.join(content, 'gfx'), exist_ok=True)
    pal_path = os.path.join(content, 'gfx', 'palette.lmp')
    with open(pal_path, 'wb') as f:
        f.write(bytes(c for rgb in palette for c in rgb))
    print(f'wrote {pal_path}')

    os.makedirs(os.path.join(content, 'textures'), exist_ok=True)
    wad_path = os.path.join(content, 'textures', 'ravage.wad')
    write_wad(wad_path, palette)
    print(f'wrote {wad_path} ({len(TEXTURES)} textures)')


if __name__ == '__main__':
    main()
