#!/usr/bin/env python3
"""Generate RAVAGE's placeholder sounds.

Writes 16-bit mono WAV files into content/sound for the sounds LibreQuake
has no equivalent for: the out-of-ammo click and the jump pad. They are
synthesised here from noise and sine generators, so they contain no
recorded or third-party audio. The rest come from LibreQuake; see
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


def noammo():
    click = burst(8, 0.03, 120, 0.8)
    return mix(click, delay(click, 0.08))


def jumppad():
    return [v * 0.6 * decay(t, 6) for t, v in sweep(180, 620, 0.35)]


SOUNDS = {
    'weapons/noammo.wav': noammo,
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
