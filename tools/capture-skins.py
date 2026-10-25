#!/usr/bin/env python3
"""Capture Bone Circuit in RAVAGE's real renderer using isolated game data.

Needs a built client, fteqcc, and compiled game data (including duel_graybox).
Only the staged capture VM adds display mannequins and grants weapons. The
repository's gameplay code and compiled game data are never modified.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
WEAPONS = ('shotgun', 'machinegun', 'rocketlauncher', 'grenadelauncher', 'lightning', 'railgun')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, default=ROOT/'build/bin/ravage')
    parser.add_argument('--qcc', type=Path, default=ROOT/'build/bin/fteqcc')
    parser.add_argument('--game-data', type=Path, default=ROOT/'build/game')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/art/bone-circuit/ingame')
    parser.add_argument('--ffmpeg', type=Path, help='Optional ffmpeg executable for the 32-second MP4')
    parser.add_argument('--weapons-only', action='store_true', help='Inspect all six idle/firing viewmodels in 22 seconds')
    parser.add_argument('--weapon', choices=WEAPONS, help='Review one weapon in its held pose and a staged engine close-up')
    parser.add_argument('--world-weapons-only', action='store_true', help='Capture a side-on lineup of all six world pickups')
    args = parser.parse_args()
    work = ROOT/'build/skin-capture'
    base = work/'game/base'
    work.mkdir(parents=True, exist_ok=True)
    if base.exists():
        shutil.rmtree(base)
    shutil.copytree(args.game_data.resolve()/'base', base)
    # Replace the entire model directory: removed old luma maps must not linger.
    shutil.rmtree(base/'models')
    shutil.copytree(ROOT/'content/models', base/'models')
    source = work/'code'
    for side in ('ssqc', 'csqc', 'shared'):
        shutil.copytree(ROOT/'game'/side, source/side, dirs_exist_ok=True)
    shutil.copyfile(ROOT/'tools/assets/skin_capture.qc', source/'ssqc/skin_capture.qc')
    p = source/'ssqc/defs.qc'
    p.write_text(p.read_text()+'\nvoid() Skin_CaptureFrame;\n')
    p = source/'ssqc/progs.src'
    p.write_text(p.read_text()+'\nskin_capture.qc\n')
    p = source/'ssqc/world.qc'
    p.write_text(p.read_text().replace('MatchTest_Frame();', 'MatchTest_Frame();\n\tSkin_CaptureFrame();'))
    p = source/'csqc/view.qc'
    p.write_text(p.read_text().replace('\tView_AddWeapon();', '\tif (!cvar("rv_skin_hideweapon"))\n\t\tView_AddWeapon();'))
    p = source/'csqc/main.qc'
    p.write_text(p.read_text().replace('\tHud_Draw([vwidth, vheight]);', '\tif (!cvar("rv_skin_hidehud"))\n\t\tHud_Draw([vwidth, vheight]);'))
    with (work/'compile.log').open('w') as log:
        for side, name in (('ssqc', 'qwprogs'), ('csqc', 'csprogs')):
            subprocess.run([str(args.qcc.resolve()), '-src', str(source/side), '-o', str(base/(name+'.dat'))],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    scenes = {
        'player': (1, '0 -300 24 6 90 0', 58),
        'health': (2, '0 -360 52 14 90 0', 60),
        'armour': (3, '0 -360 38 10 90 0', 60),
        'ammo': (4, '0 -460 45 9 90 0', 60),
        'world-weapons': (5, '0 -460 45 7 90 0', 60),
        'first-person': (0, '0 -300 24 0 90 0', 90),
        'weapon-close': (6, '35 -300 24 8 109 0', 45),
    }
    for name, (scene, pos, fov) in scenes.items():
        hide = 0 if name == 'first-person' else 1
        (base/('scene-'+name+'.cfg')).write_text(
            f'set rv_skin_scene {scene}\nset rv_skin_turn 0\nsetpos {pos}\nfov {fov}\n'
            f'set rv_skin_hideweapon {hide}\nset rv_skin_hidehud {hide}\n')
    cfg = ['con_notifytime 0', 'con_notifylines 0', 'crosshair 0', 'map duel_graybox', 'in 3 exec scene-player.cfg',
           'in 5 screenshot skin-capture/player.png']
    if args.ffmpeg:
        # Engine screenshot frames avoid the native raw-capture crash on
        # macOS Retina displays. These are real rendered frames, not tweens.
        cfg += [f'in {6+i/15:.6f} screenshot skin-capture/video/frame-{i:08d}.tga'
                for i in range(32*15)]
    cfg += ['in 6 set rv_skin_turn 1']
    for time, scene in ((10,'health'), (14,'armour'), (18,'ammo'), (22,'world-weapons')):
        cfg += [f'in {time} exec scene-{scene}.cfg',
                f'in {time+2} screenshot skin-capture/{scene}.png', f'in {time+2.2} set rv_skin_turn 1']
    cfg += ['in 26 exec scene-first-person.cfg']
    for i, name in enumerate(WEAPONS):
        cfg += [f'in {26+i*2+.2} impulse {i+1}', f'in {27+i*2} screenshot skin-capture/{name}.png']
    cfg += ['in 39 quit']
    names = ('player','health','armour','ammo','world-weapons',*WEAPONS)
    video_name = 'bone-circuit-ingame.mp4'
    if args.weapons_only:
        cfg = ['con_notifytime 0', 'con_notifylines 0', 'crosshair 0', 'map duel_graybox',
               'in 3 exec scene-player.cfg', 'in 3.2 exec scene-first-person.cfg', 'in 3.5 god']
        for i, name in enumerate(WEAPONS):
            start = 4+i*3
            cfg += [f'in {start} impulse {i+1}',
                    f'in {start+.6} screenshot skin-capture/{name}.png',
                    f'in {start+1} +attack',
                    f'in {start+1.20} screenshot skin-capture/{name}-fire.png',
                    f'in {start+1.30} -attack']
        if args.ffmpeg:
            cfg += [f'in {4+i/15:.6f} screenshot skin-capture/video/frame-{i:08d}.tga'
                    for i in range(18*15)]
        cfg += ['in 22 quit']
        names = (*WEAPONS, *(name+'-fire' for name in WEAPONS))
        video_name = 'weapons-ingame.mp4'
    if args.weapon:
        name = args.weapon
        index = WEAPONS.index(name)+1
        cfg = ['con_notifytime 0', 'con_notifylines 0', 'crosshair 0',
               f'set rv_skin_weapon {index}', 'map duel_graybox',
               'in 3 exec scene-player.cfg', 'in 3.2 exec scene-first-person.cfg',
               'in 3.5 god', f'in 4 impulse {index}',
               f'in 5 screenshot skin-capture/{name}.png',
               'in 6 +attack', f'in 6.20 screenshot skin-capture/{name}-fire.png',
               'in 6.30 -attack', 'in 9 exec scene-weapon-close.cfg',
               f'in 10 screenshot skin-capture/{name}-close.png',
               'in 11 set rv_skin_turn 1',
               f'in 13 screenshot skin-capture/{name}-angle.png']
        if args.ffmpeg:
            cfg += [f'in {5+i/15:.6f} screenshot skin-capture/video/frame-{i:08d}.tga'
                    for i in range(9*15)]
        cfg += ['in 15 quit']
        names = (name, name+'-fire', name+'-close', name+'-angle')
        video_name = name+'-review.mp4'
    if args.world_weapons_only:
        cfg = ['con_notifytime 0', 'con_notifylines 0', 'crosshair 0', 'map duel_graybox',
               'in 3 exec scene-world-weapons.cfg',
               'in 5 screenshot skin-capture/world-weapons.png', 'in 7 quit']
        names = ('world-weapons',)
        if args.ffmpeg:
            parser.error('--world-weapons-only captures a still; omit --ffmpeg')
    (base/'capture.cfg').write_text('\n'.join(cfg)+'\n')
    command = [str(args.client.resolve()), '-basedir', str(base.parent), '-nohome', '-window',
               '+set','vid_fullscreen','0','+set','vid_width','960','+set','vid_height','540',
               '+set','vid_renderer','gl','+set','s_device','none','+set','sys_colorconsole','0',
               '+set','sv_cheats','1','+set','cl_maxfps','60','+set','cl_idlefps','60',
               '+exec','capture.cfg']
    with (work/'client.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=100)
    args.output.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copyfile(base/'skin-capture'/(name+'.png'), args.output/(name+'.png'))
    shutil.copyfile(work/'client.log', args.output/'capture.log')
    if args.ffmpeg:
        subprocess.run([str(args.ffmpeg.resolve()), '-y', '-framerate', '15', '-i',
                        str(base/'skin-capture/video/frame-%08d.tga'), '-c:v', 'libx264',
                        '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        str(args.output/video_name)], check=True)
    print('Captured actual RAVAGE frames in', args.output)


if __name__ == '__main__':
    main()
