# Montaje de "El congelador de 2.000 años": subtítulo de UNA palabra grande (estilo explicativo), rótulos, música y efectos.
# Uso: python3 compose_sahara.py <carpeta_frames> <voz.wav> <words.json> <salida.mp4>
import sys, os, json, math, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

FR, VOZ, WJ, OUTP = sys.argv[1:5]
W, H, FPS, SR = 1080, 1920, 24, 44100
CUTS = [('H', 0.0), ('A1', 8.5), ('A2', 13.8), ('A3', 17.7), ('A4', 22.4), ('A5', 28.3), ('A6', 33.3), ('A7', 40.9),
        ('A8', 49.2), ('A9', 59.8), ('A10', 63.3), ('A11', 72.9), ('END', 79.2)]
END = CUTS[-1][1]
FIX = {'saruj,': 'sarooj,', 'yakchales': 'yakhchales', '40': '40°'}
words = json.load(open(WJ))
for w in words:
    k = w[2].lower()
    if k in FIX: w[2] = FIX[k] if w[2][0].islower() else FIX[k].capitalize()
KEY = {'CONGELADOR', 'AÑOS', 'DESIERTO', 'CABLE', 'HIELO', 'SOL', 'DERRITE', 'MURO', 'SOMBRA', 'CERO', 'PROBLEMA', 'VERANO', '40°',
       'POZO', 'CALIENTE', 'CÚPULA', 'ARRIBA', 'FRÍO', 'CALOR', 'SAROOJ', 'HUEVO', 'METROS', 'PERSAS', 'POSTRES', 'YAKHCHALES', 'IRÁN',
       'INVENTO', 'TECNOLOGÍA', 'COMENTARIOS', 'MIL', 'DOS', 'FÁCIL'}

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
    night = S['A1'][0] <= x < S['A2'][0]
    if k % 2 == 0 or not night:
        add(mus, x, tone(note(scale[pat[k % 16]]), 0.35, 9), 0.09 * (0.6 if night else 1.0))
    if k % 4 == 0: add(mus, x, tone(note(scale[[0, 0, 3, 4][(k // 8) % 4]] - 24), 0.5, 5), 0.16)
    if k % 8 == 4: add(mus, x, noise(0.12, 0.6, 30), 0.15)
# efectos por escena
a, b = S['H']
add(sfx, 0.0, whoosh(1.4), 1.0)
for j, m in enumerate([88, 91, 95, 100]): add(mus, 2.6 + j * 0.12, tone(note(m), 1.2, 4, 'sine'), 0.12)   # destellos del hielo
a, b = S['A1']
for x in np.arange(a, b, 0.33):
    n = int(0.09 * SR); tt = np.arange(n) / SR
    add(sfx, x + rng.uniform(0, 0.1), np.sin(2 * np.pi * 4300 * tt) * (np.sin(2 * np.pi * 60 * tt) > 0) * np.exp(-tt * 20), 0.06)
add(sfx, a + 1.6, noise(0.3, 0.2, 10), 0.4)
a, b = S['A2']
sfx += 0.3 * onepole(rng.standard_normal(N), 0.5) * env(a + 0.5, b, 0.6)
add(sfx, a + 2.6, tone(note(52), 1.0, 3), 0.3); add(sfx, a + 2.8, tone(note(49), 1.2, 3), 0.3)
a, b = S['A3']
add(sfx, a, noise(2.4, 0.03, 0.8), 2.0)
a, b = S['A4']
for x in np.arange(a + 0.5, a + 3.0, 0.11): add(sfx, x + rng.uniform(0, 0.05), tone(rng.uniform(2500, 5000), 0.05, 50, 'sine'), 0.12)  # se congela
for j, m in enumerate([72, 76, 79]): add(mus, a + 3.4 + j * 0.15, tone(note(m), 0.8, 4), 0.12)
for x in (a + 4.1, a + 4.4): add(sfx, x, noise(0.15, 0.6, 20), 0.6)
a, b = S['A5']
sfx += 0.25 * onepole(rng.standard_normal(N), 0.6) * env(a, b, 0.5)
for x in np.arange(a + 1.0, b, 0.42): add(sfx, x, tone(1200, 0.12, 30, 'sine'), 0.15)
a, b = S['A6']
for x in np.arange(a + 0.1, a + 3.0, 0.35): add(sfx, x, noise(0.12, 0.5, 25), 0.5)
for k in range(18): add(sfx, a + 1.2 + k * 0.12 + 0.35, noise(0.06, 0.4, 40), 0.25)
add(sfx, a + 5.4, whoosh(1.2), 0.7)
a, b = S['A7']
add(sfx, a, noise(1.6, 0.03, 1.5), 2.0)
sfx += 0.9 * onepole(rng.standard_normal(N), 0.04) * env(a + 1.8, b, 0.6)
a, b = S['A8']
for tt in (54.4, 55.2, 56.1, 56.7, 57.4, 58.6):
    n = int(0.15 * SR); tq = np.arange(n) / SR
    add(sfx, tt, np.sin(2 * np.pi * (400 + 1400 * tq / 0.15) * tq) * np.exp(-tq * 22), 0.45)
a, b = S['A9']; add(sfx, a + 0.4, tone(note(84), 0.6, 5), 0.3)
a, b = S['A10']
for j, m in enumerate([72, 76, 79, 84]): add(mus, a + 0.3 + j * 0.15, tone(note(m), 0.9, 4), 0.12)
a, b = S['A11']; add(sfx, a, whoosh(0.8), 0.7)
add(sfx, END - 1.6, tone(note(48), 1.6, 2), 0.4)
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
    if k == 'H' and g > 0.6:
        al = sm((g - 0.6) / 0.3) * (1 - sm((g - 7.6) / 0.5)); tag(img, '+2.000 AÑOS', W / 2, 360, font(112), al, (120, 210, 255))
    if k == 'A4' and 1.4 < g - a < 3.4:
        al = sm((g - a - 1.4) / 0.3) * (1 - sm((g - a - 3.0) / 0.4)); tag(img, 'BAJO 0°C', W / 2, 400, font(120), al, (120, 210, 255))
    if k == 'A5' and g - a > 1.5:
        al = sm((g - a - 1.5) / 0.3); tag(img, '+40°C', 300, 560, font(130), al, (255, 70, 50))
    if k == 'A9' and g - a > 0.5:
        al = sm((g - a - 0.5) / 0.3); tag(img, '≈ 2 M', 330, 1200, font(110), al, (255, 214, 64))
    if k == 'A10' and g > 69.0:
        al = sm((g - 69.0) / 0.3); tag(img, 'YAKHCHAL', W / 2, 330, FT, al, (255, 214, 64)); tag(img, 'IRÁN', W / 2, 420, FS, al)
    for a2, b2, im in WIMG:
        if a2 <= g < b2:
            age = g - a2; k2 = min(1.0, age / 0.08); s2 = 1.18 - 0.18 * k2
            im2 = im.resize((int(im.width * s2), int(im.height * s2)), Image.BILINEAR) if s2 != 1 else im
            img.alpha_composite(im2, (int((W - im2.width) / 2), int(880 - im2.height / 2)))
            break
    ff.stdin.write(img.convert('RGB').tobytes())
    if f % 240 == 0: print('frame', f, '/', nf, flush=True)
ff.stdin.close(); ff.wait(); print('ok', OUTP)
