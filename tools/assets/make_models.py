#!/usr/bin/env python3
"""Generate RAVAGE's placeholder models.

Writes static IQM models and the skin they share into content/models:

  player.iqm                      the player
  g_<weapon>.iqm, v_<weapon>.iqm  weapon pickups and first-person weapons
  <item>.iqm                      health, armor and ammo pickups
  rocket.iqm, grenade.iqm         projectiles
  skin.png, skin_luma.png         the shared skin and its glowing parts

Every model is built here from boxes, cylinders and other simple solids,
so they contain no third-party artwork. They are placeholders: blocky,
unanimated and readable from a distance, until real art replaces them.
Units are Quake units, x points forward and z up.

Usage: make_models.py [content-dir]    (default: the repository's content/)

Only the Python standard library is used. The output is deterministic, so
running the script again without changes gives byte-identical files.
"""

import math
import os
import struct
import sys
import zlib

# The skin is a 4x4 grid of colour cells. Each face of a model shows one
# cell. Cells marked glow are also drawn into skin_luma.png, so they stay
# bright in dark corners.
SKIN_SIZE = 64
CELL = 16
CELLS = [
    # name          colour           glow
    ('dark',        (52, 56, 64),    False),
    ('mid',         (98, 104, 114),  False),
    ('light',       (172, 178, 188), False),
    ('brown',       (118, 90, 62),   False),
    ('orange',      (230, 120, 40),  False),
    ('red',         (196, 40, 36),   False),
    ('white',       (236, 236, 230), False),
    ('green',       (60, 186, 88),   False),
    ('yellow',      (230, 198, 50),  False),
    ('cyan_glow',   (90, 220, 255),  True),
    ('purple_glow', (180, 96, 255),  True),
    ('green_glow',  (120, 255, 140), True),
    ('orange_glow', (255, 160, 60),  True),
    ('blue',        (50, 92, 200),   False),
    ('black',       (18, 18, 22),    False),
    ('red_glow',    (255, 70, 60),   True),
]
CELL_INDEX = {name: i for i, (name, _, _) in enumerate(CELLS)}
MATERIAL = 'models/skin'


#
# Skin
#

def png(path, width, height, rows):
    """Write 8-bit RGB rows as a PNG."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))
    raw = b''.join(b'\0' + bytes(row) for row in rows)
    data = (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(data)


def skin_pixel(x, y, luma):
    i = (y // CELL) * (SKIN_SIZE // CELL) + x // CELL
    _, colour, glow = CELLS[i]
    if luma and not glow:
        return (0, 0, 0)
    if luma:
        # The luma map is added on top of the lit skin, so half strength
        # is enough to keep glowing parts bright without washing out.
        colour = tuple(c // 2 for c in colour)
    cx, cy = x % CELL, y % CELL
    # A darker rim and a soft top-to-bottom gradient give each face a
    # bevelled, panel-like look.
    shade = 1.08 - 0.16 * cy / (CELL - 1)
    if cx in (0, CELL - 1) or cy in (0, CELL - 1):
        shade *= 0.7
    return tuple(min(255, round(c * shade)) for c in colour)


def write_skins(out):
    for name, luma in (('skin.png', False), ('skin_luma.png', True)):
        rows = []
        for y in range(SKIN_SIZE):
            row = []
            for x in range(SKIN_SIZE):
                row.extend(skin_pixel(x, y, luma))
            rows.append(row)
        png(os.path.join(out, name), SKIN_SIZE, SKIN_SIZE, rows)


def cell_uvs(cell):
    """Texture coordinates of a cell's corners, inset to avoid bleeding."""
    i = CELL_INDEX[cell]
    u0 = (i % 4) * CELL + 1.5
    v0 = (i // 4) * CELL + 1.5
    u1, v1 = u0 + CELL - 3, v0 + CELL - 3
    s = SKIN_SIZE
    return (u0 / s, v1 / s), (u1 / s, v1 / s), (u1 / s, v0 / s), (u0 / s, v0 / s)


#
# Geometry
#

def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def normalize(a):
    length = math.sqrt(dot(a, a)) or 1
    return tuple(x / length for x in a)


def centroid(points):
    return tuple(sum(c) / len(points) for c in zip(*points))


class Mesh:
    """Flat-shaded triangles, each face with its own vertices."""

    def __init__(self):
        self.verts = []    # (position, uv, normal)
        self.tris = []

    def face(self, points, cell, inside):
        """Add a convex polygon facing away from the point inside."""
        normal = normalize(cross(sub(points[1], points[0]), sub(points[2], points[0])))
        if dot(normal, sub(centroid(points), inside)) < 0:
            points = points[::-1]
            normal = tuple(-x for x in normal)
        corners = cell_uvs(cell)
        if len(points) == 4:
            uvs = corners
        else:
            # Map other polygons onto the cell around its centre.
            centre = ((corners[0][0] + corners[2][0]) / 2, (corners[0][1] + corners[2][1]) / 2)
            radius = (corners[1][0] - corners[0][0]) / 2
            uvs = [(centre[0] + radius * math.cos(2 * math.pi * k / len(points)),
                    centre[1] + radius * math.sin(2 * math.pi * k / len(points)))
                   for k in range(len(points))]
        first = len(self.verts)
        for p, uv in zip(points, uvs):
            self.verts.append((p, uv, normal))
        for k in range(1, len(points) - 1):
            # IQM front faces wind clockwise as seen from outside.
            self.tris.append((first, first + k + 1, first + k))

    def box(self, lo, hi, cell, sides=None):
        """An axis-aligned box. sides can give some faces another cell,
        keyed by '+x', '-x', '+y', '-y', '+z' or '-z'."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        inside = centroid([lo, hi])
        faces = {
            '-x': [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
            '+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            '+y': [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
            '-z': [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
            '+z': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        }
        for key, points in faces.items():
            self.face(points, (sides or {}).get(key, cell), inside)

    def cylinder(self, axis, centre, radius, start, end, cell, cap=None, segments=8):
        """A cylinder along axis 'x', 'y' or 'z', through centre (the
        other two coordinates), from start to end along the axis."""
        def point(t, a):
            u = centre[0] + radius * math.cos(a)
            v = centre[1] + radius * math.sin(a)
            return {'x': (t, u, v), 'y': (u, t, v), 'z': (u, v, t)}[axis]
        angles = [2 * math.pi * (k + 0.5) / segments for k in range(segments)]
        inside = point((start + end) / 2, 0)
        inside = {'x': (inside[0], centre[0], centre[1]),
                  'y': (centre[0], inside[1], centre[1]),
                  'z': (centre[0], centre[1], inside[2])}[axis]
        for k in range(segments):
            a0, a1 = angles[k], angles[(k + 1) % segments]
            self.face([point(start, a0), point(start, a1), point(end, a1), point(end, a0)], cell, inside)
        for t in (start, end):
            self.face([point(t, a) for a in angles], cap or cell, inside)

    def octahedron(self, centre, rx, ry, rz, cell):
        cx, cy, cz = centre
        top, bottom = (cx, cy, cz + rz), (cx, cy, cz - rz)
        ring = [(cx + rx, cy, cz), (cx, cy + ry, cz), (cx - rx, cy, cz), (cx, cy - ry, cz)]
        for k in range(4):
            a, b = ring[k], ring[(k + 1) % 4]
            self.face([a, b, top], cell, centre)
            self.face([a, b, bottom], cell, centre)

    def moved(self, offset, scale=1.0):
        m = Mesh()
        m.verts = [(tuple(p * scale + o for p, o in zip(pos, offset)), uv, n) for pos, uv, n in self.verts]
        m.tris = list(self.tris)
        return m


#
# IQM
#

IQM_POSITION, IQM_TEXCOORD, IQM_NORMAL = 0, 1, 2
IQM_FLOAT = 7


def write_iqm(path, mesh, name):
    text = b'\0' + name.encode() + b'\0' + MATERIAL.encode() + b'\0'
    text += b'\0' * (-len(text) % 4)
    n = len(mesh.verts)

    header_size = 16 + 27 * 4
    ofs_text = header_size
    ofs_meshes = ofs_text + len(text)
    ofs_varrays = ofs_meshes + 6 * 4
    ofs_pos = ofs_varrays + 3 * 5 * 4
    ofs_uv = ofs_pos + n * 12
    ofs_norm = ofs_uv + n * 8
    ofs_tris = ofs_norm + n * 12
    size = ofs_tris + len(mesh.tris) * 12

    out = bytearray(b'INTERQUAKEMODEL\0')
    out += struct.pack('<27I',
                       2, size, 0,                    # version, filesize, flags
                       len(text), ofs_text,
                       1, ofs_meshes,
                       3, n, ofs_varrays,
                       len(mesh.tris), ofs_tris, 0,   # no adjacency
                       0, 0, 0, 0, 0, 0,              # no joints, poses, anims
                       0, 0, 0, 0,                    # no frames or bounds
                       0, 0, 0, 0)                    # no comment or extensions
    out += text
    out += struct.pack('<6I', 1, 1 + len(name) + 1, 0, n, 0, len(mesh.tris))
    out += struct.pack('<5I', IQM_POSITION, 0, IQM_FLOAT, 3, ofs_pos)
    out += struct.pack('<5I', IQM_TEXCOORD, 0, IQM_FLOAT, 2, ofs_uv)
    out += struct.pack('<5I', IQM_NORMAL, 0, IQM_FLOAT, 3, ofs_norm)
    for pos, _, _ in mesh.verts:
        out += struct.pack('<3f', *pos)
    for _, uv, _ in mesh.verts:
        out += struct.pack('<2f', *uv)
    for _, _, normal in mesh.verts:
        out += struct.pack('<3f', *normal)
    for tri in mesh.tris:
        out += struct.pack('<3I', *tri)
    assert len(out) == size
    with open(path, 'wb') as f:
        f.write(out)


#
# Models
#

def player():
    m = Mesh()
    # Feet on the floor of the player box (z -24), head at its top (z 32).
    for y0, y1 in ((-9, -2), (2, 9)):        # legs and boots
        m.box((-5, y0, -18), (5, y1, 0), 'dark')
        m.box((-6, y0 - 0.5, -24), (7, y1 + 0.5, -18), 'black')
    for y0, y1 in ((-16, -11), (11, 16)):    # arms, hands and shoulder pads
        m.box((-4, y0, 4), (4, y1, 20), 'dark')
        m.box((-3, y0 + 0.5, 0), (3, y1 - 0.5, 4), 'black')
        m.box((-5, y0 - 1, 16), (5, y1 + 1, 23), 'orange')
    m.box((-7, -11, 2), (7, 11, 23), 'mid')
    m.box((7, -8, 6), (9, 8, 19), 'orange')
    m.box((-7.5, -11.5, 0), (7.5, 11.5, 3), 'black')
    m.box((-6, -6, 23), (6, 6, 32), 'mid', {'+z': 'dark'})
    m.box((6, -5, 26), (7, 5, 29.5), 'cyan_glow')
    return m


# Each weapon in its own space: x forward from the grip, y left, z up.
def shotgun(m):
    for y in (-1.4, 1.4):
        m.cylinder('x', (y, 0), 1.2, 6, 30, 'light', 'black', 6)
    m.box((0, -3, -3), (10, 3, 2), 'dark')
    m.box((-10, -2, -5), (0, 2, 1), 'brown')
    m.box((14, -2.6, -3), (22, 2.6, -1), 'brown')


def machinegun(m):
    m.box((0, -3, -3), (16, 3, 3), 'mid')
    m.box((2, -3.2, 0), (14, 3.2, 1), 'yellow')
    m.cylinder('x', (0, 0), 1.5, 16, 32, 'black')
    m.box((6, -1.5, -11), (10, 1.5, -3), 'dark')
    m.box((-8, -2, -4), (0, 2, 1), 'dark')


def rocketlauncher(m):
    m.cylinder('x', (0, 1), 4, -6, 24, 'dark', 'black', 10)
    m.cylinder('x', (0, 1), 4.4, 16, 20, 'orange_glow', None, 10)
    m.cylinder('x', (0, 1), 4.8, 24, 27, 'orange', 'black', 10)
    m.box((2, -1.5, -10), (6, 1.5, -3), 'black')


def grenadelauncher(m):
    m.box((-6, -3, -3), (6, 3, 3), 'mid')
    m.cylinder('x', (0, 0), 5, 0, 9, 'green', 'dark', 10)
    m.cylinder('x', (0, 1), 3, 9, 22, 'dark', 'black')
    m.box((-1, -1.5, -10), (3, 1.5, -3), 'black')


def lightning(m):
    m.box((0, -3, -3), (18, 3, 3), 'blue')
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 2
        m.cylinder('x', (2.4 * math.cos(a), 2.4 * math.sin(a)), 0.7, 18, 30, 'light', None, 4)
    m.cylinder('x', (0, 0), 1.6, 18, 25, 'cyan_glow')
    m.box((4, -1.5, -10), (8, 1.5, -3), 'black')


def railgun(m):
    m.box((-6, -2.5, -3), (26, 2.5, 2), 'dark')
    for y0, y1 in ((-2.9, -1.5), (1.5, 2.9)):
        m.box((0, y0, 2), (30, y1, 3.2), 'green_glow')
    m.cylinder('x', (0, -0.5), 1.2, 26, 36, 'light', 'black', 6)
    m.box((2, -1.5, -10), (6, 1.5, -3), 'black')


WEAPONS = {
    'shotgun': shotgun,
    'machinegun': machinegun,
    'rocketlauncher': rocketlauncher,
    'grenadelauncher': grenadelauncher,
    'lightning': lightning,
    'railgun': railgun,
}

# The pickup floats above the floor, centred so it spins in place. The
# first-person model is half size, low and to the right of the eye.
WORLD_OFFSET = (-12, 0, 16)
VIEW_OFFSET = (16, -6, -7)
VIEW_SCALE = 0.5


def medkit(scale):
    m = Mesh()
    s = scale
    m.box((-8 * s, -8 * s, 0), (8 * s, 8 * s, 12 * s), 'white')
    m.box((-8.5 * s, -2 * s, 2 * s), (8.5 * s, 2 * s, 10 * s), 'red')
    m.box((-2 * s, -8.5 * s, 2 * s), (2 * s, 8.5 * s, 10 * s), 'red')
    m.box((-6 * s, -2 * s, 12 * s), (6 * s, 2 * s, 12.5 * s), 'red')
    m.box((-2 * s, -6 * s, 12 * s), (2 * s, 6 * s, 12.5 * s), 'red')
    return m


def health_small():
    m = Mesh()
    m.cylinder('z', (0, 0), 3, 2, 10, 'red_glow', 'white', 8)
    m.cylinder('z', (0, 0), 1.8, 10, 13, 'white')
    return m


def health_mega():
    m = Mesh()
    m.cylinder('z', (0, 0), 10, 4, 24, 'purple_glow', 'white', 8)
    m.box((-10.5, -3, 8), (10.5, 3, 20), 'white')
    m.box((-3, -10.5, 8), (3, 10.5, 20), 'white')
    m.box((-6, -6, 0), (6, 6, 4), 'dark')
    return m


def armor(cell):
    m = Mesh()
    m.box((-3, -9, 6), (3, 9, 26), cell)
    m.box((-3.5, -10, 22), (3.5, -4, 28), 'mid')
    m.box((-3.5, 4, 22), (3.5, 10, 28), 'mid')
    m.box((3, -5, 10), (4, 5, 20), 'dark')
    m.box((-5, -5, 0), (5, 5, 6), 'dark')
    return m


def armor_shard():
    m = Mesh()
    m.octahedron((0, 0, 12), 4, 4, 8, 'orange_glow')
    return m


def ammo_box(cell):
    m = Mesh()
    m.box((-7, -5, 0), (7, 5, 9), 'dark')
    m.box((-7.5, -5.5, 3), (7.5, 5.5, 6), cell)
    return m


def rocket():
    m = Mesh()
    m.cylinder('x', (0, 0), 2, -8, 8, 'light', 'orange_glow', 6)
    m.cylinder('x', (0, 0), 1.2, 8, 11, 'red')
    for y0, y1, z0, z1 in ((-4, 4, -0.5, 0.5), (-0.5, 0.5, -4, 4)):
        m.box((-8, y0, z0), (-4, y1, z1), 'dark')
    return m


def grenade():
    m = Mesh()
    m.octahedron((0, 0, 0), 3.5, 3.5, 3.5, 'green')
    m.box((-1, -1, -1), (1, 1, 4.5), 'dark')
    return m


def models():
    out = {'player': player()}
    for name, build in WEAPONS.items():
        m = Mesh()
        build(m)
        out['g_' + name] = m.moved(WORLD_OFFSET)
        out['v_' + name] = m.moved(VIEW_OFFSET, VIEW_SCALE)
    out.update({
        'health_small': health_small(),
        'health': medkit(1.0),
        'health_large': medkit(1.3),
        'health_mega': health_mega(),
        'armor_shard': armor_shard(),
        'armor_light': armor('green'),
        'armor_medium': armor('yellow'),
        'armor_heavy': armor('red'),
        'ammo_shells': ammo_box('red'),
        'ammo_bullets': ammo_box('yellow'),
        'ammo_rockets': ammo_box('orange'),
        'ammo_grenades': ammo_box('green'),
        'ammo_cells': ammo_box('cyan_glow'),
        'ammo_slugs': ammo_box('green_glow'),
        'rocket': rocket(),
        'grenade': grenade(),
    })
    return out


def main():
    content = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'models')
    os.makedirs(out, exist_ok=True)
    write_skins(out)
    for name, mesh in models().items():
        write_iqm(os.path.join(out, name + '.iqm'), mesh, name)
    print('wrote', len(models()), 'models and their skin to', os.path.normpath(out))


if __name__ == '__main__':
    main()
