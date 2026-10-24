#!/usr/bin/env python3
"""Import the player and the weapons from LibreQuake.

Reads LibreQuake's Blender sources (lq1/progs/src/*.mdl.blend) and writes
content/models:

  player.iqm                    the player's mesh, skeleton and animations
  v_<weapon>.md3                first-person weapons, with idle and fire animations
  v_<weapon>.md3.framegroups    their animations' frame ranges
  g_<weapon>.iqm                weapon pickups
  *_skin.png, *_skin_luma.png   LibreQuake's skins, recoloured for RAVAGE, and
                                their glowing parts

LibreQuake's art is BSD-3 licensed; see content/models/LICENSE.librequake and
docs/licensing.md. The skins keep LibreQuake's painted detail but swap its
steampunk palette for RAVAGE's: wood and brass become pale ceramic, iron
becomes cool gunmetal, and muzzle flashes, the player's visor and other hot
parts glow in each weapon's energy colour.

The player's animations are split by the original Quake player frame
numbers, one IQM animation per action, at 10 frames a second. The game code
picks them by index; keep ANIMS in step with game/ssqc/anims.qc.

LibreQuake animates its weapons by morphing vertices (shape keys), which IQM
can't store, so the first-person weapons are MD3: every frame of the mesh,
sampled from Blender. The first frame is the weapon at rest ("idle"), the
rest its firing animation ("fire"); game/csqc/view.qc plays them.

Needs Blender's Python module ("pip install bpy", a Python version that bpy
supports) and a LibreQuake checkout:

  python import_librequake.py <librequake-dir> [content-dir]

The output is committed and deterministic, so building RAVAGE needs neither.
LIBREQUAKE_COMMIT is the revision the committed files came from.
"""

import colorsys
import math
import os
import struct
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_models import png, write_iqm  # noqa: E402

LIBREQUAKE_COMMIT = 'dd4d5bffcabbcf9ceca32a1d83829109928c3f08'

# (name, first Quake frame, last Quake frame, loops). Quake frame n is Blender
# frame n + 1. Same order as the ANIM_* constants in game/ssqc/anims.qc.
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


def recolour_player(x, y, rgb):
    """Map one pixel of LibreQuake's player skin to (colour, glow)."""
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


GUNMETAL = [(8, 10, 14), (40, 48, 60), (104, 116, 132), (186, 198, 214), (238, 244, 250)]


def weapon_recolour(energy, image):
    """A recolour for a weapon skin whose hot parts glow in energy.

    LibreQuake's weapons are dark, so brightness is first stretched until
    the brightest twentieth of the skin is at full."""
    pixels = image.pixels[:]
    values = sorted(max(pixels[i:i + 3]) for i in range(0, len(pixels), 4))
    values = [v for v in values if v > 0.03] or [1.0]
    gain = 1 / max(values[len(values) * 19 // 20], 0.1)

    def recolour(x, y, rgb):
        r, g, b = (c / 255 for c in rgb)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        hue = h * 360
        if s > 0.6 and v > 0.55 and (hue < 55 or hue >= 340):
            # Muzzle flashes and glowing cells.
            colour = lerp(energy, (255, 255, 255), max(0.0, v - 0.75) * 2)
            return colour, tuple(c * 0.5 for c in colour)
        v = min(1.0, v * gain)
        if 90 <= hue < 200 and s > 0.15:
            # Green-tinted iron becomes dark metal with energy-lit edges.
            colour = lerp((14, 18, 24), energy, v ** 2)
            return colour, (tuple(c * 0.35 for c in colour) if v > 0.6 else None)
        if 12 <= hue < 65 and s > 0.25:
            # Wood and brass become ceramic.
            return ramp(ARMOUR, v * 1.1), None
        if s < 0.3:
            return ramp(GUNMETAL, v), None
        return ramp(LEATHER, v * 1.3), None
    return recolour


def write_skin(image, recolour, out, name):
    """Write image, recoloured, as <name>.png and <name>_luma.png."""
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
    png(os.path.join(out, name + '.png'), width, height, rows)
    png(os.path.join(out, name + '_luma.png'), width, height, luma_rows)


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


def write_player(librequake, out):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(librequake, 'lq1', 'progs', 'src', 'player.mdl.blend'))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh_obj = next(o for o in bpy.data.objects if o.type == 'MESH')
    write_skin(bpy.data.images['player.mdl.0.png'], recolour_player, out, 'player_skin')
    joints, verts, tris = collect(arm, mesh_obj)
    poses = sample_poses(bpy.context.scene, arm)
    anims, frames = [], []
    for anim_name, first, last, loops in ANIMS:
        anims.append((anim_name, len(frames), last - first + 1, FRAMERATE, loops))
        frames += [poses[q] for q in range(first, last + 1)]
    write_iqm(os.path.join(out, 'player.iqm'), 'player', [v[:3] for v in verts], tris,
              material='models/player_skin', blend=[(v[3], v[4]) for v in verts],
              joints=joints, anims=anims, frames=frames)


#
# Weapons
#

# RAVAGE weapon: (LibreQuake model, energy colour). The railgun is
# LibreQuake's super nailgun.
WEAPONS = {
    'shotgun': ('shot', (255, 150, 60)),
    'machinegun': ('nail', (255, 170, 70)),
    'rocketlauncher': ('rock2', (255, 110, 50)),
    'grenadelauncher': ('rock', (120, 255, 140)),
    'lightning': ('light', (90, 220, 255)),
    'railgun': ('nail2', (120, 255, 140)),
}


def open_blend(librequake, name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(librequake, 'lq1', 'progs', 'src', name + '.mdl.blend'))
    return next(o for o in bpy.data.objects if o.type == 'MESH'), bpy.data.images[0]


def sample_mesh(obj):
    """The mesh at the current frame: (corners, triangles). Corners are
    (vertex, uv) pairs, so a vertex with two texture coordinates is split;
    positions and normals are per evaluated vertex, in model space."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    me = evaluated.to_mesh()
    me.calc_loop_triangles()
    uv = me.uv_layers.active.data
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    positions = [tuple(obj.matrix_world @ v.co) for v in me.vertices]
    normals = [tuple((normal_matrix @ v.normal).normalized()) for v in me.vertices]
    corners, tris, lookup = [], [], {}
    for tri in me.loop_triangles:
        ids = []
        for loop in tri.loops:
            vi = me.loops[loop].vertex_index
            u, v = uv[loop].uv
            key = (vi, round(u, 6), round(v, 6))
            if key not in lookup:
                lookup[key] = len(corners)
                corners.append((vi, (u, 1 - v)))
            ids.append(lookup[key])
        # Blender winds triangles counter-clockwise; IQM and MD3 want clockwise.
        tris.append((ids[0], ids[2], ids[1]))
    evaluated.to_mesh_clear()
    return corners, tris, positions, normals


def write_pickup(librequake, lq, energy, out, name):
    obj, image = open_blend(librequake, 'g_' + lq)
    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
    corners, tris, positions, normals = sample_mesh(obj)
    write_skin(image, weapon_recolour(energy, image), out, name + '_skin')
    verts = [(positions[vi], uv, normals[vi]) for vi, uv in corners]
    write_iqm(os.path.join(out, name + '.iqm'), name, verts, tris, material='models/%s_skin' % name)


def md3_normal(n):
    lat = round(math.acos(max(-1.0, min(1.0, n[2]))) * 255 / (2 * math.pi)) & 255
    lng = round(math.atan2(n[1], n[0]) * 255 / (2 * math.pi)) & 255
    return lat << 8 | lng


def name_field(text, size):
    return text.encode().ljust(size, b'\0')


def write_md3(path, name, material, corners, tris, frames):
    """frames: per frame, (positions, normals) per evaluated vertex."""
    nv, nt, nf = len(corners), len(tris), len(frames)
    surf_header = 4 + 64 + 4 * 10
    ofs_shaders = surf_header
    ofs_tris = ofs_shaders + 68
    ofs_st = ofs_tris + nt * 12
    ofs_xyz = ofs_st + nv * 8
    surf_size = ofs_xyz + nf * nv * 8
    header = 4 + 4 + 64 + 4 * 9
    ofs_frames = header
    ofs_surfaces = ofs_frames + nf * 56

    out = bytearray(b'IDP3')
    out += struct.pack('<i', 15) + name_field(name, 64)
    out += struct.pack('<9i', 0, nf, 0, 1, 0, ofs_frames, ofs_surfaces, ofs_surfaces, ofs_surfaces + surf_size)
    for k, (positions, _) in enumerate(frames):
        lo = [min(p[i] for p in positions) for i in range(3)]
        hi = [max(p[i] for p in positions) for i in range(3)]
        radius = max(math.sqrt(sum(c * c for c in p)) for p in positions)
        out += struct.pack('<10f', *lo, *hi, 0, 0, 0, radius) + name_field('frame%d' % k, 16)
    out += b'IDP3' + name_field(name, 64)
    out += struct.pack('<10i', 0, nf, 1, nv, nt, ofs_tris, ofs_shaders, ofs_st, ofs_xyz, surf_size)
    out += name_field(material, 64) + struct.pack('<i', 0)
    for tri in tris:
        out += struct.pack('<3i', *tri)
    for _, uv in corners:
        out += struct.pack('<2f', *uv)
    for positions, normals in frames:
        for vi, _ in corners:
            out += struct.pack('<3hH', *(round(c * 64) for c in positions[vi]), md3_normal(normals[vi]))
    with open(path, 'wb') as f:
        f.write(out)


def write_view_weapon(librequake, lq, energy, out, name):
    obj, image = open_blend(librequake, 'v_' + lq)
    scene = bpy.context.scene
    write_skin(image, weapon_recolour(energy, image), out, name + '_skin')
    frames = []
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)
        corners, tris, positions, normals = sample_mesh(obj)
        frames.append((positions, normals))
    write_md3(os.path.join(out, name + '.md3'), name, 'models/%s_skin' % name, corners, tris, frames)
    with open(os.path.join(out, name + '.md3.framegroups'), 'w') as f:
        # first frame, frame count, frames per second, loops, name
        f.write('0 1 %g true idle\n' % FRAMERATE)
        f.write('1 %d %g false fire\n' % (len(frames) - 1, FRAMERATE))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    librequake = sys.argv[1]
    content = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'models')
    os.makedirs(out, exist_ok=True)
    write_player(librequake, out)
    for name, (lq, energy) in WEAPONS.items():
        write_view_weapon(librequake, lq, energy, out, 'v_' + name)
        write_pickup(librequake, lq, energy, out, 'g_' + name)
    print('wrote the player and %d weapons to %s' % (len(WEAPONS), os.path.normpath(out)))


if __name__ == '__main__':
    main()
