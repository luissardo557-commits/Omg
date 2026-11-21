# Música de tensión (sintetizada, libre de derechos) para la Parte 4 - 65 s
import numpy as np, wave, sys

SR = 44100; DUR = 65.0
t = np.arange(int(SR * DUR)) / SR
rng = np.random.default_rng(4)
out = np.zeros_like(t)

def env(t, a, b, fade=1.0):
    return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

def lowpass(x, alpha):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc); y[i] = acc
    return y

# dron grave (La1 + Mi2) con respiración lenta
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
drone = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.41 * t) + 0.3 * np.sin(2 * np.pi * 110.3 * t)) * lfo
tension = 1 + 0.6 * env(t, 40, 55.2, 2.0)
out += 0.16 * drone * tension * env(t, 0, 64.6, 0.4)

# brillo agudo misterioso (cluster disonante suave)
shim = sum(np.sin(2 * np.pi * f * t + p) for f, p in [(659.3, 0), (698.5, 1), (987.8, 2)])
out += 0.012 * shim * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t)) * env(t, 3, 64.5, 3)

# viento (ruido filtrado)
noise = rng.standard_normal(len(t))
wind = lowpass(noise, 0.02)
out += 0.25 * wind * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)) * env(t, 0, 64.8, 1.5)

# latido: más rápido en la tensión
def thump(at, amp=1.0):
    n = int(0.35 * SR); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * (60 - 25 * tt / 0.35) * tt) * np.exp(-tt * 14)
    i = int(at * SR); j = min(len(out), i + n)
    out[i:j] += amp * s[:j - i]

x = 15.0
while x < 54.8:
    period = 1.05 if x < 40 else 0.72 - 0.2 * (x - 40) / 15
    a = 0.35 if x < 40 else 0.55
    thump(x, a); thump(x + 0.22, a * 0.6)
    x += period

# golpes graves en los momentos clave
def boom(at, amp=0.9):
    n = int(2.2 * SR); tt = np.arange(n) / SR
    s = (np.sin(2 * np.pi * (48 - 18 * tt) * tt) * np.exp(-tt * 2.2)
         + 0.4 * lowpass(rng.standard_normal(n), 0.05) * np.exp(-tt * 6))
    i = int(at * SR); j = min(len(out), i + n)
    out[i:j] += amp * s[:j - i]

for b in (0.05, 15.0, 40.0, 55.0):
    boom(b)

# whooshes en cada cambio de clip
def whoosh(center, amp=0.5, dur=0.7):
    n = int(dur * SR); tt = np.arange(n) / SR
    e = np.sin(np.pi * tt / dur) ** 2
    s = lowpass(rng.standard_normal(n), 0.12) * e
    i = int((center - dur / 2) * SR); i = max(0, i); j = min(len(out), i + n)
    out[i:j] += amp * s[:j - i]

for c in (4.0, 27.0):
    whoosh(c)

# subida (riser) antes del bucle final
r = (t > 51.5) & (t < 55.0)
k = np.clip((t - 51.5) / 3.5, 0, 1)
out += r * 0.18 * k ** 2 * np.sin(2 * np.pi * (200 + 600 * k ** 2) * t)
out += r * 0.25 * k ** 2 * lowpass(rng.standard_normal(len(t)), 0.3)

# normalizar a -3 dBFS, estéreo
out = out / np.max(np.abs(out)) * 0.7
st = np.stack([out, np.roll(out, 300)], axis=1)
pcm = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
