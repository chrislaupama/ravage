#!/usr/bin/env python3
"""Author clean Bone Circuit material maps on the existing weapon UVs.

Artist tool: needs numpy and Pillow. No original diffuse pixel is used for a
weapon surface; the upstream image is sampled ONLY inside explicit flash UVs.
Output channels: R=material ID, G=surface shade, B=emission strength. Runtime
skins rebuild from these committed maps using the standard-library importer.
"""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image

from iqm import png
from preview_skins import read_model

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent/'source/weapon-materials'
SIZE = 1024
# Component IDs come from welded, connected mesh parts, sorted by vertex count.
# Each assignment follows a physical housing / barrel / grip boundary.
# 1=color paint, 2=ivory, 3=graphite, 4=steel, 5=rubber, 6=lamp,
# 7=muzzle flash, 8=ink, 9=bright steel, 10=dark inset in identity paint.
LAYOUTS = {
    'shotgun': [(1,'circuit_stock'),(4,'circuit_tube'),(1,'circuit_pump'),(1,'circuit_shroud'),(4,'circuit_bore'),(2,'circuit_coupling'),(3,'circuit_rail'),(3,'plain')],
    'machinegun': [(1,'circuit_feeddrum'),(5,'circuit_grip'),(5,'circuit_grip'),(1,'circuit_shroud'),(2,'circuit_bore'),(2,'circuit_bore'),(3,'circuit_rail'),(4,'circuit_tube'),(4,'circuit_tube'),(7,'flash'),(7,'flash'),(3,'plain')],
    'rocketlauncher': [(1,'rocket_shroud'),(5,'rocket_grip'),(5,'rocket_grip'),(1,'rocket_breech'),(7,'flash'),(2,'rocket_coupling'),(3,'rocket_heatsink'),(3,'plain')],
    'grenadelauncher': [(1,'circuit_chamber'),(1,'circuit_shroud'),(5,'circuit_grip'),(4,'circuit_tube'),(3,'plain'),(5,'circuit_grip'),(2,'circuit_coupling'),(4,'circuit_bore'),(4,'circuit_bore'),(3,'plain'),(2,'circuit_capacitor')],
    'lightning': [(1,'circuit_shroud'),(2,'circuit_stock'),(3,'circuit_lead'),(3,'circuit_lead'),(2,'circuit_coupling'),(3,'circuit_insulator'),(3,'circuit_insulator'),(3,'circuit_insulator'),(3,'circuit_insulator'),(3,'circuit_insulator'),(9,'circuit_tip'),(9,'circuit_tip'),(9,'circuit_tip'),(3,'plain'),(4,'circuit_heatsink'),(4,'circuit_heatsink'),(4,'circuit_heatsink'),(4,'circuit_heatsink'),(1,'circuit_receiver'),(1,'circuit_arm'),(1,'circuit_arm'),(1,'circuit_arm'),(7,'flash'),(7,'flash'),(3,'plain')],
    'railgun': [(1,'circuit_shroud'),(5,'circuit_grip'),(2,'circuit_capacitor'),(5,'circuit_grip'),(1,'circuit_receiver'),(3,'circuit_heatsink'),(2,'circuit_coupling'),(3,'plain'),(7,'flash')],
}
FLASH_RECTS = {'shotgun':(10,170,76,200),'machinegun':(55,156,87,188),
               'rocketlauncher':(47,38,77,74),'lightning':(79,172,104,197),'railgun':(100,30,127,57)}


def components(pos, tris):
    parent = list(range(len(pos)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def join(a,b):
        parent[find(a)] = find(b)
    seen = {}
    for i,p in enumerate(pos):
        key = tuple(np.round(p,3))
        if key in seen:
            join(i,seen[key])
        else:
            seen[key] = i
    for a,b,c in tris:
        join(a,b);join(b,c)
    groups = {}
    for i in range(len(pos)):
        groups.setdefault(find(i),[]).append(i)
    return sorted(groups.values(),key=len,reverse=True)


def occlusion(pos, tris, groups):
    """Bake soft contact shade from geometry, independent of old textures."""
    normals = np.zeros_like(pos)
    for g in groups:
        members = set(g)
        centre = (pos[g].min(0)+pos[g].max(0))/2
        for tri in tris:
            if tri[0] not in members:
                continue
            p = pos[tri]
            n = np.cross(p[1]-p[0],p[2]-p[0])
            if np.dot(n,p.mean(0)-centre)<0:
                n = -n
            n /= max(np.linalg.norm(n),1e-9)
            for i in tri:
                normals[i] += n
        # Smooth across UV duplicates before casting rays.
        weld = {}
        for i in g:
            weld.setdefault(tuple(np.round(pos[i],3)),[]).append(i)
        for ids in weld.values():
            normal = normals[ids].sum(0)
            normals[ids] = normal/max(np.linalg.norm(normal),1e-9)
    triangles = pos[tris]
    v0 = triangles[:,0]
    e1,e2 = triangles[:,1]-v0,triangles[:,2]-v0
    result = np.ones(len(pos))
    for i,(point,n) in enumerate(zip(pos,normals)):
        if np.linalg.norm(n)<.1:
            continue
        helper = np.eye(3)[np.argmin(abs(n))]
        t1 = np.cross(n,helper);t1/=np.linalg.norm(t1)
        t2 = np.cross(n,t1)
        rays = []
        for k in range(16):
            radius = np.sqrt((k+.5)/16)
            angle = k*2.39996323
            rays.append(n*np.sqrt(1-radius*radius)+radius*(np.cos(angle)*t1+np.sin(angle)*t2))
        rays = np.asarray(rays)
        h = np.cross(rays[:,None,:],e2[None,:,:])
        det = np.einsum('ti,rti->rt',e1,h)
        inv = np.divide(1,det,out=np.zeros_like(det),where=abs(det)>1e-8)
        tv = point+n*.04-v0
        u = np.einsum('ti,rti->rt',tv,h)*inv
        q = np.cross(tv,e1)
        v = np.einsum('ri,ti->rt',rays,q)*inv
        distance = np.einsum('ti,ti->t',e2,q)[None,:]*inv
        hit = (abs(det)>1e-8)&(u>=0)&(v>=0)&(u+v<=1)&(distance>.045)&(distance<4)
        nearest = np.where(hit,distance,1e6).min(1)
        result[i] = 1-.24*np.exp(-nearest/2.0).mean()
    return result


def paint(points, normal, bounds, material, style):
    """Part-based Bone Circuit finish; no labels or decorative light boxes."""
    lo,hi = bounds
    q = (points-lo)/np.maximum(hi-lo,0.001)
    if style.startswith('rocket_'):
        return paint_rocket(q,normal,material,style)
    if style.startswith('circuit_'):
        return paint_circuit(q,normal,material,style)
    # Preserve the approved rocket's plain trigger and world muzzle cap.
    shape = q.shape[:-1]
    mat = np.full(shape,material,dtype=np.uint8)
    shade = np.minimum(244,np.uint8(np.clip(236+q[...,2]*12,0,255)))
    if style == 'bore' and int(np.argmax(abs(normal))) == 0:
        radius = np.sqrt(((q[...,1]-.5)*2)**2+((q[...,2]-.5)*2)**2)
        mat[radius<.72] = 5
        mat[(radius>=.72)&(radius<.86)] = 4
    return np.stack([mat,shade,np.zeros(shape,dtype=np.uint8)],axis=-1)


def paint_circuit(q, normal, material, style):
    """Apply the approved shell/coupling/grip finish to real weapon parts."""
    reuse = {'circuit_shroud':'rocket_shroud', 'circuit_receiver':'rocket_breech',
             'circuit_coupling':'rocket_coupling', 'circuit_grip':'rocket_grip',
             'circuit_heatsink':'rocket_heatsink'}
    if style in reuse:
        return paint_rocket(q,normal,material,reuse[style])
    x,y,z = q[...,0],q[...,1],q[...,2]
    mat = np.full(x.shape,material,dtype=np.uint8)
    shade = np.uint8(np.clip(193+55*np.sqrt(np.clip(z,0,1)),0,255))
    axis = int(np.argmax(abs(normal)))
    theta = np.arctan2(z-.5,y-.5)
    radial = np.sqrt(((y-.5)*2)**2+((z-.5)*2)**2)
    if style == 'circuit_stock':
        result = paint_rocket(q,normal,material,'rocket_breech')
        result[...,0][z<.30] = 5
        result[...,1][z<.30] = 190
        return result
    if style == 'circuit_pump':
        # Finger grooves are confined to the existing moving fore-end.
        mat[z<.28] = 5
        for centre in (.20,.35,.50,.65,.80):
            groove = (abs(x-centre)<.025)&(z<.78)
            mat[groove] = 3
            shade[groove] = 195
        mat[(x<.045)|(x>.955)] = 2
    elif style == 'circuit_feeddrum':
        # Magazine spindle and a protective rim; no painted target/number.
        if axis == 2:
            radius = np.sqrt(((x-.5)*2)**2+((y-.5)*2)**2)
            mat[radius>.94] = 3
            mat[(radius>.88)&(radius<=.94)] = 2
            mat[radius<.23] = 4
            mat[(abs(y-.5)<.025)&(abs(x-.5)<.08)] = 5
            angle = np.arctan2(y-.5,x-.5)
            ribs = (np.mod(angle*4/np.pi,1)<.045)&(radius>.40)&(radius<.82)
            mat[ribs] = 10
        else:
            mat[(z<.09)|(z>.91)] = 3
            mat[(z>.09)&(z<.14)] = 2
    elif style == 'circuit_chamber':
        # Revolver chamber: lengthwise recesses, ceramic end retainers.
        mat[(x<.055)|(x>.945)] = 3
        mat[(x>.055)&(x<.09)|(x>.91)&(x<.945)] = 2
        channel = (np.mod(theta*3/np.pi,1)<.08)&(x>.17)&(x<.83)
        mat[channel] = 10
        if axis == 0:
            mat[radial>.92] = 3
            mat[radial<.24] = 4
            mat[(radial<.13)&(abs(z-.5)<.025)] = 5
    elif style in ('circuit_tube','circuit_bore'):
        # Barrels and muzzle sleeves retain dark bores and machined lips.
        mat[(x<.065)|(x>.935)] = 3
        if style == 'circuit_tube':
            flute = (np.mod(theta*3/np.pi,1)<.06)&(x>.16)&(x<.84)
            mat[flute] = 3
        if axis == 0:
            mat[radial<.73] = 5
            mat[(radial>=.73)&(radial<.94)] = 4
    elif style == 'circuit_rail':
        mat[:] = 3
        mat[(y<.09)|(y>.91)] = 4
        mat[(x<.07)|(x>.93)] = 4
    elif style == 'circuit_lead':
        # Existing high-voltage leads have molded insulation ribs.
        mat[:] = 3
        ribs = np.mod(x*12,1)<.14
        shade[ribs] = 150
        mat[(x<.04)|(x>.96)] = 4
    elif style == 'circuit_insulator':
        mat[:] = 3
        shade[np.mod(x*6,1)<.15] = 155
        mat[(x<.055)|(x>.945)] = 4
    elif style == 'circuit_arm':
        mat[(x<.12)|(x>.88)] = 3
        mat[(x>.12)&(x<.15)|(x>.85)&(x<.88)] = 4
    elif style == 'circuit_tip':
        mat[x<.16] = 3
        mat[(x>.16)&(x<.20)] = 4
    elif style == 'circuit_capacitor':
        # Ceramic power block with retaining collars and cooling channels.
        mat[(x<.07)|(x>.93)] = 3
        groove = (np.mod(z*5,1)<.10)&(x>.16)&(x<.84)
        mat[groove] = 3
    return np.stack([mat,shade,np.zeros(x.shape,dtype=np.uint8)],axis=-1)


def paint_rocket(q, normal, material, style):
    """Rocket-specific surface design. No type, serials or decorative plaques.

    Shell seams follow the curved housing; end lips, ivory couplings and the
    separate heatsink follow real mesh parts. Details are expressed in the
    part's local coordinates, so they remain aligned through animation.
    """
    x,y,z = q[...,0],q[...,1],q[...,2]
    mat = np.full(x.shape, material, dtype=np.uint8)
    shade = np.uint8(np.clip(193 + 55*np.sqrt(np.clip(z,0,1)),0,255))
    axis = int(np.argmax(abs(normal)))
    radial = np.sqrt(((y-.5)*2)**2 + ((z-.5)*2)**2)
    if style in ('rocket_shroud','rocket_breech'):
        # Dark upper spine separates the two red cheek plates. Thin ivory
        # shoulders sit at their outside edges, not across the entire gun.
        top = z>.66
        spine = top & (abs(y-.5)<.105) & (x>.10) & (x<.93)
        mat[spine] = 3
        shoulder = top & ((y>.19)&(y<.245) | (y>.755)&(y<.81)) & (x>.12) & (x<.91)
        mat[shoulder] = 2
        seam = top & ((abs(y-.395)<.008) | (abs(y-.605)<.008)) & (x>.10)&(x<.93)
        mat[seam] = 10
        if style == 'rocket_shroud':
            # Four transverse cooling apertures within the dark spine.
            # Their steel leading lips give depth without noisy distressing.
            for centre in (.30,.43,.56,.69):
                slot = top & (abs(y-.5)<.075) & (abs(x-centre)<.024)
                lip = top & (abs(y-.5)<.077) & (x>centre+.024)&(x<centre+.032)
                mat[slot] = 5
                mat[lip] = 4
            # Existing front muzzle lip is machined steel; the bore stays dark.
            mat[x>.955] = 4
            if axis == 0:
                mat[radial<.76] = 5
                mat[(radial>=.76)&(radial<.93)] = 4
        else:
            # Rear shell terminates in an actual graphite end cap.
            mat[x<.045] = 3
        # A pair of recessed shell fasteners on each lateral cheek.
        if axis == 1:
            for cx in (.15,.86):
                bolt = ((x-cx)/.012)**2+((z-.43)/.032)**2
                mat[bolt<1] = 4
                mat[bolt<.25] = 5
    elif style == 'rocket_coupling':
        # Exposed ceramic sleeve between housings, with longitudinal flutes
        # and proper dark retaining collars at its physical ends.
        mat[(x<.075)|(x>.925)] = 3
        theta = np.arctan2(z-.5,y-.5)
        flute = (np.mod(theta*4/np.pi,1)<.07)&(x>.12)&(x<.88)
        mat[flute] = 3
        mat[(x>.075)&(x<.095)|(x>.905)&(x<.925)] = 4
    elif style == 'rocket_grip':
        # Molded rubber tread rather than bright cosmetic stripes.
        shade = np.uint8(np.clip(190+35*z,0,255))
        tread = (np.mod(z*9,1)<.16)&(z>.12)&(z<.84)
        shade[tread] = 145
        mat[z>.89] = 3
        mat[z<.07] = 3
    elif style == 'rocket_heatsink':
        # The existing side box becomes a recessed vent with a steel rim.
        u,v = (x,z) if axis != 2 else (x,y)
        mat[:] = 4
        inset = (u>.065)&(u<.935)&(v>.15)&(v<.85)
        mat[inset] = 3
        for centre in (.20,.35,.50,.65,.80):
            slot = (abs(u-centre)<.043)&(v>.28)&(v<.72)
            mat[slot] = 5
            mat[(abs(u-centre)<.043)&(v>.72)&(v<.745)] = 9
        mat[(v>.85)&(v<.88)] = 9
    return np.stack([mat,shade,np.zeros(x.shape,dtype=np.uint8)],axis=-1)


def raster(model, assignments):
    pos,uv,tris,_ = read_model(model)
    groups = components(pos,tris)
    if len(groups) != len(assignments):
        raise ValueError('model part layout changed: %s' % model)
    ao = occlusion(pos,tris,groups)
    # Sharp real mesh edges only: never draw a UV triangulation diagonal.
    edges = {}
    face_normals = []
    for ti,tri in enumerate(tris):
        p = pos[tri]
        n = np.cross(p[1]-p[0],p[2]-p[0])
        face_normals.append(n/max(np.linalg.norm(n),1e-9))
        for i,j in ((1,2),(2,0),(0,1)):
            key = tuple(sorted((tuple(np.round(p[i],3)),tuple(np.round(p[j],3)))))
            edges.setdefault(key,[]).append(ti)
    texture = np.zeros((SIZE,SIZE,3),dtype=np.uint8)
    valid = np.zeros((SIZE,SIZE),dtype=bool)
    part_index = {}
    for i,g in enumerate(groups):
        for vi in g:
            part_index[vi] = i
    for ti,tri in enumerate(tris):
        ci = part_index[tri[0]]
        material,style = assignments[ci]
        p = pos[tri];t = uv[tri]*SIZE
        a,b,c = t
        den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-7:
            continue
        x0,y0 = np.maximum(0,np.floor(t.min(0)).astype(int))
        x1,y1 = np.minimum(SIZE-1,np.ceil(t.max(0)).astype(int))
        yy,xx = np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
        w0 = ((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        w1 = ((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        w2 = 1-w0-w1
        inside = (w0>=-1e-5)&(w1>=-1e-5)&(w2>=-1e-5)
        pts = w0[...,None]*p[0]+w1[...,None]*p[1]+w2[...,None]*p[2]
        n = np.cross(p[1]-p[0],p[2]-p[0]);n/=max(np.linalg.norm(n),1e-8)
        g = groups[ci]
        pixel = paint(pts,n,(pos[g].min(0),pos[g].max(0)),material,style)
        if style.startswith(('rocket_', 'circuit_')) and material in (1,2,4):
            for k,(i,j) in enumerate(((1,2),(2,0),(0,1))):
                key = tuple(sorted((tuple(np.round(p[i],3)),tuple(np.round(p[j],3)))))
                neighbours = edges[key]
                sharp = len(neighbours)==1 or any(np.dot(face_normals[ti],face_normals[other])<.90 for other in neighbours)
                if not sharp:
                    continue
                edge_len = np.linalg.norm(p[j]-p[i])
                altitude = np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))/max(edge_len,1e-9)
                distance = (w0,w1,w2)[k]*altitude
                painted = (pixel[...,0]==1)|(pixel[...,0]==2)
                bevel = (distance<.08)&painted
                pixel[...,1][bevel] = 255
                # A short, fine paint rub at a real hard corner, under 1%
                # of surface area. No whole-surface random grain.
                along = (w0,w1,w2)[i]/np.maximum((w0,w1,w2)[i]+(w0,w1,w2)[j],1e-8)
                chip = (distance<.025)&(along>.73)&(along<.78)&(pixel[...,0]==1)
                pixel[...,0][chip] = 4
                pixel[...,1][chip] = 210
        ambient = w0*ao[tri[0]]+w1*ao[tri[1]]+w2*ao[tri[2]]
        pixel[...,1] = np.uint8(np.clip(pixel[...,1]*ambient,0,255))
        texture[y0:y1+1,x0:x1+1][inside] = pixel[inside]
        valid[y0:y1+1,x0:x1+1][inside] = True
    # Fill 12-texel gutters out from the authored islands for filtering/mips.
    for _ in range(12):
        old = valid.copy()
        for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
            shifted = np.roll(old,(dy,dx),(0,1))
            if dy:
                shifted[0 if dy>0 else -1,:] = False
            if dx:
                shifted[:,0 if dx>0 else -1] = False
            fill = shifted & ~valid
            texture[fill] = np.roll(texture,(dy,dx),(0,1))[fill]
            valid[fill] = True
    return texture,groups,uv


def match_world(world, view_groups, view_uv, view_assignments):
    p,uv,tris,_ = read_model(world)
    groups = components(p,tris)
    vsets = [{tuple(np.round(v,5)) for v in view_uv[g]} for g in view_groups]
    assignments = []
    for g in groups:
        gs = {tuple(np.round(v,5)) for v in uv[g]}
        scores = [len(gs&s)/max(len(gs|s),1) for s in vsets]
        nearest = int(np.argmax(scores))
        mat,style = view_assignments[nearest]
        # World model has no firing planes. Unmatched caps stay dark steel.
        if mat == 7:
            mat,style = 4,'bore'
        assignments.append((mat,style))
    return assignments


def flash(texture,name):
    if name not in FLASH_RECTS:
        return
    source_names = {'shotgun':'shot','machinegun':'nail','rocketlauncher':'rock2','lightning':'light','railgun':'nail2'}
    src = np.asarray(Image.open(OUT.parent/'librequake/lq1/progs/src/textures'/('v_'+source_names[name]+'.mdl.0.png')).convert('RGB'))
    x0,y0,x1,y1 = FLASH_RECTS[name]
    y,x = np.mgrid[int(y0*SIZE/200):int(y1*SIZE/200),int(x0*SIZE/200):int(x1*SIZE/200)]
    rgb = src[np.clip(y*200//SIZE,0,199),np.clip(x*200//SIZE,0,199)]
    value = rgb.max(2)
    # Keep the source's flash silhouette solely in this explicit effect UV.
    texture[y,x,0] = 7
    texture[y,x,1] = value
    texture[y,x,2] = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weapon', choices=tuple(LAYOUTS), help='Re-author only one weapon for design review')
    args = parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    manifest_path = OUT/'layouts.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name,layout in LAYOUTS.items():
        if args.weapon and name != args.weapon:
            continue
        vpath = ROOT/'content/models'/('v_'+name+'.md3')
        texture,groups,uv = raster(vpath,layout)
        flash(texture,name)
        png(OUT/('v_'+name+'.png'),SIZE,SIZE,[r.flatten().tolist() for r in texture])
        gpath = ROOT/'content/models'/('g_'+name+'.iqm')
        glayout = match_world(gpath,groups,uv,layout)
        gt,_,_ = raster(gpath,glayout)
        png(OUT/('g_'+name+'.png'),SIZE,SIZE,[r.flatten().tolist() for r in gt])
        manifest[name] = {'view_parts':layout,'world_parts':glayout}
        print('authored',name,flush=True)
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    main()
