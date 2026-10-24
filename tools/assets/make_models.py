#!/usr/bin/env python3
"""Generate RAVAGE's weapon, pickup and projectile models.

Writes IQM models and the skin they share into content/models. The player
comes from LibreQuake instead; see import_librequake.py.

  g_<weapon>.iqm, v_<weapon>.iqm  weapon pickups and first-person weapons
  <item>.iqm                      health, armor and ammo pickups
  rocket.iqm, grenade.iqm         projectiles
  skin.png, skin_luma.png         the shared skin and its glowing parts

Every model is built here from boxes, prisms, cylinders and other simple
solids, so the geometry and skin contain no third-party artwork. The
first-person weapons are animated: their idle and fire animations, with
recoil and a muzzle flash, follow LibreQuake's weapons, read from
librequake_weapons.json (BSD-3, see content/models/LICENSE.librequake).
The rest are static. Units are Quake units, x points forward and z up.

Usage: make_models.py [content-dir]    (default: the repository's content/)

Only the Python standard library is used. The output is deterministic, so
running the script again without changes gives byte-identical files.
"""

import json
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
    ('slate',       (64, 78, 98),    False),
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
        self.joints = []   # the joint that moves each vertex
        self.tris = []
        self.joint = 0     # joint for the parts added next

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
            self.joints.append(self.joint)
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

    def prism(self, profile, y0, y1, cell, side=None):
        """A convex side profile, as (x, z) points, extruded from y0 to y1.
        side gives the two flat sides another cell."""
        inside = centroid([(x, (y0 + y1) / 2, z) for x, z in profile])
        n = len(profile)
        for k in range(n):
            (xa, za), (xb, zb) = profile[k], profile[(k + 1) % n]
            self.face([(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)], cell, inside)
        for y in (y0, y1):
            self.face([(x, y, z) for x, z in profile], side or cell, inside)

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
        m.joints = list(self.joints)
        m.tris = list(self.tris)
        return m

    def part(self, joint):
        """Only the triangles that follow the given joint."""
        m = Mesh()
        keep = [t for t in self.tris if all(self.joints[i] == joint for i in t)]
        used = sorted({i for t in keep for i in t})
        index = {old: new for new, old in enumerate(used)}
        m.verts = [self.verts[i] for i in used]
        m.joints = [joint] * len(used)
        m.tris = [tuple(index[i] for i in t) for t in keep]
        return m

    def bounds(self, joint=0):
        points = [v[0] for v, j in zip(self.verts, self.joints) if j == joint]
        return tuple(map(min, zip(*points))), tuple(map(max, zip(*points)))


#
# IQM
#

IQM_POSITION, IQM_TEXCOORD, IQM_NORMAL, IQM_BLENDINDEXES, IQM_BLENDWEIGHTS = 0, 1, 2, 4, 5
IQM_UBYTE, IQM_FLOAT = 1, 7
IQM_LOOP = 1


def write_iqm(path, name, verts, tris, material=MATERIAL, blend=None, joints=(), anims=(), frames=()):
    """Write an IQM model.

    verts are (position, uv, normal) and tris index them, wound clockwise.
    A skinned model also has, per vertex, blend: (4 joint indexes, 4 weights
    out of 255); joints: (name, parent index or -1, rest pose); anims: (name,
    first frame, frame count, frames per second, loops); and frames: for
    every frame, a pose per joint. A pose is 10 numbers: translation, a
    rotation quaternion (x, y, z, w) and scale, relative to the parent joint.
    """
    strings = [b'', name.encode(), material.encode()]
    strings += [j[0].encode() for j in joints] + [a[0].encode() for a in anims]
    text, offsets = b'', {}
    for s in strings:
        if s not in offsets:
            offsets[s] = len(text)
            text += s + b'\0'
    text += b'\0' * (-len(text) % 4)

    def string(s):
        return offsets[s.encode()]

    # Each pose channel is stored as 16 bits between its smallest and
    # largest value over all frames.
    channels = []
    for j in range(len(joints)):
        for c in range(10):
            values = [frame[j][c] for frame in frames] or [0.0]
            lo, hi = min(values), max(values)
            channels.append((lo, (hi - lo) / 65535 if hi > lo else 0.0))

    n, nj, nf = len(verts), len(joints), len(frames)
    arrays = [(IQM_POSITION, IQM_FLOAT, 3, 12), (IQM_TEXCOORD, IQM_FLOAT, 2, 8), (IQM_NORMAL, IQM_FLOAT, 3, 12)]
    if blend:
        arrays += [(IQM_BLENDINDEXES, IQM_UBYTE, 4, 4), (IQM_BLENDWEIGHTS, IQM_UBYTE, 4, 4)]
    ofs_text = 16 + 27 * 4
    ofs_meshes = ofs_text + len(text)
    ofs_varrays = ofs_meshes + 6 * 4
    ofs = ofs_varrays + len(arrays) * 5 * 4
    array_offsets = []
    for _, _, _, size in arrays:
        array_offsets.append(ofs)
        ofs += n * size
    ofs_tris = ofs
    ofs_joints = ofs_tris + len(tris) * 12
    ofs_poses = ofs_joints + nj * 48
    ofs_anims = ofs_poses + nj * 88
    ofs_frames = ofs_anims + len(anims) * 20
    size = ofs_frames + nf * nj * 10 * 2
    size += -size % 4

    def table(count, offset):
        return (count, offset if count else 0)

    out = bytearray(b'INTERQUAKEMODEL\0')
    out += struct.pack('<27I',
                       2, size, 0,                    # version, filesize, flags
                       len(text), ofs_text,
                       1, ofs_meshes,
                       len(arrays), n, ofs_varrays,
                       len(tris), ofs_tris, 0,        # no adjacency
                       *table(nj, ofs_joints),
                       *table(nj if nf else 0, ofs_poses),
                       *table(len(anims), ofs_anims),
                       nf, nj * 10 if nf else 0, ofs_frames if nf else 0,
                       0, 0, 0, 0, 0)                 # no bounds, comment or extensions
    out += text
    out += struct.pack('<6I', string(name), string(material), 0, n, 0, len(tris))
    for (kind, fmt, size_, _), offset in zip(arrays, array_offsets):
        out += struct.pack('<5I', kind, 0, fmt, size_, offset)
    for pos, _, _ in verts:
        out += struct.pack('<3f', *pos)
    for _, uv, _ in verts:
        out += struct.pack('<2f', *uv)
    for _, _, normal in verts:
        out += struct.pack('<3f', *normal)
    if blend:
        for indexes, _ in blend:
            out += struct.pack('<4B', *indexes)
        for _, weights in blend:
            out += struct.pack('<4B', *weights)
    for tri in tris:
        out += struct.pack('<3I', *tri)
    for joint_name, parent, rest in joints:
        out += struct.pack('<Ii10f', string(joint_name), parent, *rest)
    if nf:
        for j, (_, parent, _) in enumerate(joints):
            ch = channels[j * 10:j * 10 + 10]
            out += struct.pack('<iI20f', parent, 0x3FF, *[c[0] for c in ch], *[c[1] for c in ch])
    for anim_name, first, count, rate, loops in anims:
        out += struct.pack('<3IfI', string(anim_name), first, count, rate, IQM_LOOP if loops else 0)
    for frame in frames:
        for j in range(nj):
            for c in range(10):
                lo, scale = channels[j * 10 + c]
                out += struct.pack('<H', round((frame[j][c] - lo) / scale) if scale else 0)
    out += b'\0' * (size - len(out))
    assert len(out) == size
    with open(path, 'wb') as f:
        f.write(out)


#
# Models
#

# Each weapon in its own space: x forward from the grip, y left, z up,
# at pickup size. The designs are RAVAGE's own: white ceramic shells over
# dark gunmetal, with glowing energy parts. Each returns its muzzle; parts
# on joint 1 are the muzzle flash, which only shows while firing.

def grip(m, x, cell='dark'):
    m.prism([(x - 2, -3.5), (x + 2, -3.5), (x, -10.5), (x - 4, -10.5)], -1.4, 1.4, cell)


def stock(m, x, cell):
    m.prism([(x, -3.5), (x, 2.5), (x - 10, 0.5), (x - 10, -4.5)], -1.6, 1.6, cell, 'dark')


def flash(m, muzzle, length, width, cell):
    m.joint = 1
    x, y, z = muzzle
    m.octahedron((x + length, y, z), length, width, width, cell)
    m.octahedron((x + length * 0.6, y, z), length * 0.4, width * 1.6, width * 1.6, cell)
    m.joint = 0
    return muzzle


def shotgun(m):
    m.prism([(-6, -3.5), (9, -3.5), (9, 2.5), (-4, 3.5)], -2.6, 2.6, 'dark', 'slate')
    m.prism([(7, -2.5), (30, -1.5), (30, 2), (9, 3.2)], -2.2, 2.2, 'white')
    m.box((10, -2.35, -0.2), (27, 2.35, 0.6), 'cyan_glow')
    for y in (-1.1, 1.1):
        m.cylinder('x', (y, 0.2), 0.9, 28, 33, 'black', None, 6)
    m.box((14, -2.6, -4.4), (23, 2.6, -2.2), 'slate')
    grip(m, 0)
    stock(m, -6, 'white')
    return flash(m, (33, 0, 0.2), 4, 2.5, 'orange_glow')


def machinegun(m):
    m.prism([(-4, -3.5), (16, -3.5), (16, 3), (-2, 3.5)], -3, 3, 'dark', 'slate')
    m.prism([(0, 3), (16, 3), (14, 5), (2, 5)], -2.4, 2.4, 'white')
    m.cylinder('x', (0, 0.5), 2.2, 16, 30, 'mid', 'black', 6)
    for x in (18, 22, 26):
        m.box((x, -2.4, -0.4), (x + 1.5, 2.4, 1.4), 'black')
    m.cylinder('x', (0, 0.5), 1, 30, 35, 'black', None, 6)
    m.box((6, -2.5, -11), (11, 2.5, -3.5), 'slate')
    m.box((6.5, -2.7, -9), (10.5, 2.7, -5), 'orange_glow')
    grip(m, 1)
    stock(m, -4, 'white')
    return flash(m, (35, 0, 0.5), 3, 2, 'orange_glow')


def rocketlauncher(m):
    m.cylinder('x', (0, 1), 4, -8, 30, 'dark', 'black', 10)
    m.prism([(-4, 1), (26, 1), (23, 6.4), (0, 6.4)], -4.4, 4.4, 'white')
    m.box((2, -4.6, 2.6), (22, 4.6, 3.4), 'orange_glow')
    m.cylinder('x', (0, 1), 4.6, 30, 33, 'slate', 'black', 10)
    m.cylinder('x', (0, 1), 4.3, -11, -8, 'slate', 'orange_glow', 10)
    m.box((6, -1, 6.4), (12, 1, 8.4), 'dark')
    m.box((16, -1.2, -8), (19, 1.2, -2.8), 'dark')
    grip(m, 6)
    return flash(m, (33, 0, 1), 5, 4, 'orange_glow')


def grenadelauncher(m):
    m.prism([(-6, -3.5), (8, -3.5), (8, 3.5), (-4, 3.5)], -3.2, 3.2, 'slate', 'dark')
    m.cylinder('x', (0, 0), 5.2, 0, 10, 'dark', 'slate', 6)
    m.cylinder('x', (0, 0), 5.5, 3.5, 6.5, 'green_glow', None, 6)
    m.cylinder('x', (0, 1), 2.8, 10, 25, 'white', 'black', 8)
    m.cylinder('x', (0, 1), 3.3, 23, 27, 'dark', 'black', 8)
    grip(m, -1)
    stock(m, -6, 'white')
    return flash(m, (27, 0, 1), 4, 3, 'green_glow')


def lightning(m):
    m.prism([(-6, -4), (16, -3), (16, 3), (-4, 4)], -3.4, 3.4, 'blue', 'slate')
    m.prism([(-2, 4), (14, 3), (12, 5.5), (0, 5.5)], -2.6, 2.6, 'white')
    for x in (3, 7, 11):
        m.cylinder('x', (0, 0), 3.9, x, x + 1.6, 'cyan_glow', None, 8)
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 2
        m.cylinder('x', (2.4 * math.cos(a), 2.4 * math.sin(a)), 0.7, 16, 30, 'light', None, 4)
    m.cylinder('x', (0, 0), 1.6, 16, 26, 'cyan_glow')
    grip(m, 3)
    return flash(m, (30, 0, 0), 5, 2.5, 'cyan_glow')


def railgun(m):
    m.prism([(-8, -3), (28, -2.5), (28, 2), (-6, 3)], -2.4, 2.4, 'white')
    for y0, y1 in ((-3, -1.6), (1.6, 3)):
        m.box((0, y0, 2), (38, y1, 3.4), 'dark')
    m.box((2, -1.6, 2), (36, 1.6, 2.8), 'green_glow')
    m.cylinder('x', (0, -0.5), 1.2, 28, 40, 'light', 'black', 6)
    m.cylinder('x', (0, 5.4), 1.4, 4, 14, 'dark', 'green_glow', 6)
    m.box((8, -2, -6), (18, 2, -2.5), 'slate')
    m.box((9, -2.2, -5), (17, 2.2, -3.5), 'green_glow')
    grip(m, 2)
    stock(m, -8, 'dark')
    return flash(m, (40, 0, -0.5), 5, 1.6, 'green_glow')


WEAPONS = {
    'shotgun': shotgun,
    'machinegun': machinegun,
    'rocketlauncher': rocketlauncher,
    'grenadelauncher': grenadelauncher,
    'lightning': lightning,
    'railgun': railgun,
}

# The pickup floats above the floor, centred so it spins in place.
WORLD_OFFSET = (-12, 0, 16)

# The first-person model is a little over half size, low and to the right
# of the eye, with the grip at VIEW_OFFSET. Its firing motion comes from
# LibreQuake's matching weapon (see import_librequake.py).
VIEW_OFFSET = (10, -6.5, -8.5)
VIEW_SCALE = 0.55
LIBREQUAKE_WEAPONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'librequake_weapons.json')


def quaternion(r):
    """A rotation matrix as an IQM quaternion (x, y, z, w), w >= 0."""
    w = math.sqrt(max(0.0, 1 + r[0][0] + r[1][1] + r[2][2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + r[0][0] - r[1][1] - r[2][2])) / 2, r[2][1] - r[1][2])
    y = math.copysign(math.sqrt(max(0.0, 1 - r[0][0] + r[1][1] - r[2][2])) / 2, r[0][2] - r[2][0])
    z = math.copysign(math.sqrt(max(0.0, 1 - r[0][0] - r[1][1] + r[2][2])) / 2, r[1][0] - r[0][1])
    return (x, y, z, w)


def rotate(r, v):
    return tuple(dot(row, v) for row in r)


def view_weapon(m, muzzle, reference):
    """The first-person weapon, with an idle and a fire animation. Joint 0
    moves the weapon, joint 1 (at the muzzle) scales the flash.

    LibreQuake's weapons sit centred below the eye and turn about it as
    they kick. RAVAGE's are held elsewhere, so each frame's kick is moved
    to turn about the grip instead: the grip follows the back of the
    LibreQuake weapon, scaled to the two weapons' lengths, and the weapon
    tilts by the same angle."""
    view = m.moved(VIEW_OFFSET, VIEW_SCALE)
    muzzle = tuple(p * VIEW_SCALE + o for p, o in zip(muzzle, VIEW_OFFSET))
    lo, hi = reference['bounds']
    back = (lo[0], (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    view_lo, view_hi = view.bounds()
    size = (view_hi[0] - view_lo[0]) / (hi[0] - lo[0])
    joints = [('weapon', -1, (0, 0, 0, 0, 0, 0, 1, 1, 1, 1)),
              ('flash', 0, muzzle + (0, 0, 0, 1, 1, 1, 1))]
    # LibreQuake's first frame is the weapon at rest, the rest are firing.
    frames = []
    for f in reference['frames']:
        r = f['rotation']
        kick = sub(tuple(a + b for a, b in zip(rotate(r, back), f['move'])), back)
        kick = tuple(k * size for k in kick)
        move = tuple(g + k - x for g, k, x in zip(VIEW_OFFSET, kick, rotate(r, VIEW_OFFSET)))
        frames.append([move + quaternion(r) + (1, 1, 1),
                       muzzle + (0, 0, 0, 1) + (f['flash'],) * 3])
    rate = LIBREQUAKE['framerate']
    anims = [('idle', 0, 1, rate, True), ('fire', 1, len(frames) - 1, rate, False)]
    return view, joints, anims, frames


LIBREQUAKE = None


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
    """Every model, as name: (mesh, skeleton); skeleton is None or
    (joints, anims, frames)."""
    global LIBREQUAKE
    with open(LIBREQUAKE_WEAPONS) as f:
        LIBREQUAKE = json.load(f)
    out = {}
    for name, build in WEAPONS.items():
        m = Mesh()
        muzzle = build(m)
        out['g_' + name] = (m.part(0).moved(WORLD_OFFSET), None)
        view, joints, anims, frames = view_weapon(m, muzzle, LIBREQUAKE['weapons'][name])
        out['v_' + name] = (view, (joints, anims, frames))
    static = {
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
    }
    out.update((name, (mesh, None)) for name, mesh in static.items())
    return out


def main():
    content = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'models')
    os.makedirs(out, exist_ok=True)
    write_skins(out)
    built = models()
    for name, (mesh, skeleton) in built.items():
        path = os.path.join(out, name + '.iqm')
        if skeleton:
            # Each vertex follows one joint.
            joints, anims, frames = skeleton
            blend = [((j, 0, 0, 0), (255, 0, 0, 0)) for j in mesh.joints]
            write_iqm(path, name, mesh.verts, mesh.tris, blend=blend, joints=joints, anims=anims, frames=frames)
        else:
            write_iqm(path, name, mesh.verts, mesh.tris)
    print('wrote', len(built), 'models and their skin to', os.path.normpath(out))


if __name__ == '__main__':
    main()
