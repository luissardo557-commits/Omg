# Música + efectos (sintetizados, sin derechos) y pista de narración del Episodio 1.
# Uso: python3 ep1_audio.py <carpeta_voz> <salida_musica_sfx.wav> <salida_voz.wav>
import sys, json, os, wave, numpy as np
import soundfile as sf
from ep1_timeline import T, NARR

SR = 44100; DUR = T['fin']; N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1)
mus = np.zeros(N); sfx = np.zeros(N)

def onepole(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y

def win(a, b, fade=0.3):
    return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

def add(buf, at, sig, amp=1.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if i < N: buf[i:j] += amp * sig[:j - i]

def tone(f, d, kind='sine', dec=4.0, att=0.005):
    n = int(d * SR); tt = np.arange(n) / SR
    ph = 2 * np.pi * f * tt
    if kind == 'sine': s = np.sin(ph)
    elif kind == 'saw': s = 2 * ((f * tt) % 1) - 1
    elif kind == 'square': s = np.sign(np.sin(ph))
    else: s = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)
    env = np.minimum(1, tt / att) * np.exp(-tt * dec)
    return s * env

def noise(d, a=0.2, dec=6.0):
    n = int(d * SR); tt = np.arange(n) / SR
    return onepole(rng.standard_normal(n), a) * np.exp(-tt * dec)

def boom(d=2.0, f0=55, amp=1.0):
    n = int(d * SR); tt = np.arange(n) / SR
    return amp * (np.sin(2 * np.pi * (f0 - 20 * tt / d) * tt) * np.exp(-tt * 2.5) + 0.5 * onepole(rng.standard_normal(n), 0.04) * np.exp(-tt * 4))

def note(m): return 440 * 2 ** ((m - 69) / 12)

# ---------------- ruido de fondo continuo (olas / viento) que se usa en varias escenas
base_noise = onepole(rng.standard_normal(N), 0.015)
surf = base_noise * (0.6 + 0.4 * np.sin(2 * np.pi * 0.18 * t) ** 2)
wind = onepole(rng.standard_normal(N), 0.05) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t))

# 0 - 6.8 épica: tambores + acordes graves
s1, s2 = T['s1'], T['s2']
sfx += 2.2 * surf * win(0, s2, 0.5)
for k, x in enumerate(np.arange(0.0, s2 - 0.2, 0.5)):
    add(mus, x, boom(0.5, 60, 1.0 if k % 4 == 0 else 0.5), 0.55)
for x, ch in [(0.0, [38, 45, 50]), (1.6, [34, 41, 46]), (3.2, [36, 43, 48]), (4.7, [38, 45, 50, 53])]:
    for m in ch: add(mus, x, tone(note(m), 1.8, 'saw', dec=1.2, att=0.05), 0.06)
add(sfx, 1.0, boom(2.5, 40), 0.8)            # trueno
add(sfx, 4.65, noise(2.5, 0.08, 1.2), 2.0)   # ola gigante
add(sfx, 4.75, boom(2.5, 38), 1.0)
add(sfx, 4.75, boom(1.5, 70), 0.5)

# 6.8 - 14.6 misterio: pad + celesta
pad = sum(np.sin(2 * np.pi * note(m) * t + i) for i, m in enumerate([50, 57, 60, 64]))
mus += 0.05 * onepole(pad, 0.2) * win(s2, T['s3a'], 0.6)
for k, x in enumerate(np.arange(s2 + 0.2, T['s3a'] - 0.3, 0.45)):
    m = [74, 77, 81, 76, 72, 77, 79, 74][k % 8]
    add(mus, x, tone(note(m), 1.2, 'bell', dec=3.0), 0.07)
for code_t in (7.0, 7.89, 8.33, 8.77, 9.38):    # 'pop' cuando se presenta cada país
    n = int(0.15 * SR); tt = np.arange(n) / SR
    add(sfx, code_t - 0.05, np.sin(2 * np.pi * (500 + 1500 * tt / 0.15) * tt) * np.exp(-tt * 25), 0.35)
sfx += 1.2 * surf * win(s2, T['s3a'], 0.6) * 0.6
add(sfx, T['isla'], boom(2.5, 45), 0.6)

# 14.6 - 19.4 barco: cuerdas tensas, olas, madera
a, b = T['s3a'], T['s3b']
for k, x in enumerate(np.arange(a, b - 0.1, 60 / 150 / 2)):
    m = [38, 38, 41, 38, 43, 38, 41, 40][k % 8]
    add(mus, x, tone(note(m), 0.25, 'saw', dec=10), 0.12)
sfx += (2.5 * surf + 1.5 * wind) * win(a, b, 0.3)
for x in (a + 0.3, a + 1.9, a + 3.0, a + 4.1):
    add(sfx, x, noise(1.4, 0.1, 2.5), 1.6)        # golpes de ola
for x in (a + 0.8, a + 2.3, a + 3.6):            # crujido de madera
    n = int(0.6 * SR); tt = np.arange(n) / SR
    add(sfx, x, np.sin(2 * np.pi * (90 + 40 * np.sin(tt * 30)) * tt) * np.exp(-tt * 4) * (1 + 0.5 * np.sign(np.sin(tt * 160))), 0.18)
add(sfx, a + 1.2, boom(2.0, 42), 0.7)
for x in np.arange(a + 1.5, a + 3.0, 0.18):        # Canadá rodando
    add(sfx, x, noise(0.08, 0.3, 30), 0.6)
add(sfx, a + 3.0, boom(2.0, 36), 1.0)

# 19.4 - 24.0 avión: turbulencia, relámpagos, alarma
a, b = T['s3b'], T['s3c']
rumble = onepole(rng.standard_normal(N), 0.01) * (1 + 0.6 * np.sin(2 * np.pi * 7 * t))
sfx += 3.0 * rumble * win(a, b, 0.2)
for x in np.arange(a, b - 0.3, 60 / 150):
    add(mus, x, tone(note(38), 0.35, 'saw', dec=6), 0.1)
for f in (0.45, 1.3, 1.75):
    add(sfx, a + f, noise(0.25, 0.9, 15), 1.2)    # chasquido del rayo
    add(sfx, a + f + 0.05, boom(2.2, 38), 0.9)
for x in np.arange(T['cabina'] + 0.7, b, 1 / 3):  # pitido de alarma
    add(sfx, x, tone(880, 0.17, 'square', dec=2) * 0.5, 0.12)

# 24.0 - 28.6 bajo el agua
a, b = T['s3c'], T['s4']
under = onepole(rng.standard_normal(N), 0.004)
sfx += 4.0 * under * win(a, b, 0.4)
mus += 0.09 * np.sin(2 * np.pi * 41.2 * t) * win(a, b, 0.6) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.5 * t))
for x in np.arange(a + 0.1, b - 0.3, 0.23):
    n = int(0.07 * SR); tt = np.arange(n) / SR; f0 = rng.uniform(500, 1100)
    add(sfx, x + rng.uniform(0, 0.1), np.sin(2 * np.pi * (f0 + 2500 * tt) * tt) * np.exp(-tt * 40), 0.22)
add(sfx, a + 1.6, boom(3.0, 32), 0.9)
n = int(2.5 * SR); tt = np.arange(n) / SR
add(sfx, a + 2.2, np.sin(2 * np.pi * (70 - 20 * tt) * tt) * np.sin(np.pi * tt / 2.5), 0.4)

# 28.6 - 40.4 discusión: pizzicato cómico + efectos
a, b = T['s4'], T['s5']
melody = [67, 71, 74, 71, 72, 69, 67, 66, 67, 71, 74, 76, 74, 72, 71, 69]
bass = [43, 38, 43, 38, 45, 40, 43, 38]
beat = 60 / 132
for k, x in enumerate(np.arange(a, 36.1, beat / 2)):
    add(mus, x, tone(note(melody[k % 16]), 0.3, 'sine', dec=14), 0.14)
    if k % 2 == 0: add(mus, x, tone(note(bass[(k // 2) % 8]), 0.35, 'square', dec=9), 0.05)
sfx += 0.9 * surf * win(a, b, 0.5)
for x in (28.7, 29.0, 29.25, 29.9, 30.1, 30.35):   # saltitos
    n = int(0.12 * SR); tt = np.arange(n) / SR
    add(sfx, x, np.sin(2 * np.pi * (300 + 900 * tt / 0.12) * tt) * np.exp(-tt * 20), 0.2)
n = int(0.5 * SR); tt = np.arange(n) / SR
add(sfx, 31.0, np.sin(2 * np.pi * (220 + 120 * np.sin(tt * 40)) * tt) * np.exp(-tt * 5), 0.25)   # boing de EE. UU.
add(sfx, 32.3, noise(0.4, 0.5, 8), 0.4)                                                          # grito de Argentina
add(sfx, 33.6, tone(note(62), 0.6, 'bell', dec=3), 0.15); add(sfx, 33.75, tone(note(65), 0.6, 'bell', dec=3), 0.15)
for x in np.arange(35.2, 36.2, 0.07):                                                            # temblor de Canadá
    add(sfx, x, tone(180, 0.05, 'sine', dec=40), 0.07)
mus += 0.06 * onepole(pad, 0.2) * win(36.2, b, 0.4)
add(sfx, 38.6, boom(3.0, 30), 1.1)                                                               # sonido grave del océano

# 40.4 - 55.0 suspenso creciente + golpe final
a, b = T['s5'], T['negro']
k = np.clip((t - a) / (b - a), 0, 1)
drone = (np.sin(2 * np.pi * 36.7 * t) + 0.6 * np.sin(2 * np.pi * 55 * t) + 0.25 * np.sin(2 * np.pi * 77.8 * t))
mus += 0.14 * drone * win(a, b, 0.6) * (0.5 + 0.8 * k)
x = a + 0.3
while x < b - 0.2:
    p = 1.0 - 0.55 * (x - a) / (b - a)
    add(mus, x, boom(0.35, 55, 1.0), 0.45); add(mus, x + 0.22, boom(0.3, 55, 0.6), 0.3)
    x += p
r = (t > b - 4.0) & (t < b)
kk = np.clip((t - (b - 4.0)) / 4.0, 0, 1)
mus += r * 0.12 * kk ** 2 * np.sin(2 * np.pi * (180 + 700 * kk ** 2) * t)
sfx += r * 0.9 * kk ** 2 * onepole(rng.standard_normal(N), 0.25)
sfx += 2.5 * under * win(43.0, 47.5, 0.5)
add(sfx, 43.4, boom(3.0, 30), 0.8)
for i, x in enumerate((47.1, 47.9, 48.8)):                      # iconos de rutas
    add(sfx, x, tone(note(76 + i * 3), 0.4, 'bell', dec=6), 0.25)
add(sfx, 47.7, noise(0.15, 0.6, 25), 0.4)                       # gafas cayendo
add(sfx, b, boom(3.5, 34), 1.6)                                 # GOLPE + corte a negro
add(sfx, b, boom(2.0, 80), 0.6)
add(sfx, b + 0.12, noise(0.6, 0.4, 5), 0.6)

# cierre: fanfarria corta
a = T['final']
for i, (x, m) in enumerate([(a, 62), (a + 0.18, 66), (a + 0.36, 69), (a + 0.6, 74)]):
    for d in (0, 7): add(mus, x, tone(note(m - 12 + d), 1.2 if i == 3 else 0.4, 'saw', dec=2.5 if i == 3 else 6, att=0.01), 0.07)
add(mus, a, boom(1.0, 60), 0.6)
for x in np.arange(a + 0.6, DUR - 0.2, 0.25):
    add(mus, x, tone(note([74, 78, 81, 78][int((x - a) * 4) % 4]), 0.25, 'bell', dec=8), 0.06)

out = mus * 1.0 + sfx * 0.55
out *= np.clip((DUR - t) / 0.4, 0, 1)
out = out / np.max(np.abs(out)) * 0.85
sf.write(sys.argv[2], np.stack([out, np.roll(out, 250)], 1).astype(np.float32), SR)

# pista de narración
vd = sys.argv[1]; lines = json.load(open(os.path.join(vd, 'lines.json')))
voz = np.zeros(N)
for blk, i, start in NARR:
    a, sr = sf.read(os.path.join(vd, lines[blk][i]['file']))
    if sr != SR:
        idx = np.arange(int(len(a) * SR / sr)) * sr / SR
        a = np.interp(idx, np.arange(len(a)), a)
    add(voz, start, a, 1.0)
voz = voz / np.max(np.abs(voz)) * 0.9
sf.write(sys.argv[3], voz.astype(np.float32), SR)
print('ok')
