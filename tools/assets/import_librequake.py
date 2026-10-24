#!/usr/bin/env python3
"""Import the player model and the weapon animations from LibreQuake.

Reads LibreQuake's Blender sources (lq1/progs/src/*.mdl.blend) and writes:

  content/models/player.iqm             the player's mesh, skeleton and animations
  content/models/player_skin.png        LibreQuake's skin, recoloured for RAVAGE
  content/models/player_skin_luma.png   its glowing parts
  tools/assets/librequake_weapons.json  how each first-person weapon sits in view
                                        and moves when it fires

RAVAGE's weapons are its own futuristic designs (make_models.py builds them),
but they take their size, place in view and firing motion from LibreQuake's:
the json holds each LibreQuake weapon's bounds, and per frame of its firing
animation, the weapon's rigid movement (kick) and the size of its muzzle flash.

LibreQuake's art is BSD-3 licensed; see content/models/LICENSE.librequake and
docs/licensing.md. The skin keeps LibreQuake's painted detail but swaps its
palette: the yellow armour becomes pale ceramic plates, the orange suit a dark
undersuit, and the visor and chest light glow cyan.

The animations are split by the original Quake player frame numbers, one IQM
animation per action (run, stand, attack, pain, death), at 10 frames a second.
The game code picks them by index; keep ANIMS in step with game/shared/anims.qc.

Needs Blender's Python module ("pip install bpy", a Python version that bpy
supports) and a LibreQuake checkout:

  python import_librequake.py <librequake-dir> [content-dir]

Run make_models.py afterwards, since it reads the json. The output is
committed, so building RAVAGE needs neither. LIBREQUAKE_COMMIT is
the revision the committed files came from.
"""

import colorsys
import json
import os
import struct
import sys

import bpy
import numpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_models import png  # noqa: E402

LIBREQUAKE_COMMIT = 'dd4d5bffcabbcf9ceca32a1d83829109928c3f08'
MATERIAL = 'models/player_skin'

# (name, first Quake frame, last Quake frame, loops). Quake frame n is Blender
# frame n + 1. Same order as the PLAYER_ANIM_* constants.
ANIMS = [
    ('stand', 12, 16, True),
    ('run', 6, 11, True),
    ('shoot', 107, 112, False),
    ('pain', 35, 40, False),
    ('death1', 50, 60, False),
    ('death2', 61, 69, False),
    ('death3', 70, 84, False),
    ('death4', 85, 93, False),
    ('death5', 94, 102, False),
    ('shoot_rapid', 103, 104, True),
    ('melee', 119, 124, False),
]
FRAMERATE = 10.0

# Bones whose parts this game never shows: the axe the Quake player swings.
HIDDEN_BONES = {'playeraxe'}


#
# Skin
#

def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def ramp(stops, t):
    """Colour at t (0..1) along evenly spaced colour stops."""
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return lerp(stops[i], stops[i + 1], t - i)


ARMOUR = [(30, 34, 42), (96, 104, 116), (170, 178, 190), (226, 231, 238)]
SUIT = [(10, 12, 16), (30, 35, 44), (62, 70, 84), (98, 108, 124)]
LEATHER = [(12, 13, 16), (36, 40, 48), (70, 76, 88)]
METAL = [(12, 14, 18), (60, 66, 76), (140, 150, 162), (220, 228, 236)]
GLOW = (80, 220, 255)
FLASH = [(40, 120, 255), (150, 230, 255), (255, 255, 255)]

# Regions of the 296x194 skin, as (x0, y0, x1, y1): the visor slot on the
# helmet, the light strip on the chest, and the muzzle flash.
VISOR = (78, 11, 98, 19)
CHEST_LIGHT = (222, 41, 248, 46)
FLASH_STRIPS = ((35, 116, 57, 188), (184, 116, 205, 188))


def inside(box, x, y):
    return box[0] <= x < box[2] and box[1] <= y < box[3]


def recolour(x, y, rgb):
    """Map one LibreQuake skin pixel to (colour, glow) for RAVAGE."""
    r, g, b = (c / 255 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hue = h * 360
    if any(inside(box, x, y) for box in FLASH_STRIPS):
        colour = ramp(FLASH, v * v)
        return colour, colour
    if inside(VISOR, x, y) or (inside(CHEST_LIGHT, x, y) and s > 0.3):
        # Keep the painted grille: darker pixels glow less.
        colour = tuple(c * min(1.0, 0.35 + v) for c in GLOW)
        return colour, tuple(c * 0.5 for c in colour)
    if s < 0.22:
        return ramp(METAL, v * 1.1), None
    if 33 <= hue < 75 and v > 0.12:
        return ramp(ARMOUR, (v - 0.12) / 0.7), None
    if (hue < 25 or hue >= 340) and s > 0.45 and v > 0.45:
        return ramp(SUIT, v), None
    # Browns: belts, gloves, boots and the gun's grip, and the axe's blood.
    return ramp(LEATHER, v * 1.6), None


def write_skin(image, out):
    width, height = image.size
    pixels = image.pixels[:]
    rows, luma_rows = [], []
    for y in range(height):
        row, luma_row = [], []
        src = (height - 1 - y) * width * 4      # Blender stores rows bottom-up
        for x in range(width):
            rgb = tuple(round(pixels[src + x * 4 + k] * 255) for k in range(3))
            colour, glow = recolour(x, y, rgb)
            row.extend(min(255, round(c)) for c in colour)
            luma_row.extend(min(255, round(c)) for c in (glow or (0, 0, 0)))
        rows.append(row)
        luma_rows.append(luma_row)
    png(os.path.join(out, 'player_skin.png'), width, height, rows)
    png(os.path.join(out, 'player_skin_luma.png'), width, height, luma_rows)


#
# Skeleton and mesh
#

def decompose(matrix):
    t, r, s = matrix.decompose()
    # IQM quaternions are x, y, z, w with w positive.
    q = (r.x, r.y, r.z, r.w)
    if r.w < 0:
        q = tuple(-c for c in q)
    return tuple(t) + q + tuple(s)


def joint_local(pose_bone):
    if pose_bone.parent:
        return pose_bone.parent.matrix.inverted() @ pose_bone.matrix
    return pose_bone.matrix.copy()


def rest_local(bone):
    if bone.parent:
        return bone.parent.matrix_local.inverted() @ bone.matrix_local
    return bone.matrix_local.copy()


def collect(arm, mesh_obj):
    bones = list(arm.data.bones)
    index = {b.name: i for i, b in enumerate(bones)}
    joints = [(b.name, index[b.parent.name] if b.parent else -1, decompose(rest_local(b))) for b in bones]

    # The armature sits at the origin unscaled, so armature space is model
    # space. The mesh object's own transform is applied before skinning.
    assert arm.matrix_world.is_identity
    to_model = mesh_obj.matrix_world
    normal_matrix = to_model.to_3x3().inverted().transposed()
    me = mesh_obj.data
    me.calc_loop_triangles()
    groups = {g.index: g.name for g in mesh_obj.vertex_groups}
    uv = me.uv_layers.active.data

    verts, tris, lookup = [], [], {}
    for tri in me.loop_triangles:
        corners = []
        for loop in tri.loops:
            vi = me.loops[loop].vertex_index
            u, v = uv[loop].uv
            key = (vi, round(u, 6), round(v, 6))
            if key not in lookup:
                vert = me.vertices[vi]
                weights = sorted(((g.weight, index[groups[g.group]]) for g in vert.groups
                                  if g.weight > 0 and groups[g.group] in index), reverse=True)[:4]
                total = sum(w for w, _ in weights) or 1
                blend = [round(w / total * 255) for w, _ in weights]
                if blend:
                    blend[0] += 255 - sum(blend)
                blend_index = [j for _, j in weights]
                while len(blend) < 4:
                    blend.append(0)
                    blend_index.append(0)
                hidden = any(bones[j].name in HIDDEN_BONES for w, j in weights if w / total > 0.5)
                lookup[key] = len(verts)
                verts.append((tuple(to_model @ vert.co), (u, 1 - v),
                              tuple((normal_matrix @ vert.normal).normalized()),
                              blend_index, blend, hidden))
            corners.append(lookup[key])
        if all(verts[c][5] for c in corners):
            continue
        # Blender winds triangles counter-clockwise; IQM wants clockwise.
        tris.append((corners[0], corners[2], corners[1]))
    return joints, verts, tris


def sample_poses(scene, arm):
    """Every joint's local transform at every Blender frame, as 10 channels."""
    frames = {}
    first = min(a[1] for a in ANIMS)
    last = max(a[2] for a in ANIMS)
    for quake_frame in range(first, last + 1):
        scene.frame_set(quake_frame + 1)
        frames[quake_frame] = [decompose(joint_local(pb)) for pb in arm.pose.bones]
    return frames


#
# IQM
#

IQM_POSITION, IQM_TEXCOORD, IQM_NORMAL, IQM_BLENDINDEXES, IQM_BLENDWEIGHTS = 0, 1, 2, 4, 5
IQM_UBYTE, IQM_FLOAT = 1, 7
IQM_LOOP = 1


def write_iqm(path, name, joints, verts, tris, poses):
    strings = [b'', name.encode(), MATERIAL.encode()]
    strings += [j[0].encode() for j in joints]
    strings += [a[0].encode() for a in ANIMS]
    text, offsets = b'', {}
    for s in strings:
        if s not in offsets:
            offsets[s] = len(text)
            text += s + b'\0'
    text += b'\0' * (-len(text) % 4)

    def string(s):
        return offsets[s.encode()]

    # Every frame of every animation, in order.
    frame_list = [q for _, first, last, _ in ANIMS for q in range(first, last + 1)]
    channels = []
    for j in range(len(joints)):
        for c in range(10):
            values = [poses[q][j][c] for q in frame_list]
            lo, hi = min(values), max(values)
            channels.append((lo, (hi - lo) / 65535 if hi > lo else 0.0))

    n, nj = len(verts), len(joints)
    nf = len(frame_list)
    header_size = 16 + 27 * 4
    ofs_text = header_size
    ofs_meshes = ofs_text + len(text)
    ofs_varrays = ofs_meshes + 6 * 4
    ofs_pos = ofs_varrays + 5 * 5 * 4
    ofs_uv = ofs_pos + n * 12
    ofs_norm = ofs_uv + n * 8
    ofs_bi = ofs_norm + n * 12
    ofs_bw = ofs_bi + n * 4
    ofs_tris = ofs_bw + n * 4
    ofs_joints = ofs_tris + len(tris) * 12
    ofs_poses = ofs_joints + nj * 48
    ofs_anims = ofs_poses + nj * 88
    ofs_frames = ofs_anims + len(ANIMS) * 20
    size = ofs_frames + nf * nj * 10 * 2
    size += -size % 4

    out = bytearray(b'INTERQUAKEMODEL\0')
    out += struct.pack('<27I',
                       2, size, 0,
                       len(text), ofs_text,
                       1, ofs_meshes,
                       5, n, ofs_varrays,
                       len(tris), ofs_tris, 0,
                       nj, ofs_joints,
                       nj, ofs_poses,
                       len(ANIMS), ofs_anims,
                       nf, nj * 10, ofs_frames, 0,
                       0, 0, 0, 0)
    out += text
    out += struct.pack('<6I', string(name), string(MATERIAL), 0, n, 0, len(tris))
    out += struct.pack('<5I', IQM_POSITION, 0, IQM_FLOAT, 3, ofs_pos)
    out += struct.pack('<5I', IQM_TEXCOORD, 0, IQM_FLOAT, 2, ofs_uv)
    out += struct.pack('<5I', IQM_NORMAL, 0, IQM_FLOAT, 3, ofs_norm)
    out += struct.pack('<5I', IQM_BLENDINDEXES, 0, IQM_UBYTE, 4, ofs_bi)
    out += struct.pack('<5I', IQM_BLENDWEIGHTS, 0, IQM_UBYTE, 4, ofs_bw)
    for v in verts:
        out += struct.pack('<3f', *v[0])
    for v in verts:
        out += struct.pack('<2f', *v[1])
    for v in verts:
        out += struct.pack('<3f', *v[2])
    for v in verts:
        out += struct.pack('<4B', *v[3])
    for v in verts:
        out += struct.pack('<4B', *v[4])
    for tri in tris:
        out += struct.pack('<3I', *tri)
    for joint_name, parent, rest in joints:
        out += struct.pack('<Ii10f', string(joint_name), parent, *rest)
    for j, (_, parent, _) in enumerate(joints):
        offsets_scales = [channels[j * 10 + c][0] for c in range(10)] + [channels[j * 10 + c][1] for c in range(10)]
        out += struct.pack('<iI20f', parent, 0x3FF, *offsets_scales)
    first = 0
    for anim_name, a, b, loops in ANIMS:
        count = b - a + 1
        out += struct.pack('<3IfI', string(anim_name), first, count, FRAMERATE, IQM_LOOP if loops else 0)
        first += count
    for q in frame_list:
        for j in range(nj):
            for c in range(10):
                lo, scale = channels[j * 10 + c]
                out += struct.pack('<H', round((poses[q][j][c] - lo) / scale) if scale else 0)
    out += b'\0' * (size - len(out))
    assert len(out) == size
    with open(path, 'wb') as f:
        f.write(out)


#
# Weapons
#

# RAVAGE weapon: the LibreQuake first-person models it takes its size and
# its firing animation from. The railgun borrows the super nailgun's length
# and the super shotgun's heavy kick.
WEAPONS = {
    'shotgun': ('v_shot', 'v_shot'),
    'machinegun': ('v_nail', 'v_nail'),
    'rocketlauncher': ('v_rock2', 'v_rock2'),
    'grenadelauncher': ('v_rock', 'v_rock'),
    'lightning': ('v_light', 'v_light'),
    'railgun': ('v_nail2', 'v_shot2'),
}


def evaluated_points(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    me = evaluated.to_mesh()
    points = numpy.array([tuple(obj.matrix_world @ v.co) for v in me.vertices])
    evaluated.to_mesh_clear()
    return points


def rigid_fit(rest, moved):
    """Rotation matrix and translation taking rest onto moved (Kabsch)."""
    a, b = rest.mean(axis=0), moved.mean(axis=0)
    u, _, vt = numpy.linalg.svd((rest - a).T @ (moved - b))
    d = numpy.sign(numpy.linalg.det(vt.T @ u.T))
    rot = vt.T @ numpy.diag([1, 1, d]) @ u.T
    return rot, b - rot @ a


def open_weapon(librequake, name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(librequake, 'lq1', 'progs', 'src', name + '.mdl.blend'))
    obj = next(o for o in bpy.data.objects if o.type == 'MESH')
    keys = obj.data.shape_keys.key_blocks
    # Shape keys that show or hide the muzzle flash, and which way round:
    # LibreQuake hides a flash by shrinking it into the barrel.
    basis = numpy.array([tuple(v.co) for v in keys[0].data])
    is_flash = numpy.zeros(len(basis), bool)
    flash_keys = []
    for key in keys[1:]:
        if 'flame' not in key.name and 'fire' not in key.name:
            continue
        shape = numpy.array([tuple(v.co) for v in key.data])
        moved = numpy.linalg.norm(shape - basis, axis=1) > 0.01
        is_flash |= moved
        shows = numpy.ptp(shape[moved], axis=0).max() > numpy.ptp(basis[moved], axis=0).max()
        flash_keys.append((key, shows))
    return obj, is_flash, flash_keys


def weapon_bounds(librequake, name):
    obj, is_flash, _ = open_weapon(librequake, name)
    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
    rest = evaluated_points(obj)[~is_flash]
    return [[round(float(x), 2) for x in rest.min(axis=0)], [round(float(x), 2) for x in rest.max(axis=0)]]


def weapon_motion(librequake, name):
    """Per frame of a weapon's firing animation, its kick and flash."""
    obj, is_flash, flash_keys = open_weapon(librequake, name)
    scene = bpy.context.scene
    frames = []
    rest = None
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)
        body = evaluated_points(obj)[~is_flash]
        if rest is None:
            rest = body
        keep = numpy.ones(len(body), bool)
        # Fit twice, dropping the moving parts (spinning barrels, opening
        # claws) that don't follow the weapon as a whole.
        for _ in range(2):
            rot, move = rigid_fit(rest[keep], body[keep])
            keep = numpy.linalg.norm(rest @ rot.T + move - body, axis=1) < 0.5
        flash = max([k.value if shows else 1 - k.value for k, shows in flash_keys] or [0])
        frames.append({'rotation': [[round(float(x), 4) for x in row] for row in rot],
                       'move': [round(float(x), 3) for x in move],
                       'flash': round(flash, 3)})
    return frames


def write_weapon_motions(librequake, path):
    motions = {name: {'bounds': weapon_bounds(librequake, size_from), 'frames': weapon_motion(librequake, motion_from),
                      'librequake_models': sorted({size_from, motion_from})}
               for name, (size_from, motion_from) in WEAPONS.items()}
    with open(path, 'w') as f:
        json.dump({'librequake_commit': LIBREQUAKE_COMMIT, 'framerate': FRAMERATE, 'weapons': motions},
                  f, indent=1, sort_keys=True)
        f.write('\n')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    librequake = sys.argv[1]
    content = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'models')
    os.makedirs(out, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=os.path.join(librequake, 'lq1', 'progs', 'src', 'player.mdl.blend'))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh_obj = next(o for o in bpy.data.objects if o.type == 'MESH')
    write_skin(bpy.data.images['player.mdl.0.png'], out)
    joints, verts, tris = collect(arm, mesh_obj)
    poses = sample_poses(bpy.context.scene, arm)
    write_iqm(os.path.join(out, 'player.iqm'), 'player', joints, verts, tris, poses)
    print('wrote player.iqm (%d joints, %d vertices, %d triangles, %d animations) to %s'
          % (len(joints), len(verts), len(tris), len(ANIMS), os.path.normpath(out)))
    write_weapon_motions(librequake, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'librequake_weapons.json'))
    print('wrote librequake_weapons.json')


if __name__ == '__main__':
    main()
