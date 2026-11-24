# Montaje v2 de "El congelador de 2.000 años": gancho-pregunta con avances rápidos, ritmo más rápido y
# cambio de plano cada ~2 s (punch-ins / encuadres distintos sobre los planos renderizados).
# Uso: python3 compose_hielo_v2.py <carpeta_frames> <carpeta_scratch> <salida.mp4>
#      (lee voz_v2.wav, words_v2.json, map_v2.json generados por voz_v2.py)
import sys, os, json, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FR, D, OUTP = sys.argv[1:4]
VOZ = os.path.join(D, 'voz_v2.wav')
W, H, FPS, SR = 1080, 1920, 24, 44100
MP = json.load(open(os.path.join(D, 'map_v2.json')))
END = MP['END']; HOOK = MP['hook_end']
CUTS = [('HOOK', 0.0, 0.0)] + [tuple(c) for c in MP['cuts']] + [('END', END, 79.2)]
S = {k: (a, CUTS[i + 1][1]) for i, (k, a, _) in enumerate(CUTS[:-1])}       # tiempos nuevos
SO = {k: (o, CUTS[i + 1][2]) for i, (k, _, o) in enumerate(CUTS[:-1])}      # tiempos del montaje viejo
OX, OY = np.array(MP['o2n']).T
def o2n(x): return float(np.interp(x, OX, OY))
def n2o(g, k):  # tiempo nuevo -> tiempo viejo equivalente dentro del plano k
    a, b = S[k]; oa, ob = SO[k]
    return oa + (g - a) / (b - a) * (ob - oa)

FIX = {'saruj,': 'sarooj,', 'yakchales': 'yakhchales', '40': '40°'}
words = json.load(open(os.path.join(D, 'words_v2.json')))
for w in words:
    k = w[2].lower()
    if k in FIX: w[2] = FIX[k] if w[2][0].islower() else FIX[k].capitalize()
KEY = {'CONGELADOR', 'AÑOS', 'DESIERTO', 'CABLE', 'HIELO', 'SOL', 'DERRITE', 'MURO', 'SOMBRA', 'CERO', 'PROBLEMA', 'VERANO', '40°',
       'POZO', 'CALIENTE', 'CÚPULA', 'ARRIBA', 'FRÍO', 'CALOR', 'SAROOJ', 'HUEVO', 'METROS', 'PERSAS', 'POSTRES', 'YAKHCHALES', 'IRÁN',
       'INVENTO', 'TECNOLOGÍA', 'COMENTARIOS', 'MIL', 'DOS', 'FÁCIL', '2.000', 'ELECTRICIDAD', '45', 'GRADOS', 'SECRETO', 'INGREDIENTE',
       'ADIVINARÍAS', 'JAMÁS', 'SABES'}
def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def wstart(txt, after=0.0):
    return next(w[0] for w in words if w[0] >= after and w[2].strip('¿?,.').lower() == txt)

# ------------------------------------------------------------------ plan de planos
# gancho: avances rápidos de lo que viene (bucle abierto: el "ingrediente secreto" se resuelve en el sarooj)
t_pleno = wstart('en'); t_hace = wstart('hace'); t_sin = wstart('sin'); t_a = wstart('a', t_sin); t_y = wstart('y', t_a)
CLIPS = [  # (t0, t1, plano, f0, f1, zoom, cx, cy, efecto)
    (0.0, t_pleno, 'H', 105, 204, 1.18, 0.55, 0.42, None),
    (t_pleno, t_hace, 'H', 0, 70, 1.0, 0.5, 0.5, None),
    (t_hace, t_sin, 'A8', 0, 90, 1.08, 0.5, 0.45, None),
    (t_sin, t_a, 'A7', 50, 160, 1.12, 0.5, 0.55, None),
    (t_a, t_y, 'A5', 10, 115, 1.0, 0.5, 0.5, None),
    (t_y, HOOK, 'A8', 150, 254, 1.0, 0.5, 0.55, 'mystery'),
]
# resto: cada escena se parte en trozos de ~2 s (cortes en inicio de palabra) con encuadres alternos
FRAMES = [(1.0, 0.5, 0.5), (1.3, 0.5, 0.56), (1.14, 0.42, 0.5), (1.22, 0.58, 0.45), (1.0, 0.5, 0.5), (1.32, 0.5, 0.62)]
LIMIT = {'A8': (1.1, 0.5, 0.6), 'A9': (1.0, 0.5, 0.5), 'A4': (1.2, 0.5, 0.55)}
TARGET = 1.9
fi = 0
for i, (k, a, _) in enumerate(CUTS[1:-1], 1):
    b = CUTS[i + 1][1]
    n = max(1, round((b - a) / TARGET)); bounds = [a]
    for j in range(1, n):
        x = a + (b - a) * j / n
        cand = [w[0] for w in words if a + 0.9 < w[0] < b - 0.9]
        if cand: x = min(cand, key=lambda c: abs(c - x))
        if x - bounds[-1] > 0.8: bounds.append(x)
    bounds.append(b)
    for t0, t1 in zip(bounds[:-1], bounds[1:]):
        z, cx, cy = FRAMES[fi % len(FRAMES)]; fi += 1
        if k in LIMIT:
            zl, lx, ly = LIMIT[k]
            if z > zl: z, cx, cy = zl, lx, ly
        CLIPS.append((t0, t1, k, None, None, z, cx, cy, 'scene' if t0 == a else None))
CHANGES = [c[0] for c in CLIPS[1:]]
print(len(CLIPS), 'planos; corte medio', round(END / len(CLIPS), 2), 's')

# ------------------------------------------------------------------ audio
N = int(END * SR); t = np.arange(N) / SR; rng = np.random.default_rng(5)
def onepole(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
def add(buf, at, sig, amp=1.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if 0 <= i < N: buf[i:j] += amp * sig[:j - i]
def env(a, b, f=0.3): return np.clip((t - a) / f, 0, 1) * np.clip((b - t) / f, 0, 1)
def tone(f, d, dec=6, kind='pluck'):
    n = int(d * SR); tt = np.arange(n) / SR; ph = 2 * np.pi * f * tt
    s = np.sin(ph) + (0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph) if kind == 'pluck' else 0)
    return s * np.minimum(1, tt / 0.005) * np.exp(-tt * dec)
def noise(d, a=0.3, dec=8):
    n = int(d * SR); tt = np.arange(n) / SR
    return onepole(rng.standard_normal(n), a) * np.exp(-tt * dec)
def whoosh(d=0.5):
    n = int(d * SR); tt = np.arange(n) / SR
    return onepole(rng.standard_normal(n), 0.12) * np.sin(np.pi * tt / d) ** 2
def riser(d):
    n = int(d * SR); tt = np.arange(n) / SR
    x = rng.standard_normal(n); al = 0.05 + 0.25 * tt / d; y = np.empty(n); acc = 0.0
    for i in range(n): acc += al[i] * (x[i] - acc); y[i] = acc
    return y * (tt / d) ** 2
def note(m): return 440 * 2 ** ((m - 69) / 12)
mus = np.zeros(N); sfx = np.zeros(N)
scale = [62, 63, 66, 67, 69, 70, 72, 74]
beat = 60 / 122
pat = [0, 2, 4, 2, 5, 4, 2, 1, 0, 2, 4, 6, 5, 4, 2, 3]
for k, x in enumerate(np.arange(0.0, END - 1.2, beat / 2)):
    if t_y - 0.1 < x < HOOK: continue                       # silencio tenso antes de la respuesta
    night = S['A1'][0] <= x < S['A2'][0]
    if k % 2 == 0 or not night:
        add(mus, x, tone(note(scale[pat[k % 16]]), 0.35, 9), 0.09 * (0.6 if night else 1.0))
    if k % 4 == 0: add(mus, x, tone(note(scale[[0, 0, 3, 4][(k // 8) % 4]] - 24), 0.5, 5), 0.16)
    if k % 8 == 4: add(mus, x, noise(0.12, 0.6, 30), 0.15)
    if k % 2 == 1 and x > HOOK: add(mus, x, noise(0.04, 0.8, 60), 0.05)   # hi-hat para más energía
# gancho
for j, m in enumerate([88, 91, 95, 100]): add(mus, 0.15 + j * 0.1, tone(note(m), 1.2, 4, 'sine'), 0.12)
add(sfx, t_sin, tone(note(40), 0.5, 8), 0.35)                                     # "sin electricidad": corte seco
sfx += 0.25 * onepole(rng.standard_normal(N), 0.6) * env(t_a, t_y, 0.2)           # calor
add(sfx, t_y, tone(note(31), 1.6, 2, 'sine'), 0.7)                                # golpe grave misterio
add(sfx, HOOK - 1.6, riser(1.6), 0.6)
add(sfx, HOOK, noise(0.5, 0.15, 7), 0.8); add(sfx, HOOK, tone(note(36), 0.8, 4, 'sine'), 0.5)
# cambios de plano
for c in CLIPS[1:]:
    add(sfx, c[0] - 0.12, whoosh(0.28), 0.55 if c[8] else 0.22)
# efectos por escena (tiempos viejos -> nuevos)
a, b = S['A1']
for x in np.arange(a, b, 0.3):
    n = int(0.09 * SR); tt = np.arange(n) / SR
    add(sfx, x + rng.uniform(0, 0.1), np.sin(2 * np.pi * 4300 * tt) * (np.sin(2 * np.pi * 60 * tt) > 0) * np.exp(-tt * 20), 0.06)
add(sfx, o2n(SO['A1'][0] + 1.6), noise(0.3, 0.2, 10), 0.4)
a, b = S['A2']; oa = SO['A2'][0]
sfx += 0.3 * onepole(rng.standard_normal(N), 0.5) * env(o2n(oa + 0.5), b, 0.5)
add(sfx, o2n(oa + 2.6), tone(note(52), 1.0, 3), 0.3); add(sfx, o2n(oa + 2.8), tone(note(49), 1.2, 3), 0.3)
add(sfx, S['A3'][0], noise(2.2, 0.03, 0.8), 2.0)
oa = SO['A4'][0]
for x in np.arange(oa + 0.5, oa + 3.0, 0.11): add(sfx, o2n(x) + rng.uniform(0, 0.05), tone(rng.uniform(2500, 5000), 0.05, 50, 'sine'), 0.12)
for j, m in enumerate([72, 76, 79]): add(mus, o2n(oa + 3.4) + j * 0.14, tone(note(m), 0.8, 4), 0.12)
for x in (oa + 4.1, oa + 4.4): add(sfx, o2n(x), noise(0.15, 0.6, 20), 0.6)
a, b = S['A5']
sfx += 0.25 * onepole(rng.standard_normal(N), 0.6) * env(a, b, 0.4)
for x in np.arange(a + 0.9, b, 0.38): add(sfx, x, tone(1200, 0.12, 30, 'sine'), 0.15)
oa = SO['A6'][0]
for x in np.arange(oa + 0.1, oa + 3.0, 0.35): add(sfx, o2n(x), noise(0.12, 0.5, 25), 0.5)
for k in range(18): add(sfx, o2n(oa + 1.2 + k * 0.12 + 0.35), noise(0.06, 0.4, 40), 0.25)
add(sfx, o2n(oa + 5.4), whoosh(1.1), 0.7)
a, b = S['A7']
add(sfx, a, noise(1.5, 0.03, 1.5), 2.0)
sfx += 0.9 * onepole(rng.standard_normal(N), 0.04) * env(o2n(SO['A7'][0] + 1.8), b, 0.5)
for x in (54.4, 55.2, 56.1, 56.7, 57.4, 58.6):
    n = int(0.15 * SR); tq = np.arange(n) / SR
    add(sfx, o2n(x), np.sin(2 * np.pi * (400 + 1400 * tq / 0.15) * tq) * np.exp(-tq * 22), 0.45)
for j, m in enumerate([84, 88, 91]): add(mus, o2n(58.6) + 0.15 + j * 0.1, tone(note(m), 0.8, 5, 'sine'), 0.12)   # "¡ese era el secreto!"
add(sfx, S['A9'][0] + 0.35, tone(note(84), 0.6, 5), 0.3)
a, b = S['A10']
for j, m in enumerate([72, 76, 79, 84]): add(mus, a + 0.3 + j * 0.14, tone(note(m), 0.9, 4), 0.12)
add(sfx, S['A11'][0], whoosh(0.8), 0.7)
add(sfx, END - 1.6, tone(note(48), 1.6, 2), 0.4)
bed = mus + 0.6 * sfx; bed *= np.clip((END - t) / 0.5, 0, 1); bed = bed / np.max(np.abs(bed)) * 0.8
bedp = '/tmp/claude-0/_hielo2_bed.wav'; sf.write(bedp, np.stack([bed, np.roll(bed, 200)], 1).astype(np.float32), SR)
mix = '/tmp/claude-0/_hielo2_mix.wav'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', VOZ, '-i', bedp, '-filter_complex',
                '[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=90,volume=1.8,asplit=2[v][sc];'
                '[1:a]volume=0.55[m];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=300[md];'
                '[v][md]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]',
                '-map', '[out]', '-ar', '44100', '-t', f'{END:.2f}', mix], check=True)

# ------------------------------------------------------------------ texto
def font(size, var=b'Black'):
    f = ImageFont.truetype(os.path.expanduser('~/.fonts/Montserrat.ttf'), size); f.set_variation_by_name(var); return f
FW = font(118); FT = font(84); FS = font(60, b'ExtraBold')
def clean(w): return w.strip('¡!¿?,.:;…').upper()
def word_img(w):
    txt = w.strip(',.:;…').rstrip('.').upper()
    col = (255, 214, 64, 255) if clean(w) in KEY else (255, 255, 255, 255)
    d = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    bb = d.textbbox((0, 0), txt, font=FW, stroke_width=10)
    im = Image.new('RGBA', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.text((20 - bb[0] + 6, 20 - bb[1] + 8), txt, font=FW, fill=(0, 0, 0, 120), stroke_width=10, stroke_fill=(0, 0, 0, 120))
    dr.text((20 - bb[0], 20 - bb[1]), txt, font=FW, fill=col, stroke_width=10, stroke_fill=(0, 0, 0, 255))
    if im.width > W - 60:
        r = (W - 60) / im.width; im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    return im
WIMG = [(w[0], w[1], word_img(w[2])) for w in words]
for i in range(len(WIMG) - 1):
    a, b, im = WIMG[i]
    if WIMG[i + 1][0] - b < 0.35: WIMG[i] = (a, WIMG[i + 1][0], im)
def tag(img, text, x, y, f, alpha=1.0, col=(255, 255, 255), scale=1.0):
    if alpha <= 0: return
    ImageDraw.Draw(img).text((x, y), text, font=f, fill=col + (int(255 * alpha),), stroke_width=8, stroke_fill=(0, 0, 0, int(255 * alpha)), anchor='mm')

# ------------------------------------------------------------------ video
cache = {}
def frames(k):
    if k not in cache: cache[k] = sorted(os.path.join(FR, k, f) for f in os.listdir(os.path.join(FR, k)) if f.endswith('.jpg'))
    return cache[k]
def framed(path, z, cx, cy):
    src = Image.open(path).convert('RGB'); sw, sh = src.size
    cw, ch = sw / z, sh / z
    x0 = min(max(cx * sw - cw / 2, 0), sw - cw); y0 = min(max(cy * sh - ch / 2, 0), sh - ch)
    return src.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')
ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                       '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUTP], stdin=subprocess.PIPE)
nf = int(END * FPS); FB = font(130); QF = font(420)
for f in range(nf):
    g = f / FPS
    c = next((c for c in CLIPS if c[0] <= g < c[1]), CLIPS[-1])
    t0, t1, k, f0, f1, z, cx, cy, fx = c
    fr = frames(k)
    if f0 is not None:                                       # avance del gancho
        idx = int(f0 + (f1 - f0) * (g - t0) / (t1 - t0)); og = None
    else:
        og = n2o(g, k); idx = int((og - SO[k][0]) * FPS)
    idx = max(0, min(len(fr) - 1, idx))
    p = (g - t0) / 0.14
    zz = z * (1 + 0.08 * (1 - sm(p))) if p < 1 else z * (1 + 0.025 * (g - t0) / max(0.5, t1 - t0))   # golpe de zoom + deriva lenta
    img = framed(fr[idx], zz, cx, cy)
    # rótulos del gancho
    if c is CLIPS[2]: tag(img, '+2.000 AÑOS', W / 2, 360, font(112), sm((g - t0) / 0.15), (120, 210, 255))
    if c is CLIPS[3]: tag(img, 'SIN CABLES', W / 2, 360, font(112), sm((g - t0) / 0.15), (255, 214, 64))
    if c is CLIPS[4]: tag(img, '+45°C', W / 2, 360, font(150), sm((g - t0) / 0.15), (255, 70, 50))
    if fx == 'mystery':
        dark = Image.new('RGBA', (W, H), (0, 0, 0, 205)); img = img.filter(ImageFilter.GaussianBlur(10)); img.alpha_composite(dark)
        pul = 1 + 0.06 * np.sin((g - t0) * 9)
        tag(img, '?', W / 2, 1380, font(int(420 * pul)), sm((g - t0) / 0.2), (255, 214, 64))
        tag(img, 'INGREDIENTE SECRETO', W / 2, 360, font(80), sm((g - t0) / 0.2), (255, 214, 64))
    # rótulos del cuerpo (en tiempo viejo equivalente)
    if og is not None:
        a = SO[k][0]
        if k == 'A4' and 1.4 < og - a < 3.4:
            al = sm((og - a - 1.4) / 0.3) * (1 - sm((og - a - 3.0) / 0.4)); tag(img, 'BAJO 0°C', W / 2, 400, font(120), al, (120, 210, 255))
        if k == 'A5' and og - a > 1.5:
            tag(img, '+40°C', 300, 560, font(130), sm((og - a - 1.5) / 0.3), (255, 70, 50))
        if k == 'A8' and og > 54.2:
            tag(img, 'EL SECRETO:', W / 2, 330, FT, sm((og - 54.2) / 0.3), (255, 214, 64))
        if k == 'A9' and og - a > 0.5:
            tag(img, '≈ 2 M', 330, 1200, font(110), sm((og - a - 0.5) / 0.3), (255, 214, 64))
        if k == 'A10' and og > 69.0:
            al = sm((og - 69.0) / 0.3); tag(img, 'YAKHCHAL', W / 2, 330, FT, al, (255, 214, 64)); tag(img, 'IRÁN', W / 2, 420, FS, al)
    if p < 0.6 and c[8] == 'scene' or (fx is None and f0 is not None and p < 0.5):   # destello blanco en cambio de escena
        img.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(150 * (1 - p / 0.6)))))
    for a2, b2, im in WIMG:
        if a2 <= g < b2:
            age = g - a2; k2 = min(1.0, age / 0.08); s2 = 1.18 - 0.18 * k2
            im2 = im.resize((int(im.width * s2), int(im.height * s2)), Image.BILINEAR) if s2 != 1 else im
            img.alpha_composite(im2, (int((W - im2.width) / 2), int(880 - im2.height / 2)))
            break
    ff.stdin.write(img.convert('RGB').tobytes())
    if f % 240 == 0: print('frame', f, '/', nf, flush=True)
ff.stdin.close(); ff.wait(); print('ok', OUTP)
