#!/usr/bin/env python3
"""Generate RAVAGE's placeholder sounds.

Writes 16-bit mono WAV files into content/sound: weapon fire, explosions,
pain, death and jump pads. Every sound is synthesised here from sine, saw
and noise generators, so they contain no recorded or third-party audio.
They are placeholders until real sound design replaces them. Pickup,
grenade and teleporter sounds come from LibreQuake instead; see
import_librequake_sounds.py.

Usage: make_sounds.py [content-dir]    (default: the repository's content/)

Only the Python standard library is used. The output is deterministic, so
running the script again without changes gives byte-identical files.
"""

import math
import os
import struct
import sys

RATE = 22050


class Noise:
    """Deterministic white noise in [-1, 1]."""

    def __init__(self, seed):
        self.state = seed

    def __call__(self):
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state / 0x3FFFFFFF - 1


def samples(seconds):
    return range(int(seconds * RATE))


def decay(t, rate):
    return math.exp(-t * rate)


def lowpass(signal, amount):
    """One-pole low-pass filter. amount 0..1, smaller is darker."""
    out, y = [], 0.0
    for x in signal:
        y += amount * (x - y)
        out.append(y)
    return out


def sweep(f0, f1, seconds, wave=math.sin):
    """A tone gliding from f0 to f1 Hz. Yields (t, value)."""
    phase = 0.0
    n = int(seconds * RATE)
    for i in range(n):
        t = i / RATE
        phase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / RATE
        yield t, wave(phase)


def saw(phase):
    return (phase / math.pi) % 2 - 1


def square(phase):
    return 1.0 if math.sin(phase) >= 0 else -1.0


def mix(*signals):
    n = max(len(s) for s in signals)
    return [sum(s[i] for s in signals if i < len(s)) for i in range(n)]


def delay(signal, seconds):
    return [0.0] * int(seconds * RATE) + signal


def burst(seed, seconds, rate, tone=1.0):
    noise = Noise(seed)
    return lowpass([noise() * decay(i / RATE, rate) for i in samples(seconds)], tone)


#
# The sounds
#

def shotgun():
    thump = [math.sin(2 * math.pi * 58 * t) * decay(t, 14) for t in (i / RATE for i in samples(0.35))]
    return mix(burst(1, 0.35, 11, 0.5), thump)


def machinegun():
    tone = [square(2 * math.pi * 170 * t) * 0.3 * decay(t, 50) for t in (i / RATE for i in samples(0.1))]
    return mix(burst(2, 0.1, 40, 0.6), tone)


def rocketlauncher():
    noise = Noise(3)
    whoosh = lowpass([noise() * math.sin(math.pi * min(1, i / RATE / 0.5)) * decay(i / RATE, 3)
                      for i in samples(0.6)], 0.15)
    boom = [v * decay(t, 9) * 0.6 for t, v in sweep(110, 50, 0.4)]
    return mix([x * 2.5 for x in whoosh], boom)


def lightning():
    # A 110 Hz buzz with noise crackling in short bursts.
    noise = Noise(5)
    buzz = []
    for i in samples(0.25):
        crackle = 0.3 if (i // 180) % 3 == 0 else 0.06
        buzz.append(saw(2 * math.pi * 110 * i / RATE) * 0.5 + noise() * crackle)
    return lowpass(buzz, 0.5)


def railgun():
    ring = [v * 0.5 * decay(t, 3) for t, v in sweep(300, 1800, 0.7)]
    metal = [math.sin(2 * math.pi * 2400 * t) * 0.15 * decay(t, 6) for t in (i / RATE for i in samples(0.7))]
    return mix(ring, metal, burst(6, 0.2, 20, 0.7))


def explode():
    rumble = [v * decay(t, 4) * 0.8 for t, v in sweep(70, 30, 1.0)]
    return mix([x * 1.6 for x in burst(7, 1.0, 4, 0.12)], rumble)


def noammo():
    click = burst(8, 0.03, 120, 0.8)
    return mix(click, delay(click, 0.08))


def pain():
    return lowpass([saw(2 * math.pi * (140 + 15 * math.sin(2 * math.pi * 9 * t)) * t)
                    * 0.6 * decay(t, 7) for t in (i / RATE for i in samples(0.25))], 0.3)


def death():
    return lowpass([v * 0.7 * decay(t, 2.5) for t, v in sweep(220, 55, 0.8, saw)], 0.3)


def jumppad():
    return [v * 0.6 * decay(t, 6) for t, v in sweep(180, 620, 0.35)]


SOUNDS = {
    'weapons/shotgun.wav': shotgun,
    'weapons/machinegun.wav': machinegun,
    'weapons/rocketlauncher.wav': rocketlauncher,
    'weapons/lightning.wav': lightning,
    'weapons/railgun.wav': railgun,
    'weapons/explode.wav': explode,
    'weapons/noammo.wav': noammo,
    'player/pain.wav': pain,
    'player/death.wav': death,
    'misc/jumppad.wav': jumppad,
}


def write_wav(path, signal):
    # Normalise to a common loudness, then fade the last few milliseconds
    # so no sound ends with a click.
    peak = max(abs(x) for x in signal) or 1
    fade = int(0.005 * RATE)
    pcm = bytearray()
    for i, x in enumerate(signal):
        gain = min(1, (len(signal) - i) / fade)
        pcm += struct.pack('<h', round(x / peak * 0.8 * gain * 32767))
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(pcm), b'WAVE', b'fmt ', 16,
                         1, 1, RATE, RATE * 2, 2, 16, b'data', len(pcm))
    with open(path, 'wb') as f:
        f.write(header + pcm)


def main():
    content = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', 'content')
    out = os.path.join(content, 'sound')
    for name, build in SOUNDS.items():
        path = os.path.join(out, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_wav(path, build())
    print('wrote', len(SOUNDS), 'sounds to', os.path.normpath(out))


if __name__ == '__main__':
    main()
