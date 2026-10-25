#!/usr/bin/env python3
"""Render the actual IQM/MD3 meshes and their skins for offline art review.

Needs Pillow and numpy (review tooling only). This is a UV/material preview,
not a game capture or a replacement for checking the assets in RAVAGE.

  python preview_skins.py [content-dir] [output-dir]
"""
import math
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw


def transform(values):
    tx, ty, tz, x, y, z, w, sx, sy, sz = values
    m = np.eye(4)
    m[:3, :3] = np.array([
        [1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w],
        [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w],
        [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]]) @ np.diag([sx, sy, sz])
    m[:3, 3] = tx, ty, tz
    return m


def read_model(path):
    d = path.read_bytes()
    if path.suffix == '.md3':
        surface, = struct.unpack_from('<I', d, 100)
        _, _, _, nv, nt, ot, osh, ouv, ov, _ = struct.unpack_from('<10I', d, surface+68)
        pos = np.array([struct.unpack_from('<3h', d, surface+ov+i*8) for i in range(nv)], dtype=float)/64
        uv = np.array([struct.unpack_from('<2f', d, surface+ouv+i*8) for i in range(nv)])
        tris = np.array([struct.unpack_from('<3I', d, surface+ot+i*12) for i in range(nt)])
        material = d[surface+osh:surface+osh+64].split(b'\0')[0].decode()
        return pos, uv, tris, material
    h = struct.unpack_from('<27I', d, 16)
    arrays = {}
    for i in range(h[7]):
        kind, _, fmt, size, off = struct.unpack_from('<5I', d, h[9]+20*i)
        arrays[kind] = np.array([struct.unpack_from('<'+('f' if fmt==7 else 'B')*size, d,
                                                     off+j*size*(4 if fmt==7 else 1)) for j in range(h[8])])
    pos, uv = arrays[0], arrays[1]
    tris = np.array([struct.unpack_from('<3I', d, h[11]+i*12) for i in range(h[10])])
    material_off, = struct.unpack_from('<I', d, h[6]+4)
    start = h[4]+material_off
    material = d[start:d.index(b'\0', start)].decode()
    if h[13] and h[19]:
        bind, posed = [], []
        channels = struct.unpack_from('<%dH' % h[20], d, h[21])
        cursor = 0
        for j in range(h[13]):
            joint = struct.unpack_from('<Ii10f', d, h[14]+j*48)
            parent = joint[1]
            b = transform(joint[2:])
            if parent >= 0:
                b = bind[parent] @ b
            bind.append(b)
            pose = struct.unpack_from('<iI20f', d, h[16]+j*88)
            values = list(pose[2:12])
            for k in range(10):
                if pose[1] & (1<<k):
                    values[k] += channels[cursor]*pose[12+k]
                    cursor += 1
            p = transform(values)
            if parent >= 0:
                p = posed[parent] @ p
            posed.append(p)
        matrices = [p @ np.linalg.inv(b) for p,b in zip(posed,bind)]
        points = np.c_[pos,np.ones(len(pos))]
        result = np.zeros_like(points)
        for k in range(4):
            for j,m in enumerate(matrices):
                selected = arrays[4][:,k] == j
                result[selected] += (points[selected] @ m.T)*(arrays[5][selected,k,None]/255)
        pos = result[:,:3]
    return pos, uv, tris, material


def render(path, content, size=(360,300), angle=35):
    pos, uv, tris, material = read_model(path)
    # Discard unreferenced vertices such as the hidden player axe.
    lo, hi = pos[np.unique(tris)].min(axis=0),pos[np.unique(tris)].max(axis=0)
    pos = pos-(lo+hi)/2
    a = math.radians(angle)
    # Quake Z is up; camera sees front and one side, with a little top.
    right = np.array([math.cos(a), math.sin(a),0])
    forward = np.array([-math.sin(a), math.cos(a),0])
    elev = math.radians(15)
    up = np.array([0,0,math.cos(elev)])-forward*math.sin(elev)
    toward = forward*math.cos(elev)+np.array([0,0,math.sin(elev)])
    coords = np.stack([pos@right, -(pos@up), pos@toward],axis=1)
    used=coords[np.unique(tris)]
    scale=min((size[0]-32)/max(np.ptp(used[:,0]),1),(size[1]-32)/max(np.ptp(used[:,1]),1))
    coords[:,:2] = (coords[:,:2]-(used[:,:2].min(0)+used[:,:2].max(0))/2)*scale+np.array(size)/2
    tex=np.asarray(Image.open(content/(material+'.png')).convert('RGB'),dtype=float)
    lp=content/(material+'_luma.png')
    luma=np.asarray(Image.open(lp).convert('RGB'),dtype=float) if lp.exists() else np.zeros_like(tex)
    canvas=np.full((size[1],size[0],3),(27,31,36),dtype=float)
    depth=np.full((size[1],size[0]),-np.inf)
    light=np.array([-0.35,-0.45,0.82]);light/=np.linalg.norm(light)
    for tri in tris:
        pts=coords[tri];p0,p1,p2=pts
        xmin=max(0,int(np.floor(pts[:,0].min())));xmax=min(size[0]-1,int(np.ceil(pts[:,0].max())))
        ymin=max(0,int(np.floor(pts[:,1].min())));ymax=min(size[1]-1,int(np.ceil(pts[:,1].max())))
        den=(p1[1]-p2[1])*(p0[0]-p2[0])+(p2[0]-p1[0])*(p0[1]-p2[1])
        if abs(den)<1e-8 or xmax<xmin or ymax<ymin:continue
        yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1];xx=xx+0.5;yy=yy+0.5
        w0=((p1[1]-p2[1])*(xx-p2[0])+(p2[0]-p1[0])*(yy-p2[1]))/den
        w1=((p2[1]-p0[1])*(xx-p2[0])+(p0[0]-p2[0])*(yy-p2[1]))/den
        w2=1-w0-w1; z=w0*p0[2]+w1*p1[2]+w2*p2[2]
        region=depth[ymin:ymax+1,xmin:xmax+1]
        mask=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(z>region)
        if not mask.any():continue
        tuv=w0[...,None]*uv[tri[0]]+w1[...,None]*uv[tri[1]]+w2[...,None]*uv[tri[2]]
        tx=np.clip((tuv[:,:,0]*tex.shape[1]).astype(int),0,tex.shape[1]-1)
        ty=np.clip((tuv[:,:,1]*tex.shape[0]).astype(int),0,tex.shape[0]-1)
        n=np.cross(pos[tri[1]]-pos[tri[0]],pos[tri[2]]-pos[tri[0]])
        n/=max(np.linalg.norm(n),1e-10)
        # Two-sided preview, independent of engine culling. Ambient keeps
        # the original painted texture shading visible.
        shade=.70+.30*abs(n@light)
        rgb=np.maximum(tex[ty,tx]*shade,luma[ty,tx])
        canvas[ymin:ymax+1,xmin:xmax+1][mask]=rgb[mask];region[mask]=z[mask]
    return Image.fromarray(np.uint8(np.clip(canvas,0,255)))


def sheet(content, output, title, names, cols=3, angle=35):
    cw,ch=400,350;rows=(len(names)+cols-1)//cols
    im=Image.new('RGB',(cols*cw,rows*ch+90),(20,24,29));d=ImageDraw.Draw(im)
    d.text((24,18),title,fill=(235,231,216),font_size=25)
    d.text((24,52),'ACTUAL MESH + TEXTURE PREVIEW / NOT AN IN-GAME CAPTURE',fill=(150,165,175),font_size=14)
    for i,(label,name) in enumerate(names):
        x=i%cols*cw;y=i//cols*ch+85
        p=content/'models'/name
        if not p.suffix:p=p.with_suffix('.iqm')
        view_angle = -55 if name.startswith('armor_') and name != 'armor_shard' else angle
        im.paste(render(p,content,angle=view_angle),(x+20,y))
        d.text((x+22,y+310),label,fill=(230,230,220),font_size=18)
    im.save(output)


def main():
    content=Path(sys.argv[1] if len(sys.argv)>1 else 'content')
    out=Path(sys.argv[2] if len(sys.argv)>2 else 'build/skin-review');out.mkdir(parents=True,exist_ok=True)
    sheet(content,out/'weapons-preview.png','BONE CIRCUIT / WEAPONS',[
        (n.upper(),'v_'+n+'.md3') for n in ('shotgun','machinegun','rocketlauncher','grenadelauncher','lightning','railgun')],angle=125)
    sheet(content,out/'player-preview.png','BONE CIRCUIT / CIRCUIT PLAYER',[
        ('FRONT','player'),('THREE QUARTER','player'),('BACK','player')],angle=-55)
    # Replace repeated player tiles with front / rear cameras.
    im=Image.open(out/'player-preview.png')
    im.paste(render(content/'models/player.iqm',content,angle=-90),(20,85))
    im.paste(render(content/'models/player.iqm',content,angle=90),(820,85));im.save(out/'player-preview.png')
    names=['health_small','health','health_large','health_mega','armor_shard','armor_light','armor_medium','armor_heavy',
           'ammo_shells','ammo_bullets','ammo_rockets','ammo_grenades','ammo_cells','ammo_slugs']
    sheet(content,out/'pickups-preview.png','BONE CIRCUIT / PICKUPS',[(n.upper().replace('_',' '),n) for n in names],cols=4)
    sheet(content,out/'weapon-pickups-preview.png','BONE CIRCUIT / WORLD WEAPONS',[
        (n.upper(),'g_'+n) for n in ('shotgun','machinegun','rocketlauncher','grenadelauncher','lightning','railgun')],angle=125)
    print('wrote UV/material review sheets to',out)


if __name__=='__main__':main()
