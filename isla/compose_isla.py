# Montaje final de "La isla prohibida": ajusta cada toma 3D a su frase, subtítulos, rótulos, música y efectos.
# Uso: python3 compose_isla.py <carpeta_frames> <voz.wav> <tiempos.json> <salida.mp4>
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

FR, VOZ, TJ, OUTP = sys.argv[1:5]
W, H, FPS, SR = 1080, 1920, 24, 44100
ORDER = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'B4', 'C1', 'D1', 'B5', 'B6', 'A4', 'C2', 'A5']
FONT = os.path.expanduser('~/.fonts/LuckiestGuy-Regular.ttf')
lines = json.load(open(TJ))
END = lines[-1]['end'] + 1.0

# límites de cada toma: empieza un poco antes de su frase
starts = [0.0] + [max(0.0, l['start'] - 0.15) for l in lines[1:]]
ends = starts[1:] + [END]
SH = list(zip(ORDER, starts, ends))

def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ------------------------------------------------------------------ audio: música + efectos
N = int(END * SR); t = np.arange(N) / SR
rng = np.random.default_rng(3)
def onepole(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
def add(buf, at, sig, amp=1.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if 0 <= i < N: buf[i:j] += amp * sig[:j - i]
def env_win(a, b, f=0.3): return np.clip((t - a) / f, 0, 1) * np.clip((b - t) / f, 0, 1)
def boom(d=2.0, f0=50):
    n = int(d * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 - 18 * tt / d) * tt) * np.exp(-tt * 2.5) + 0.4 * onepole(rng.standard_normal(n), 0.04) * np.exp(-tt * 5)
def hiss(d=0.9):
    n = int(d * SR); tt = np.arange(n) / SR
    x = rng.standard_normal(n); hp = x - onepole(x, 0.25)
    return hp * np.minimum(1, tt / 0.08) * np.exp(-tt * 2.2)
def whoosh(d=0.6):
    n = int(d * SR); tt = np.arange(n) / SR
    return onepole(rng.standard_normal(n), 0.1) * np.sin(np.pi * tt / d) ** 2
def tone(f, d, dec=4, kind='sine'):
    n = int(d * SR); tt = np.arange(n) / SR; ph = 2 * np.pi * f * tt
    s = np.sin(ph) if kind == 'sine' else (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph))
    return s * np.minimum(1, tt / 0.01) * np.exp(-tt * dec)
def note(m): return 440 * 2 ** ((m - 69) / 12)
S = {k: (a, b) for k, a, b in SH}

mus = np.zeros(N); sfx = np.zeros(N)
waves = onepole(rng.standard_normal(N), 0.012) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t) ** 2)
# olas en las tomas exteriores
for k in ('A1', 'A2', 'A3', 'C1', 'C2', 'A4', 'B1', 'B2', 'B3', 'A5'):
    sfx += 1.6 * waves * env_win(*S[k], 0.25)
# dron de suspenso todo el video, más intenso al final
k = np.clip(t / END, 0, 1)
drone = np.sin(2 * np.pi * 41.2 * t) + 0.6 * np.sin(2 * np.pi * 61.7 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)
mus += 0.12 * drone * (0.6 + 0.6 * k) * np.clip((END - t) / 0.8, 0, 1)
# pulso misterioso (pizzicato grave) que acelera
x = 0.1; i = 0
while x < END - 1.0:
    m = [40, 43, 40, 46, 40, 43, 47, 46][i % 8]
    add(mus, x, tone(note(m), 0.4, 9, 'rich'), 0.16); i += 1
    x += 0.5 - 0.18 * (x / END)
# campanita misteriosa en momentos clave
for kk in ('A1', 'B2', 'C1', 'A4'):
    for j, m in enumerate([76, 79, 83]): add(mus, S[kk][0] + 0.2 + j * 0.18, tone(note(m), 1.2, 3), 0.06)
# golpe de gancho, whooshes en cortes
# gancho: siseo, ataque de la serpiente a cámara, golpe y whoosh
add(sfx, 0.05, hiss(0.7), 0.7)
add(sfx, 0.5, whoosh(0.25), 1.4); add(sfx, 0.6, boom(2.5, 45), 1.4); add(sfx, 0.6, hiss(0.6), 1.0)
add(sfx, 1.05, whoosh(0.9), 1.0)
for kk, a, b in SH[1:]: add(sfx, a - 0.25, whoosh(0.5), 0.5)
# barco de la Marina: bocina
a = S['A2'][0]
n = int(1.6 * SR); tt = np.arange(n) / SR
horn = (np.sin(2 * np.pi * 110 * tt) + 0.5 * np.sin(2 * np.pi * 220 * tt) + 0.3 * np.sin(2 * np.pi * 330 * tt)) * np.minimum(1, tt / 0.1) * np.clip((1.6 - tt) / 0.3, 0, 1)
add(sfx, a + 0.6, horn, 0.35)
# salto de EE. UU.: boing + aterrizaje
a = S['A3'][0]; L = S['A3'][1] - a; f = L / 3.63
n = int(0.5 * SR); tt = np.arange(n) / SR
add(sfx, a + 0.8 * f, np.sin(2 * np.pi * (200 + 300 * tt) * tt) * np.exp(-tt * 5), 0.3)
add(sfx, a + 1.7 * f, boom(0.6, 80), 0.6)
# siseos y apariciones de serpientes
a, b = S['B1']; add(sfx, a + 0.5, onepole(rng.standard_normal(int(1.5 * SR)), 0.3) * 0.5, 0.5)
add(sfx, a + (b - a) * 0.35, hiss(1.0), 0.4)
a, b = S['B2']; f = (b - a) / 2.22
for d in (0.2, 0.8, 1.4): add(sfx, a + d * f, hiss(0.6), 0.6); add(sfx, a + d * f, boom(0.5, 70), 0.5)
a, b = S['B3']
for j in range(10): add(sfx, a + j * (b - a) / 10, hiss(0.8), 0.35)
add(sfx, a, boom(3.0, 38), 0.9)
a, b = S['B4']
for j in range(3): add(sfx, a + 0.5 + j * 1.9, hiss(1.2), 0.45)
# subida del mar
a, b = S['D1']
add(sfx, a + 0.3, onepole(rng.standard_normal(int(4.5 * SR)), 0.05) * np.sin(np.linspace(0, np.pi, int(4.5 * SR))), 1.6)
for j, m in enumerate([64, 67, 71, 74]): add(mus, a + 1.0 + j * 0.7, tone(note(m), 1.5, 2.5), 0.07)
# pájaro: aleteo y ataque
a, b = S['B5']; f = (b - a) / 5.29
for j in range(12): add(sfx, a + j * 0.16 * f, onepole(rng.standard_normal(int(0.07 * SR)), 0.4), 0.35)
add(sfx, a + 3.0 * f, hiss(1.0), 0.4)
a, b = S['B6']; f = (b - a) / 6.27
add(sfx, a + 0.6 * f, whoosh(0.3), 1.4); add(sfx, a + 0.62 * f, boom(1.5, 60), 1.0); add(sfx, a + 0.62 * f, hiss(0.5), 0.6)
for j in range(14): add(sfx, a + (0.8 + j * 0.15) * f, onepole(rng.standard_normal(int(0.06 * SR)), 0.4), 0.3)
add(sfx, a + 5.3 * f, whoosh(0.25), 1.4); add(sfx, a + 5.32 * f, boom(1.2, 70), 1.2); add(sfx, a + 5.32 * f, hiss(0.6), 0.8)
# faro: campanadas lejanas
a, b = S['A4']
for j in range(3): add(mus, a + 0.4 + j * 1.3, tone(note(57), 2.5, 1.5, 'rich'), 0.08)
# pregunta final y bucle
a, b = S['C2']; add(sfx, a + 1.6 * (b - a) / 4.08, boom(1.5, 60), 0.5)
a, b = S['A5']
r = (t > a) & (t < END - 0.6)
kk = np.clip((t - a) / (END - 0.6 - a), 0, 1)
mus += r * 0.1 * kk ** 2 * np.sin(2 * np.pi * (200 + 500 * kk ** 2) * t)
add(sfx, END - 0.9, boom(2.0, 40), 1.0); add(sfx, END - 0.9, hiss(0.8), 0.6)

bed = mus + 0.55 * sfx
bed = bed / np.max(np.abs(bed)) * 0.8
bedp = '/tmp/claude-0/_isla_bed.wav'; sf.write(bedp, np.stack([bed, np.roll(bed, 220)], 1).astype(np.float32), SR)
mix = '/tmp/claude-0/_isla_mix.wav'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', VOZ, '-i', bedp, '-filter_complex',
                '[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=90,volume=1.8,asplit=2[v][sc];'
                '[1:a]volume=0.6[m];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=300[md];'
                '[v][md]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]',
                '-map', '[out]', '-ar', '44100', '-t', f'{END:.2f}', mix], check=True)

# ------------------------------------------------------------------ texto
HL = {'BRASIL', 'PROHIBIDO', 'HUMANOS', 'QUEIMADA', 'GRANDE', 'MARINA', 'CIENTÍFICOS', 'REGLAS', 'ROCAS', 'SERPIENTES',
      'VENENOSAS', 'AQUÍ', 'ATRAPADAS', 'MAR', 'CONTINENTE', 'AVES', 'VENENO', 'RÁPIDO', 'FARO', 'SOLO', 'MILLÓN', 'TÚ',
      'SÍ', 'NO', 'VISTE', 'MILES', 'DORADA', 'EXTRAÑO', 'PELIGROSA', 'BARCO', 'ÚLTIMO', 'MILLÓN', 'SUELO', 'RAZÓN'}
def chunks():
    out = []
    for l in lines:
        words = l['text'].split(); groups = []; cur = []
        for w in words:
            cur.append(w)
            if len(cur) >= 3 or w.endswith((',', ':', '.', '?', '!', '...')): groups.append(cur); cur = []
        if cur: groups.append(cur)
        tot = sum(len(' '.join(g)) for g in groups); s = l['start']; d = l['end'] - l['start']
        for g in groups:
            dd = d * len(' '.join(g)) / tot; out.append([s, s + dd, g]); s += dd
    for i in range(len(out) - 1):
        if out[i + 1][0] - out[i][1] < 0.45: out[i][1] = out[i + 1][0]
    return out
SUBS = chunks()
F86 = ImageFont.truetype(FONT, 88); F60 = ImageFont.truetype(FONT, 60); F120 = ImageFont.truetype(FONT, 120)

def clean(w): return w.strip('¡!¿?,.:;…').upper()
def draw_words(img, words, cy, font, age, scale_pop=True):
    k = min(1.0, age / 0.12); s = 1.15 - 0.15 * k if scale_pop else 1.0
    d = ImageDraw.Draw(img)
    words = [w.upper() for w in words]
    sp = d.textlength(' ', font=font); wl = [d.textlength(w, font=font) for w in words]
    rows = [list(range(len(words)))]
    if sum(wl) + sp * (len(words) - 1) > 940 and len(words) > 1: rows = [list(range(len(words) - 1)), [len(words) - 1]]
    layer = Image.new('RGBA', (W, 400), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    for ri, row in enumerate(rows):
        tw = sum(wl[i] for i in row) + sp * (len(row) - 1); x = (W - tw) / 2; y = 60 + ri * 105
        for i in row:
            col = (255, 210, 63, 255) if clean(words[i]) in HL else (255, 255, 255, 255)
            ld.text((x, y), words[i], font=font, fill=col, stroke_width=9, stroke_fill=(0, 0, 0, 255)); x += wl[i] + sp
    if s != 1.0: layer = layer.resize((int(W * s), int(400 * s)), Image.BILINEAR)
    img.alpha_composite(layer, (int((W - layer.width) / 2), int(cy - layer.height / 2)))

def tag(img, text, x, y, font, alpha=1.0, col=(255, 255, 255)):
    d = ImageDraw.Draw(img)
    d.text((x, y), text, font=font, fill=col + (int(255 * alpha),), stroke_width=7, stroke_fill=(0, 0, 0, int(255 * alpha)), anchor='mm')

# ------------------------------------------------------------------ frames
cache = {}
def shot_frames(k):
    if k not in cache: cache[k] = sorted(os.path.join(FR, k, f) for f in os.listdir(os.path.join(FR, k)) if f.endswith('.jpg'))
    return cache[k]

ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                       '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUTP], stdin=subprocess.PIPE)
nf = int(END * FPS)
for f in range(nf):
    g = f / FPS
    for k, a, b in SH:
        if a <= g < b or (k == 'A5' and g >= a): break
    fr = shot_frames(k); u = (g - a) / (b - a)
    src = fr[min(len(fr) - 1, int(u * len(fr)))]
    img = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
    # rótulos
    if k == 'A1':
        ua = (g - a) / (b - a) * 5.92
        if 0.55 <= ua < 0.75:
            fl = 1 - (ua - 0.55) / 0.2
            img = Image.blend(img, Image.new('RGBA', (W, H), (255, 255, 255, 255)), 0.6 * fl)
        if 0.65 <= ua < 3.4:
            age = ua - 0.65; al = min(1.0, age / 0.1) * (1 - sm((ua - 3.0) / 0.4))
            sc = 1.35 - 0.35 * min(1.0, age / 0.15)
            Fb = ImageFont.truetype(FONT, int(150 * sc))
            tag(img, '¡NO TE', W / 2 + 6 * math.sin(g * 70) * max(0, 1 - age * 3), 360, Fb, al, (255, 255, 255))
            tag(img, 'BAJES!', W / 2 + 6 * math.sin(g * 60) * max(0, 1 - age * 3), 520, Fb, al, (235, 40, 40))
    if k == 'A2' and g - a < 3.5:
        al = sm((g - a - 0.3) / 0.3) * (1 - sm((g - a - 3.0) / 0.4))
        if al > 0: tag(img, 'ILHA DA QUEIMADA GRANDE', W / 2, 330, F60, al, (255, 210, 63)); tag(img, 'SÃO PAULO · BRASIL', W / 2, 400, F60, al)
    if k == 'D1':
        al = sm((g - a - 0.3) / 0.3)
        tag(img, 'HACE ~11.000 AÑOS', W / 2, 330, F86, al, (255, 210, 63))
        al2 = sm((g - a - 2.6) / 0.3)
        if al2 > 0: tag(img, 'CONTINENTE', 300, 1050, F60, al2); tag(img, 'ISLA', 800, 900, F60, al2)
    if k == 'B2':
        n = sum(1 for d in (0.2, 0.8, 1.4) if (g - a) / (b - a) * 2.22 >= d)
        if n: tag(img, '!' * n, W / 2, 330, F120, 1.0, (255, 80, 60))
    if k == 'A5' and g > END - 1.0:
        al = sm((g - (END - 1.0)) / 0.2)
        tag(img, '¿LA VISTE? 👀'.replace(' 👀', ''), W / 2, 420, F120, al, (255, 210, 63))
    for s0, s1, words in SUBS:
        if s0 <= g < s1: draw_words(img, words, 1400, F86, g - s0)
    ff.stdin.write(img.convert('RGB').tobytes())
    if f % 240 == 0: print('frame', f, '/', nf, flush=True)
ff.stdin.close(); ff.wait(); print('ok', OUTP, round(END, 2), 's')
