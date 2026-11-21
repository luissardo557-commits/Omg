# Monta los 6 clips: escala a 1080x1920, títulos grandes + subtítulos, fundido a blanco, música.
# Uso: python3 compose.py <carpeta_frames> <musica.wav> <salida.mp4> [--clean]
import os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont

FR, MUSIC, OUTP = sys.argv[1:4]
CLEAN = '--clean' in sys.argv
FPS = 24; W, H = 1080, 1920
ORDER = [1, 2, 3, 4, 5, 6]
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

HEAD = [(0.2, 4.0, 'NO ES LA ÚNICA'), (4.0, 9.5, '200+ CIUDADES'), (9.5, 15.0, 'BAJO CAPADOCIA'),
        (15.0, 19.0, '2014'), (19.0, 23.0, 'NEVŞEHIR'), (23.0, 27.0, 'BAJO EL CASTILLO'),
        (40.0, 47.5, '¿MÁS GRANDE QUE\nDERINKUYU?'), (47.5, 55.0, 'NADIE SABE HASTA\nDÓNDE LLEGA'),
        (55.0, 61.0, '¿DE QUIÉN SE\nESCONDÍAN?'), (61.0, 65.0, 'PARTE 5')]
SUBS = [(0.0, 1.6, 'Derinkuyu no es la única.'),
        (1.6, 4.0, 'Bajo Capadocia hay muchas más ciudades escondidas.'),
        (4.0, 6.6, 'Kaymaklı, Özkonak, Mazı…'),
        (6.6, 10.4, 'Se estima que en la región hay más de 200 ciudades y refugios subterráneos.'),
        (10.4, 12.6, 'La mayoría son pequeños.'),
        (12.6, 15.0, 'Pero algunos son gigantes.'),
        (15.0, 17.8, 'Y una de las más sorprendentes apareció hace muy poco.'),
        (17.8, 20.6, 'En 2014, en la ciudad de Nevşehir,'),
        (20.6, 24.0, 'unas obras derribaban casas viejas alrededor del castillo.'),
        (24.0, 27.0, 'Debajo de ellas apareció la entrada a otra ciudad subterránea:'),
        (27.0, 31.5, 'túneles, habitaciones y capillas talladas en la roca,'),
        (31.5, 36.0, 'todo escondido durante siglos…'),
        (36.0, 40.0, '…justo debajo de la gente.'),
        (40.0, 43.6, 'Los primeros estudios sugieren que podría ser incluso más grande que Derinkuyu.'),
        (43.6, 46.4, 'Pero gran parte sigue enterrada,'),
        (46.4, 49.6, 'y excavarla es lento y delicado,'),
        (49.6, 52.4, 'porque encima hay calles, casas y gente viviendo hoy.'),
        (52.4, 55.0, 'Nadie sabe todavía hasta dónde llega.'),
        (55.0, 57.4, 'Pero hay una pregunta más importante.'),
        (57.4, 60.6, 'Si construyeron tantas ciudades bajo tierra…'),
        (60.6, 63.0, '¿de quién se estaban escondiendo?'),
        (63.0, 65.0, 'Te lo cuento en la parte 5.')]

def wrap(draw, text, font, maxw):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split():
            test = (cur + ' ' + w).strip()
            if draw.textlength(test, font=font) <= maxw: cur = test
            else: lines.append(cur); cur = w
        lines.append(cur)
    return lines

def text_img(text, size, fill, stroke, maxw, spacing=1.12):
    font = ImageFont.truetype(BOLD, size)
    d = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    lines = wrap(d, text, font, maxw)
    lh = int(size * spacing); pad = stroke + 10
    wmax = max(int(d.textlength(l, font=font)) for l in lines)
    im = Image.new('RGBA', (wmax + 2 * pad, lh * len(lines) + 2 * pad), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = (im.width - dr.textlength(l, font=font)) / 2
        dr.text((x, pad + i * lh), l, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return im

if len(sys.argv) > 4 and sys.argv[4].endswith('.json'):
    import json
    SUBS = [(a, b, SUBS[i][2]) for a, b, i in json.load(open(sys.argv[4]))]

head_imgs = [(a, b, text_img(s, 112, (255, 214, 64, 255), 10, 960)) for a, b, s in HEAD]
sub_imgs = [(a, b, text_img(s, 62, (255, 255, 255, 255), 7, 940)) for a, b, s in SUBS]

def paste_pop(base, im, cx, cy, age, pop=True):
    k = min(1.0, age / 0.18)
    s = (1.25 - 0.25 * k) if pop else 1.0
    if s != 1.0:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if k < 1:
        a = im.getchannel('A').point(lambda v: int(v * k)); im = im.copy(); im.putalpha(a)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

frames = []
for s in ORDER:
    d = os.path.join(FR, 's%d' % s)
    frames += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.jpg')]
total = len(frames); dur = total / FPS
print('frames', total, 'dur', dur)

ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-i', MUSIC, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                       '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUTP], stdin=subprocess.PIPE)
white = Image.new('RGBA', (W, H), (255, 255, 255, 255))
for i, fp in enumerate(frames):
    t = i / FPS
    im = Image.open(fp).convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
    if not CLEAN:
        for a, b, ti in head_imgs:
            if a <= t < b: paste_pop(im, ti, W / 2, 330 + ti.height / 2 - 60, t - a)
        for a, b, ti in sub_imgs:
            if a <= t < b: paste_pop(im, ti, W / 2, 1330, t - a, pop=False)
    fw = min(1.0, max(0.0, (t - (dur - 0.7)) / 0.6))
    if fw > 0: im = Image.blend(im, white, fw)
    ff.stdin.write(im.convert('RGB').tobytes())
ff.stdin.close(); ff.wait()
print('ok', OUTP)
