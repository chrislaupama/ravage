#!/usr/bin/env python3
"""Import the player, the weapons, the pickups and projectiles from LibreQuake.

Reads LibreQuake's Blender sources (lq1/progs/src/*.mdl.blend), and the
brush models its health and ammo boxes are built from
(lq1/maps/src/brushmodels), and writes content/models:

  player.iqm                    the player's mesh, skeleton and animations
  v_<weapon>.md3                first-person weapons, with idle and fire animations
  v_<weapon>.md3.framegroups    their animations' frame ranges
  g_<weapon>.iqm                weapon pickups
  health*.iqm, ammo_*.iqm       health and ammo pickups, with their skins in pickups/
  armor_*.iqm                   armor pickups
  rocket.iqm, grenade.iqm       projectiles
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
import re
import struct
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iqm import cross, dot, normalize, png, sub, write_iqm  # noqa: E402

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


def brightness_gain(image):
    """How much to brighten image so its brightest twentieth is at full."""
    pixels = image.pixels[:]
    values = sorted(max(pixels[i:i + 3]) for i in range(0, len(pixels), 4))
    values = [v for v in values if v > 0.03] or [1.0]
    return 1 / max(values[len(values) * 19 // 20], 0.1)


def weapon_recolour(energy, image):
    """A recolour for a weapon skin whose hot parts glow in energy.

    LibreQuake's weapons are dark, so brightness is first stretched until
    the brightest twentieth of the skin is at full."""
    gain = brightness_gain(image)

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


def recoloured(image, recolour):
    """image's pixels, recoloured: (rows, glow rows) of 8-bit RGB."""
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
    return rows, luma_rows


def write_png_pair(out, name, rows, luma_rows):
    """Write <name>.png, and its glowing parts, if it has any, as
    <name>_luma.png."""
    width, height = len(rows[0]) // 3, len(rows)
    png(os.path.join(out, name + '.png'), width, height, rows)
    if any(any(row) for row in luma_rows):
        png(os.path.join(out, name + '_luma.png'), width, height, luma_rows)


def write_skin(image, recolour, out, name):
    """Write image, recoloured, as <name>.png and <name>_luma.png."""
    write_png_pair(out, name, *recoloured(image, recolour))


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

#
# Pickups and projectiles
#

def write_mdl_item(librequake, lq, recolour, out, name, skin=0):
    """A static model from one of LibreQuake's .mdl sources, in its own
    coordinates, with skin number skin recoloured."""
    obj, _ = open_blend(librequake, lq)
    image = bpy.data.images[skin]
    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
    corners, tris, positions, normals = sample_mesh(obj)
    write_skin(image, recolour(image), out, name + '_skin')
    verts = [(positions[vi], uv, normals[vi]) for vi, uv in corners]
    write_iqm(os.path.join(out, name + '.iqm'), name, verts, tris, 'models/%s_skin' % name)


def armour_recolour(hue, colour):
    """A recolour for an armor skin: its painted base, of the given hue,
    becomes plating in colour, with the brightest edges glowing, and the
    rest becomes gunmetal."""
    def make(image):
        gain = brightness_gain(image)

        def recolour(x, y, rgb):
            h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
            v = min(1.0, v * gain)
            if s > 0.18 and abs((h * 360 - hue + 180) % 360 - 180) < 18:
                plate = ramp([(10, 12, 16), tuple(c * 0.3 for c in colour), colour,
                              lerp(colour, (255, 255, 255), 0.35)], v)
                return plate, (tuple(c * 0.3 for c in colour) if v > 0.8 else None)
            return ramp(GUNMETAL, v), None
        return recolour
    return make


# LibreQuake's health and ammo boxes are brush models, built in TrenchBroom
# (lq1/maps/src/brushmodels) with textures from texture-wads/lq_health_ammo.
# Each is turned into a mesh, with its textures recoloured in the item's
# energy colour: the medkits' red crosses and the ammo boxes'
# lights glow in it.
BRUSH_ITEMS = {
    # name: (brush model, energy colour, scale)
    'health_small': ('b_bh10', (120, 255, 140), 1.0),
    'health': ('b_bh25', (255, 220, 80), 1.0),
    'health_large': ('b_bh25', (255, 150, 60), 1.25),
    'health_mega': ('b_bh100', (180, 110, 255), 1.0),
    'ammo_shells': ('b_shell1', WEAPONS['shotgun'][1], 1.0),
    'ammo_bullets': ('b_nail1', WEAPONS['machinegun'][1], 1.0),
    'ammo_rockets': ('b_rock1', WEAPONS['rocketlauncher'][1], 1.0),
    'ammo_grenades': ('b_rock0', WEAPONS['grenadelauncher'][1], 1.0),
    'ammo_cells': ('b_batt1', WEAPONS['lightning'][1], 1.0),
    'ammo_slugs': ('b_nail0', WEAPONS['railgun'][1], 1.0),
}

MAP_FACE = re.compile(r'\(([^)]*)\)\s*\(([^)]*)\)\s*\(([^)]*)\)\s*(\S+)\s*'
                      r'\[([^\]]*)\]\s*\[([^\]]*)\]\s*(\S+)\s+(\S+)\s+(\S+)')
EPSILON = 0.01


def read_brushes(path):
    """The brushes of a Valve 220 .map file. A brush is a list of faces:
    (normal, distance, texture, (u axis, u offset), (v axis, v offset),
    (u scale, v scale)). A point x is inside a face's plane when
    dot(normal, x) <= distance."""
    brushes, brush, depth = [], None, 0
    for line in open(path):
        line = line.strip()
        if line == '{':
            depth += 1
            if depth == 2:
                brush = []
        elif line == '}':
            if depth == 2 and brush:
                brushes.append(brush)
            depth -= 1
        elif depth == 2 and line.startswith('('):
            m = MAP_FACE.match(line)
            p0, p1, p2 = (tuple(float(c) for c in m.group(k).split()) for k in (1, 2, 3))
            normal = normalize(cross(sub(p0, p1), sub(p2, p1)))
            u, v = ([float(c) for c in m.group(k).split()] for k in (5, 6))
            brush.append((normal, dot(normal, p1), m.group(4), (u[:3], u[3]), (v[:3], v[3]),
                          (float(m.group(8)), float(m.group(9)))))
    return brushes


def clip(polygon, normal, distance, keep_front=False):
    """The part of a convex polygon behind (or in front of) a plane."""
    sign = -1 if keep_front else 1
    dists = [sign * (dot(normal, p) - distance) for p in polygon]
    out = []
    for i, p in enumerate(polygon):
        q, dp, dq = polygon[(i + 1) % len(polygon)], dists[i], dists[(i + 1) % len(polygon)]
        if dp <= EPSILON:
            out.append(p)
        if (dp < -EPSILON and dq > EPSILON) or (dp > EPSILON and dq < -EPSILON):
            t = dp / (dp - dq)
            out.append(tuple(a + (b - a) * t for a, b in zip(p, q)))
    return out if len(out) >= 3 else []


def brush_polygon(brush, face):
    """The polygon of one face of a convex brush, wound counter-clockwise
    seen from outside."""
    normal, distance = brush[face][:2]
    up = (0, 0, 1) if abs(normal[2]) < 0.9 else (1, 0, 0)
    u = normalize(cross(up, normal))
    v = cross(normal, u)
    centre = tuple(c * distance for c in normal)
    size = 4096
    polygon = [tuple(c + (a * su + b * sv) * size for c, a, b in zip(centre, u, v))
               for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k, (other_normal, other_distance, *_) in enumerate(brush):
        if k != face and polygon:
            polygon = clip(polygon, other_normal, other_distance)
    return polygon


def outside(polygon, normal, brush, first):
    """The parts of a face's polygon that aren't inside another brush, so
    faces hidden where brushes overlap or touch are left out. Where two
    faces lie on top of each other, the one from the earlier brush is
    kept: first says whether that's this face's."""
    parts = []
    for other_normal, other_distance, *_ in brush:
        if all(abs(dot(other_normal, p) - other_distance) < EPSILON for p in polygon):
            if dot(normal, other_normal) > 0 and first:
                return parts + [polygon]
            continue
        front = clip(polygon, other_normal, other_distance, keep_front=True)
        if front:
            parts.append(front)
        polygon = clip(polygon, other_normal, other_distance)
        if not polygon:
            return parts
    return parts


def texture_path(librequake, texture):
    base = os.path.join(librequake, 'texture-wads', 'lq_health_ammo', texture.replace('+', 'plus_'))
    return base + '.png' if os.path.exists(base + '.png') else base + '_fbr.png'


def split_tiles(polygon, axes):
    """Split a polygon where its texture repeats: along every whole number
    of each texture coordinate. axes are (vector, offset) per coordinate,
    giving it as dot(vector, point) + offset."""
    pieces = [polygon]
    for vector, offset in axes:
        length = math.sqrt(dot(vector, vector))
        normal = tuple(c / length for c in vector)
        values = [dot(vector, p) + offset for p in polygon]
        for k in range(math.floor(min(values)) + 1, math.ceil(max(values))):
            distance = (k - offset) / length
            pieces = [part for piece in pieces
                      for part in (clip(piece, normal, distance), clip(piece, normal, distance, keep_front=True)) if part]
    return pieces


TILE_PAD = 4    # texels of repeated texture around each tile in an atlas


def write_brush_item(librequake, lq, energy, scale, out, name):
    brushes = read_brushes(os.path.join(librequake, 'lq1', 'maps', 'src', 'brushmodels', lq + '.map'))
    faces = []      # (polygon, face)
    for b, brush in enumerate(brushes):
        for f, face in enumerate(brush):
            pieces = [brush_polygon(brush, f)]
            for o, other in enumerate(brushes):
                if o != b:
                    pieces = [part for piece in pieces if piece for part in outside(piece, face[0], other, b < o)]
            faces.extend((piece, face) for piece in pieces if piece)

    # Centre the item on its origin, standing on the floor, so it spins in
    # place. The floor hides its underside, so that is left out.
    points = [p for polygon, _ in faces for p in polygon]
    lo = [min(p[k] for p in points) for k in range(3)]
    hi = [max(p[k] for p in points) for k in range(3)]
    centre = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
    faces = [(polygon, face) for polygon, face in faces
             if not (face[0][2] < -0.99 and all(abs(p[2] - lo[2]) < EPSILON for p in polygon))]

    # One skin per item, so it draws in one go: its textures, recoloured,
    # side by side in an atlas. Faces are cut where their texture repeats,
    # so each piece maps onto one copy of it.
    textures = sorted({face[2] for _, face in faces})
    images = [bpy.data.images.load(texture_path(librequake, t)) for t in textures]
    size = images[0].size[0]
    assert all(tuple(image.size) == (size, size) for image in images), 'textures must be square and the same size'
    columns = math.ceil(math.sqrt(len(textures)))
    tile_rows = math.ceil(len(textures) / columns)
    slot = size + 2 * TILE_PAD
    width, height = columns * slot, tile_rows * slot
    atlas = [[0] * (width * 3) for _ in range(height)]
    luma = [[0] * (width * 3) for _ in range(height)]
    for i, image in enumerate(images):
        tile, glow = recoloured(image, weapon_recolour(energy, image))
        x0, y0 = (i % columns) * slot, (i // columns) * slot
        for y in range(slot):
            for x in range(slot):
                sx, sy = (x - TILE_PAD) % size, (y - TILE_PAD) % size
                atlas[y0 + y][(x0 + x) * 3:(x0 + x) * 3 + 3] = tile[sy][sx * 3:sx * 3 + 3]
                luma[y0 + y][(x0 + x) * 3:(x0 + x) * 3 + 3] = glow[sy][sx * 3:sx * 3 + 3]
        bpy.data.images.remove(image)
    skins = os.path.join(out, 'pickups')
    os.makedirs(skins, exist_ok=True)
    write_png_pair(skins, name, atlas, luma)

    verts, tris = [], []
    for polygon, (normal, _, texture, (u_axis, u_offset), (v_axis, v_offset), (u_scale, v_scale)) in faces:
        # Texture coordinates in copies of the texture.
        axes = ((tuple(c / (u_scale * size) for c in u_axis), u_offset / size),
                (tuple(c / (v_scale * size) for c in v_axis), v_offset / size))
        i = textures.index(texture)
        x0, y0 = (i % columns) * slot + TILE_PAD, (i // columns) * slot + TILE_PAD
        for piece in split_tiles(polygon, axes):
            uvs = [tuple(dot(vector, p) + offset for vector, offset in axes) for p in piece]
            tile = [math.floor(sum(c) / len(uvs)) for c in zip(*uvs)]
            first = len(verts)
            for p, uv in zip(piece, uvs):
                position = tuple(round((c - o) * scale, 3) for c, o in zip(p, centre))
                verts.append((position, ((x0 + (uv[0] - tile[0]) * size) / width,
                                         (y0 + (uv[1] - tile[1]) * size) / height), normal))
            for k in range(1, len(piece) - 1):
                # IQM front faces wind clockwise as seen from outside.
                tris.append((first, first + k + 1, first + k))
    write_iqm(os.path.join(out, name + '.iqm'), name, verts, tris, 'models/pickups/' + name)


ARMOURS = {
    # name: (skin, the skin's painted hue, colour)
    'armor_light': (0, 135, (120, 255, 140)),
    'armor_medium': (1, 42, (255, 210, 70)),
    'armor_heavy': (2, 0, (255, 70, 60)),
}
SHARD = (25, (255, 160, 60))      # the shard's painted hue, and its colour

MDL_ITEMS = {
    # name: (model, energy colour)
    'rocket': ('missile', WEAPONS['rocketlauncher'][1]),
    'grenade': ('grenade', WEAPONS['grenadelauncher'][1]),
}


def write_items(librequake, out):
    for name, (skin, hue, colour) in ARMOURS.items():
        write_mdl_item(librequake, 'armor', armour_recolour(hue, colour), out, name, skin)
    write_mdl_item(librequake, 'armorshard', armour_recolour(*SHARD), out, 'armor_shard')
    for name, (lq, energy) in MDL_ITEMS.items():
        write_mdl_item(librequake, lq, lambda image, energy=energy: weapon_recolour(energy, image), out, name)
    for name, (lq, energy, scale) in BRUSH_ITEMS.items():
        write_brush_item(librequake, lq, energy, scale, out, name)


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
    write_items(librequake, out)
    print('wrote the player, %d weapons and %d pickups and projectiles to %s'
          % (len(WEAPONS), len(ARMOURS) + 1 + len(MDL_ITEMS) + len(BRUSH_ITEMS), os.path.normpath(out)))


if __name__ == '__main__':
    main()
