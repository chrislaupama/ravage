#!/usr/bin/env python3
"""IQM and PNG writers for the asset scripts.

Only the Python standard library is used, and the output is
deterministic: the same input always gives byte-identical files.
"""

import math
import struct
import zlib


def read_png(path):
    """Read our deterministic, unfiltered 8-bit RGB asset-source PNGs.

    Kept deliberately narrow: these sources are normalized by png(), not
    arbitrary artist exports. No Pillow or Blender dependency for skin builds.
    """
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG: %s' % path)
    offset, compressed = 8, bytearray()
    width = height = None
    while offset < len(data):
        size, = struct.unpack_from('>I', data, offset)
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        crc, = struct.unpack_from('>I', data, offset + 8 + size)
        if zlib.crc32(kind + body) != crc:
            raise ValueError('PNG checksum mismatch: %s' % path)
        if kind == b'IHDR':
            width, height, depth, colour, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
            if (depth, colour, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ValueError('expected normalized RGB asset source: %s' % path)
        elif kind == b'IDAT':
            compressed.extend(body)
        elif kind == b'IEND':
            break
        offset += size + 12
    raw = zlib.decompress(compressed)
    stride = width * 3 + 1
    if len(raw) != stride * height or any(raw[y * stride] for y in range(height)):
        raise ValueError('expected unfiltered RGB asset source: %s' % path)
    return width, height, [raw[y * stride + 1:(y + 1) * stride] for y in range(height)]


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


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def normalize(a):
    length = math.sqrt(dot(a, a)) or 1
    return tuple(x / length for x in a)


IQM_POSITION, IQM_TEXCOORD, IQM_NORMAL, IQM_BLENDINDEXES, IQM_BLENDWEIGHTS = 0, 1, 2, 4, 5
IQM_UBYTE, IQM_FLOAT = 1, 7
IQM_LOOP = 1


def write_iqm(path, name, verts, tris, material, blend=None, joints=(), anims=(), frames=()):
    """Write an IQM model.

    verts are (position, uv, normal) and tris index them, wound clockwise.
    material is the skin's path without its extension.
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
