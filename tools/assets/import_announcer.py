#!/usr/bin/env python3
"""Convert the announcer's voice lines into game sounds.

The announcer lines were generated with ElevenLabs text to speech (voice
YOq2y2Up4RgXP2HyXjE5, model eleven_v4). Download each take as MP3, name it
after its line below, and run:

  import_announcer.py <mp3-dir> [content-dir]

Each take is cut from its start offset (a few takes open with a breath
before the word), trimmed of silence at both ends, normalised and written
to content/sound/announcer as 22050 Hz mono 16-bit WAV. Needs ffmpeg.
"""

import os
import subprocess
import sys

LINES = {
    # sound: (text spoken, start offset in seconds)
    'getready': ('Get ready!', 0),
    'three': ('Three.', 1.25),
    'two': ('Two.', 0),
    'one': ('One.', 0),
    'fight': ('Fight!', 0),
}

TRIM = 'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02'
FILTER = ','.join([TRIM, 'areverse', TRIM, 'areverse', 'afade=t=in:d=0.01', 'loudnorm=I=-14:TP=-1.5'])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    content = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'sound', 'announcer')
    os.makedirs(out, exist_ok=True)
    for name, (_, start) in LINES.items():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-i', os.path.join(src, name + '.mp3'),
                        '-af', FILTER, '-ar', '22050', '-ac', '1',
                        '-c:a', 'pcm_s16le', '-map_metadata', '-1', '-fflags', '+bitexact', '-flags:a', '+bitexact',
                        os.path.join(out, name + '.wav')], check=True)
    print('wrote', len(LINES), 'announcer lines to', os.path.normpath(out))


if __name__ == '__main__':
    main()
