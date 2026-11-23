# Montaje de "Tu casa en el Sahara": subtítulo de UNA palabra grande (estilo explicativo), rótulos, música y efectos.
# Uso: python3 compose_sahara.py <carpeta_frames> <voz.wav> <words.json> <salida.mp4>
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

FR, VOZ, WJ, OUTP = sys.argv[1:5]
W, H, FPS, SR = 1080, 1920, 24, 44100
CUTS = [('S1', 0.0), ('S2', 6.0), ('S3', 11.6), ('S4', 19.3), ('S5', 22.8), ('S6', 28.8), ('S7', 32.9),
        ('S8', 39.7), ('S9', 44.2), ('S10', 49.4), ('S11', 54.4), ('END', 63.4)]
END = CUTS[-1][1]
FIX = {'cabas': 'cavas', 'fogaras.': 'foggaras.', '45': '45°', '2.': '2.'}
words = json.load(open(WJ))
for w in words:
    k = w[2].lower()
    if k in FIX: w[2] = FIX[k] if w[2][0].islower() else FIX[k].capitalize()
KEY = {'SAHARA', 'HORNO', '45°', 'GRADOS', 'BARRO', 'HORAS', 'NOCHE', 'MUCHÍSIMO', 'TEMPLADA', 'SOFOCANTE', 'TORRE', 'VIENTO',
       'AGUA', 'GOTA', 'TÚNEL', 'KILÓMETROS', 'ARGELIA', 'FOGGARAS', 'HIELO', 'ELECTRICIDAD', 'PARTE', '2', 'LISTO', 'CALOR'}

def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

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
def note(m): return 440 * 2 ** ((m - 69) / 12)
S = {k: (a, CUTS[i + 1][1]) for i, (k, a) in enumerate(CUTS[:-1])}
mus = np.zeros(N); sfx = np.zeros(N)
# música: marimba curiosa (escala árabe suave: hijaz) + bajo, más baja por la noche
scale = [62, 63, 66, 67, 69, 70, 72, 74]
beat = 60 / 112
pat = [0, 2, 4, 2, 5, 4, 2, 1, 0, 2, 4, 6, 5, 4, 2, 3]
for k, x in enumerate(np.arange(0.0, END - 1.2, beat / 2)):
    night = S['S4'][0] <= x < S['S6'][0]
    if k % 2 == 0 or not night:
        add(mus, x, tone(note(scale[pat[k % 16]]), 0.35, 9), 0.09 * (0.6 if night else 1.0))
    if k % 4 == 0: add(mus, x, tone(note(scale[[0, 0, 3, 4][(k // 8) % 4]] - 24), 0.5, 5), 0.16)
    if k % 8 == 4: add(mus, x, noise(0.12, 0.6, 30), 0.15)
# efectos por escena
a, b = S['S1']
for x in np.arange(a + 0.9, a + 4.4, 0.45):
    add(sfx, x, tone(1900, 0.08, 40, 'sine') + noise(0.08, 0.7, 40) * 0.8, 0.35)          # martillo
add(sfx, a + 4.6, tone(note(84), 0.5, 6), 0.25); add(sfx, a + 4.75, tone(note(88), 0.6, 5), 0.25)  # "¡listo!"
a, b = S['S2']
sfx += 0.25 * onepole(rng.standard_normal(N), 0.6) * env(a + 3.2, b, 0.8) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t))  # chisporroteo
add(sfx, a + 1.0, whoosh(1.2), 0.6)
a, b = S['S3']; add(sfx, a, whoosh(0.4), 0.8)
for k in range(5): add(sfx, a + 1.4 + k * 0.12, whoosh(0.3), 0.3)
a, b = S['S4']
for x in np.arange(a, S['S5'][1], 0.33):   # grillos
    n = int(0.09 * SR); tt = np.arange(n) / SR
    add(sfx, x + rng.uniform(0, 0.1), np.sin(2 * np.pi * 4300 * tt) * (np.sin(2 * np.pi * 60 * tt) > 0) * np.exp(-tt * 20), 0.06)
sfx += 0.6 * onepole(rng.standard_normal(N), 0.02) * env(a, S['S4'][1], 0.4)
a, b = S['S6']
for k in range(10): add(sfx, a + 0.2 + k * 0.4, whoosh(0.2), 0.15)   # abanicarse
a, b = S['S7']
sfx += 1.4 * onepole(rng.standard_normal(N), 0.03) * env(a + 0.8, b, 0.6) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.4 * t))
add(sfx, a + 3.6, tone(note(79), 0.8, 4), 0.2); add(sfx, a + 3.8, tone(note(84), 0.9, 4), 0.2)
a, b = S['S8']
n = int(0.25 * SR); tt = np.arange(n) / SR
add(sfx, a + 1.5, np.sin(2 * np.pi * (1500 - 3000 * tt) * tt) * np.exp(-tt * 18), 0.5)          # gota
add(sfx, a + 2.0, tone(note(55), 0.9, 3), 0.25)
a, b = S['S9']
for x in np.arange(a + 0.1, a + 3.8, 0.35): add(sfx, x, noise(0.12, 0.5, 25), 0.5)               # cavar
sfx += 0.8 * onepole(rng.standard_normal(N), 0.08) * env(a + 1.2, b, 0.5) * (0.7 + 0.3 * np.sin(2 * np.pi * 3 * t))  # agua
a, b = S['S10']; add(sfx, a, whoosh(0.8), 1.0)
a, b = S['S11']
add(sfx, a, whoosh(0.6), 0.7)
for j, m in enumerate([74, 77, 81, 86]): add(mus, a + 2.5 + j * 0.35, tone(note(m), 2.0, 2, 'sine'), 0.1)
add(sfx, END - 2.0, tone(note(43), 2.0, 2), 0.5); add(sfx, END - 2.0, noise(1.5, 0.05, 2), 0.8)
bed = mus + 0.6 * sfx; bed *= np.clip((END - t) / 0.5, 0, 1); bed = bed / np.max(np.abs(bed)) * 0.8
bedp = '/tmp/claude-0/_sahara_bed.wav'; sf.write(bedp, np.stack([bed, np.roll(bed, 200)], 1).astype(np.float32), SR)
mix = '/tmp/claude-0/_sahara_mix.wav'
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
    txt = w.strip(',.:;').upper()
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
def tag(img, text, x, y, f, alpha=1.0, col=(255, 255, 255)):
    ImageDraw.Draw(img).text((x, y), text, font=f, fill=col + (int(255 * alpha),), stroke_width=8, stroke_fill=(0, 0, 0, int(255 * alpha)), anchor='mm')

# ------------------------------------------------------------------ video
cache = {}
def frames(k):
    if k not in cache: cache[k] = sorted(os.path.join(FR, k, f) for f in os.listdir(os.path.join(FR, k)) if f.endswith('.jpg'))
    return cache[k]
ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                       '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUTP], stdin=subprocess.PIPE)
nf = int(END * FPS)
for f in range(nf):
    g = f / FPS
    for k, (a, b) in S.items():
        if a <= g < b: break
    fr = frames(k); idx = min(len(fr) - 1, int((g - a) * FPS))
    img = Image.open(fr[idx]).convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
    if k == 'S2' and g - a > 2.0:
        al = sm((g - a - 2.0) / 0.3); tag(img, '+45°C', 300, 520, font(130), al, (255, 70, 50))
    if k == 'S10':
        al = sm((g - a - 0.3) / 0.3) * (1 - sm((g - b + 0.5) / 0.4)); tag(img, 'FOGGARAS', W / 2, 330, FT, al, (255, 214, 64)); tag(img, 'SAHARA · ARGELIA', W / 2, 420, FS, al)
    if k == 'S9' and g - a > 2.5:
        al = sm((g - a - 2.5) / 0.3); tag(img, 'ACUÍFERO', 260, 1450, FS, al, (120, 200, 255)); tag(img, 'TU CASA', 820, 760, FS, al)
    if g > 61.3:
        al = sm((g - 61.3) / 0.25); sc = 1.3 - 0.3 * al
        tag(img, 'PARTE 2', W / 2, 520, font(int(150 * sc)), al, (255, 214, 64))
    for a2, b2, im in WIMG:
        if a2 <= g < b2:
            age = g - a2; k2 = min(1.0, age / 0.08); s2 = 1.18 - 0.18 * k2
            im2 = im.resize((int(im.width * s2), int(im.height * s2)), Image.BILINEAR) if s2 != 1 else im
            img.alpha_composite(im2, (int((W - im2.width) / 2), int(880 - im2.height / 2)))
            break
    ff.stdin.write(img.convert('RGB').tobytes())
    if f % 240 == 0: print('frame', f, '/', nf, flush=True)
ff.stdin.close(); ff.wait(); print('ok', OUTP)
