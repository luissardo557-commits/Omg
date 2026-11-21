"""Reel vertical 9:16: "Ciudad subterranea".

Animacion 2D minimalista: un solo muñeco blanco de lineas, sin cara,
sobre fondo negro. Sin texto, sin color, sin objetos extra.

Uso:
    python3 render.py                 # renderiza reel.mp4
    python3 render.py --stills DIR    # solo guarda fotogramas clave en DIR
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

W, H = 1080, 1920
S = 2  # supersampling para lineas suaves
FPS = 30


# ---------------------------------------------------------------- utilidades
def clamp(t, a=0.0, b=1.0):
    return max(a, min(b, t))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, t0, t1):
    """Progreso suavizado de t dentro del tramo [t0, t1]."""
    return ease((t - t0) / (t1 - t0))


def flick(t, k=0.0):
    """Parpadeo de llama, determinista."""
    return (math.sin(t * 13.0 + k) * 0.5 + math.sin(t * 7.3 + k * 2.1) * 0.35
            + math.sin(t * 23.0 + k * 0.7) * 0.15)


class Pen:
    def __init__(self, draw, cx, cy, z=1.0):
        self.d, self.cx, self.cy, self.z = draw, cx, cy, z

    def p(self, x, y):
        return ((x - self.cx) * self.z + W / 2) * S, ((y - self.cy) * self.z + H / 2) * S

    def wd(self, w):
        return max(1, int(round(w * self.z * S)))

    def line(self, pts, w=6, caps=True):
        sp = [self.p(*q) for q in pts]
        ww = self.wd(w)
        self.d.line(sp, fill=255, width=ww, joint="curve")
        if caps:
            r = ww / 2
            for x, y in (sp[0], sp[-1]):
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=255)

    def poly(self, pts, w=6):
        self.line(list(pts) + [pts[0], pts[1]], w, caps=False)

    def circle(self, x, y, r, w=6, black_fill=False):
        (ax, ay), (bx, by) = self.p(x - r, y - r), self.p(x + r, y + r)
        self.d.ellipse([ax, ay, bx, by], outline=255, width=self.wd(w),
                       fill=0 if black_fill else None)

    def arc(self, x, y, r, a0, a1, w=6):
        (ax, ay), (bx, by) = self.p(x - r, y - r), self.p(x + r, y + r)
        self.d.arc([ax, ay, bx, by], a0, a1, fill=255, width=self.wd(w))

    def dot(self, x, y, r):
        (ax, ay), (bx, by) = self.p(x - r, y - r), self.p(x + r, y + r)
        self.d.ellipse([ax, ay, bx, by], fill=255)


# ---------------------------------------------------------------- muñeco
def figure(pen, hx, hy, L, facing=1, torso=0.0, head=0.0,
           lt=0.0, ls=0.0, rt=0.0, rs=0.0, la=0.0, lf=0.0, ra=0.0, rf=0.0, w=9):
    """Muñeco de palitos sin cara. Angulos en grados.
    Piernas/brazos: 0 = hacia abajo, positivo = hacia delante.
    Torso/cabeza: 0 = vertical, positivo = inclinado hacia delante."""
    def vd(a):
        r = math.radians(a)
        return math.sin(r) * facing, math.cos(r)

    def vu(a):
        r = math.radians(a)
        return math.sin(r) * facing, -math.cos(r)

    def add(p, v, k):
        return p[0] + v[0] * k * L, p[1] + v[1] * k * L

    hip = (hx, hy)
    tv = vu(torso)
    neck = add(hip, tv, 0.33)
    sh = add(hip, tv, 0.29)
    hr = 0.085
    hc = add(neck, vu(torso + head), 0.035 + hr)

    lk = add(hip, vd(lt), 0.26)
    lft = add(lk, vd(lt + ls), 0.26)
    rk = add(hip, vd(rt), 0.26)
    rft = add(rk, vd(rt + rs), 0.26)
    le = add(sh, vd(la), 0.17)
    lh = add(le, vd(la + lf), 0.16)
    re = add(sh, vd(ra), 0.17)
    rh = add(re, vd(ra + rf), 0.16)

    pen.line([lft, lk, hip, rk, rft], w)
    pen.line([hip, neck], w)
    pen.line([lh, le, sh, re, rh], w)
    pen.circle(hc[0], hc[1], hr * L, w)
    return {"lh": lh, "rh": rh, "head": hc, "lf": lft, "rf": rft}


def walk_pose(p, amp=1.0):
    s, c = math.sin(p), math.cos(p)
    return dict(lt=28 * s * amp, rt=-28 * s * amp,
                ls=-8 - 32 * max(0, c) * amp, rs=-8 - 32 * max(0, -c) * amp,
                la=-22 * s * amp, lf=18, ra=22 * s * amp, rf=18)


def flame(pen, x, y, h, w, t, k=0.0, w_line=5):
    """Llama de contorno blanco apoyada en (x, y)."""
    f = flick(t, k)
    hh = h * (1 + 0.14 * f)
    tipx = x + w * 0.45 * flick(t * 1.3, k + 3)
    pts = []
    for a in np.linspace(-15, 195, 18):
        r = math.radians(a)
        pts.append((x + w * math.cos(r), y - w + w * math.sin(r)))
    pts = pts[::-1]
    pts.insert(0, (tipx, y - hh))
    pts.append((tipx, y - hh))
    pen.line(pts, w_line, caps=False)
    # llama interior
    ih, iw = hh * 0.5, w * 0.45
    pen.line([(x - iw, y - iw * 0.8), (x + 0.4 * (tipx - x), y - ih), (x + iw, y - iw * 0.8)],
             max(2, w_line - 2))


def rays(pen, x, y, r0, r1, n, t, a0=0, a1=360, w=3, k=0.0):
    for i in range(n):
        a = math.radians(lerp(a0, a1, (i + 0.5) / n))
        ln = lerp(r0, r1, 0.6 + 0.4 * flick(t * 0.8, i * 1.7 + k))
        pen.line([(x + math.cos(a) * r0, y + math.sin(a) * r0),
                  (x + math.cos(a) * ln, y + math.sin(a) * ln)], w)


# ---------------------------------------------------------------- escenas
def scene_gancho(d, t, D):
    """1. El suelo se agrieta a los pies del muñeco."""
    k = seg(t, 0.0, D)
    pen = Pen(d, lerp(540, 640, k), lerp(960, 1160, k), lerp(1.0, 1.35, k))
    G, cx = 1250, 700
    wdt = lerp(6, 170, seg(t, 0.7, 3.6))
    depth = 60 + wdt * 1.4
    rng = random.Random(4)
    n = 9
    left, right = [], []
    for i in range(n + 1):
        f = i / n
        jy = G + depth * f
        j = rng.uniform(-1, 1) * 14 * (1 - f) * min(1, wdt / 40)
        half = wdt / 2 * (1 - f) ** 0.8
        left.append((cx - half + j, jy))
        right.append((cx + half + j * 0.6, jy))
    pen.line([(-600, G), (cx - wdt / 2, G)], 7)
    pen.line([(cx + wdt / 2, G), (1800, G)], 7)
    pen.line(left + right[::-1][1:], 5, caps=False)
    # pequeñas grietas laterales
    g2 = seg(t, 1.2, 3.0)
    if g2 > 0:
        pen.line([(cx + wdt / 2, G), (cx + wdt / 2 + 70 * g2, G + 30 * g2),
                  (cx + wdt / 2 + 120 * g2, G + 20 * g2)], 4)
        pen.line([(cx - wdt / 2, G), (cx - wdt / 2 - 50 * g2, G + 40 * g2)], 4)
    # luz de abajo: rayos saliendo de la grieta
    lk = seg(t, 1.4, 3.8)
    if lk > 0:
        for i in range(7):
            a = math.radians(lerp(-130, -50, (i + 0.5) / 7))
            ln = (90 + 120 * lk) * (0.75 + 0.25 * flick(t, i * 2.3))
            r0 = 30
            bx, by = cx, G + 10
            pen.line([(bx + math.cos(a) * r0, by + math.sin(a) * r0),
                      (bx + math.cos(a) * ln, by + math.sin(a) * ln)], 3)
    # muñeco mirando hacia abajo, retrocede un poco al final
    L = 380
    back = seg(t, 3.0, 4.2)
    pose = walk_pose(back * math.pi, amp=0.5 * (1 - back) if back > 0 else 0)
    pose.update(la=lerp(8, 30, back), ra=lerp(-6, 40, back), lf=10, rf=25)
    figure(pen, 330 - 40 * back, G - 0.52 * L, L, 1,
           torso=lerp(10, -4, back), head=lerp(32, 22, back), **pose)


def stair_y(x, x0=-200, y0=650, sw=120, rise=72):
    return y0 + math.floor((x - x0) / sw) * rise


def scene_bajada(d, t, D):
    """2. Baja escaleras estrechas con una antorcha."""
    L = 330
    x0, y0, sw, rise = -200, 650, 120, 72
    hx = 200 + 95 * t
    slope = rise / sw
    hy = y0 + (hx - x0) * slope - 0.5 * L + 10
    pen = Pen(d, hx + 140, hy + 140, 1.0)
    # escalones
    pts = []
    for i in range(-2, 24):
        x = x0 + i * sw
        y = y0 + i * rise
        pts += [(x, y), (x + sw, y)]
        pts.append((x + sw, y + rise))
    pen.line(pts, 6, caps=False)
    # techo del tunel, paralelo a la escalera
    cy = -560
    pen.line([(x0 - 2 * sw, y0 - 2 * rise + cy), (x0 + 24 * sw, y0 + 24 * rise + cy)], 6)
    # juntas de piedra en el techo
    for i in range(0, 24, 2):
        bx = x0 + i * sw + 40
        by = y0 + (bx - x0) * slope + cy
        pen.line([(bx, by), (bx, by + 28)], 3)
    p = t * 2 * math.pi * 0.95
    pose = walk_pose(p, 0.8)
    pose.update(ra=62, rf=-30)
    hy += -6 * abs(math.cos(p))
    f = figure(pen, hx, hy, L, 1, torso=6, head=18, **pose)
    # antorcha en la mano derecha
    h = f["rh"]
    tip = (h[0] + 22, h[1] - 70)
    pen.line([(h[0] - 8, h[1] + 20), tip], 7)
    flame(pen, tip[0], tip[1] + 6, 70, 18, t, 1.0, 4)
    rays(pen, tip[0], tip[1] - 22, 60, 110, 10, t, w=3, k=2)


def scene_interior(d, t, D):
    """3. Sala de piedra con tinajas y un fuego pequeño."""
    k = seg(t, 0, D)
    pen = Pen(d, 540, lerp(900, 980, k), lerp(1.0, 1.08, k))
    F = 1350
    # sala en arco
    l, r, top = 110, 970, 740
    arc_r = (r - l) / 2
    pen.line([(l, F + 1), (l, top)], 7)
    pen.line([(r, top), (r, F + 1)], 7)
    pen.arc((l + r) / 2, top, arc_r, 180, 360, 7)
    pen.line([(-200, F), (1300, F)], 7)
    # piedras del suelo
    for x in (220, 470, 760, 900):
        pen.line([(x, F + 30), (x + 60, F + 30)], 3)
    # estante con tres tinajas
    sy = 880
    pen.line([(610, sy), (930, sy)], 6)
    for i, jx in enumerate((655, 765, 880)):
        jw, jh = (32, 48, 28)[i], (90, 120, 75)[i]
        pen.line([(jx - jw * 0.4, sy - jh), (jx - jw, sy - jh * 0.75), (jx - jw, sy - 8),
                  (jx - jw * 0.7, sy), (jx + jw * 0.7, sy), (jx + jw, sy - 8),
                  (jx + jw, sy - jh * 0.75), (jx + jw * 0.4, sy - jh)], 5, caps=False)
        pen.line([(jx - jw * 0.5, sy - jh), (jx + jw * 0.5, sy - jh)], 5)
    # fuego
    fx = 590
    pen.line([(fx - 70, F - 4), (fx + 60, F - 30)], 7)
    pen.line([(fx - 60, F - 30), (fx + 70, F - 4)], 7)
    flame(pen, fx, F - 30, 150, 38, t, 0.0, 6)
    rays(pen, fx, F - 110, 140, 200, 12, t, a0=190, a1=350, w=3)
    # muñeco sentado, levanta las manos hacia el fuego
    L = 340
    up = seg(t, 1.0, 2.4)
    figure(pen, 300, F - 0.03 * L, L, 1, torso=lerp(2, 12, up), head=lerp(4, 14, up),
           lt=128, ls=-112, rt=82, rs=-4,
           la=lerp(20, 78, up), lf=lerp(30, 8, up),
           ra=lerp(35, 92, up), rf=lerp(25, 0, up))


def scene_ciudad(d, t, D):
    """4. Corte transversal de la ciudad: niveles y salas con fuego."""
    a = seg(t, 0.2, 3.2)
    b = seg(t, 3.3, D - 0.1)
    cy = lerp(lerp(700, 1500, a), 1200, b)
    z = lerp(1.15, 0.84, b)
    pen = Pen(d, 540, cy, z)
    G = 300
    rooms = [(420, 560), (660, 920), (430, 1280), (650, 1640), (540, 2000)]
    rw, rh = 430, 250
    hole = 470
    pen.line([(-400, G), (hole - 25, G)], 7)
    pen.line([(hole + 25, G), (1500, G)], 7)
    # estratos de tierra
    rng = random.Random(7)
    for i in range(70):
        x = rng.uniform(-150, 1230)
        y = rng.uniform(G + 40, 2250)
        if any(abs(x - rx) < rw / 2 + 40 and abs(y - ry) < rh / 2 + 40 for rx, ry in rooms):
            continue
        pen.line([(x, y), (x + rng.uniform(30, 80), y)], 2)

    def ladder(x, y0, y1):
        pen.line([(x - 18, y0), (x - 18, y1)], 4)
        pen.line([(x + 18, y0), (x + 18, y1)], 4)
        yy = y0 + 22
        while yy < y1 - 10:
            pen.line([(x - 18, yy), (x + 18, yy)], 3)
            yy += 34

    ladder(hole, G, rooms[0][1] + rh / 2)
    for (ax, ay), (bx, by) in zip(rooms, rooms[1:]):
        lx = (max(ax, bx) - rw / 2 + min(ax, bx) + rw / 2) / 2
        ladder(lx, ay + rh / 2, by + rh / 2)
    lad = [hole] + [(max(ax, bx) - rw / 2 + min(ax, bx) + rw / 2) / 2
                    for (ax, _), (bx, _) in zip(rooms, rooms[1:])]
    for i, (rx, ry) in enumerate(rooms):
        x0, x1, y0, y1 = rx - rw / 2, rx + rw / 2, ry - rh / 2, ry + rh / 2
        pen.line([(x0, y1), (x0, y0 + 40)], 6, caps=False)
        pen.arc(x0 + 40, y0 + 40, 40, 180, 270, 6)
        pen.line([(x0 + 40, y0), (x1 - 40, y0)], 6, caps=False)
        pen.arc(x1 - 40, y0 + 40, 40, 270, 360, 6)
        pen.line([(x1, y0 + 40), (x1, y1), (x0, y1)], 6, caps=False)
        fx = rx + (-130 if lad[i] > rx else 130)
        flame(pen, fx, y1 - 6, 60, 16, t, i * 1.9, 4)
        rays(pen, fx, y1 - 40, 55, 85, 7, t, a0=200, a1=340, w=2, k=i)


def scene_puerta(d, t, D):
    """5. Empuja una puerta circular de piedra para cerrar el tunel."""
    pen = Pen(d, 540, 1030, 1.0)
    F = 1300
    ax, aw, ah = 760, 300, 390
    r = 196
    # pared y tunel
    pen.line([(-300, F), (1400, F)], 7)
    pen.line([(ax - aw / 2, F), (ax - aw / 2, F - ah + aw / 2)], 7, caps=False)
    pen.arc(ax, F - ah + aw / 2, aw / 2, 180, 360, 7)
    pen.line([(ax + aw / 2, F - ah + aw / 2), (ax + aw / 2, F)], 7, caps=False)
    # profundidad del tunel
    iw, ih = aw * 0.55, ah * 0.6
    pen.line([(ax - iw / 2 + 25, F), (ax - iw / 2 + 25, F - ih + iw / 2)], 4, caps=False)
    pen.arc(ax + 25, F - ih + iw / 2, iw / 2, 180, 360, 4)
    pen.line([(ax + iw / 2 + 25, F - ih + iw / 2), (ax + iw / 2 + 25, F)], 4, caps=False)
    # juntas de la pared
    for (x, y) in ((200, 640), (330, 760), (950, 700), (1010, 980), (120, 1000), (980, 520)):
        pen.line([(x, y), (x + 70, y)], 3)
    # disco
    m = seg(t, 0.5, 3.4)
    dx = lerp(ax - 470, ax, m)
    dy = F - r
    rot = (dx - (ax - 470)) / r * 180 / math.pi
    pen.circle(dx, dy, r, 8, black_fill=True)
    pen.arc(dx, dy, r * 0.72, rot + 20, rot + 120, 4)
    pen.arc(dx, dy, r * 0.72, rot + 200, rot + 290, 4)
    for kk in (60, 250):
        aa = math.radians(rot + kk)
        pen.line([(dx + math.cos(aa) * r * 0.25, dy + math.sin(aa) * r * 0.25),
                  (dx + math.cos(aa) * r * 0.5, dy + math.sin(aa) * r * 0.5)], 4)
    # muñeco empujando
    L = 360
    rel = seg(t, 3.5, 4.3)
    hand_y = F - 0.5 * L - 0.25 * L
    contact = dx - math.sqrt(max(0, r * r - (hand_y - dy) ** 2))
    hx = contact - 0.47 * L - 6 - 70 * rel
    p = (dx - (ax - 470)) / 45
    pose = walk_pose(p, 0.9 * (1 - rel))
    pose.update(la=lerp(96, 10, rel), lf=lerp(-4, 18, rel),
                ra=lerp(92, -8, rel), rf=lerp(0, 18, rel))
    figure(pen, hx, F - 0.5 * L, L, 1, torso=lerp(30, 0, rel), head=lerp(-12, 0, rel), **pose)


def scene_final(d, t, D):
    """6. Mira una luz lejana arriba; fundido a negro."""
    k = seg(t, 0.2, D - 0.3)
    pen = Pen(d, 540, lerp(640, 120, k), lerp(1.0, 1.35, k))
    F = 1500
    top = -300
    lb, rb = (360, F), (720, F)
    lt_, rt_ = (500, top), (580, top)
    pen.line([lt_, lb], 6)
    pen.line([rt_, rb], 6)
    pen.line([(lb[0], F), (rb[0], F)], 6)
    for i in range(1, 14):
        f = i / 14
        y = lerp(F, top, f)
        xl = lerp(lb[0], lt_[0], f)
        xr = lerp(rb[0], rt_[0], f)
        ln = lerp(30, 8, f)
        pen.line([(xl, y), (xl + ln, y)], 3)
        pen.line([(xr - ln, y + 40), (xr, y + 40)], 3)
    # luz arriba
    sh = 1 - seg(t, 1.5, D - 0.4)
    lx, ly = 540, -240
    pen.dot(lx, ly, lerp(3, 12, sh))
    rays(pen, lx, ly, 18, lerp(22, 50, sh), 8, t, w=2)
    L = 330
    figure(pen, 540, F - 0.52 * L, L, 1, torso=-4, head=-38,
           la=12, lf=8, ra=-6, rf=10, lt=6, rt=-6, ls=-2, rs=-2)


SCENES = [
    (scene_gancho, 4.5),
    (scene_bajada, 5.0),
    (scene_interior, 4.5),
    (scene_ciudad, 5.5),
    (scene_puerta, 4.5),
    (scene_final, 5.0),
]


def render_frame(fn, t, D, idx):
    img = Image.new("L", (W * S, H * S), 0)
    fn(ImageDraw.Draw(img), t, D)
    img = img.reduce(S)
    fin = 0.4 if idx == 0 else 0.25
    fout = 1.6 if idx == len(SCENES) - 1 else 0.25
    a = clamp(min(t / fin, (D - t) / fout))
    if a < 1:
        img = Image.fromarray((np.asarray(img, dtype=np.float32) * a).astype(np.uint8))
    return img


def main():
    out_dir = Path(__file__).parent
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        dst = Path(sys.argv[2])
        dst.mkdir(parents=True, exist_ok=True)
        for i, (fn, D) in enumerate(SCENES):
            for j, f in enumerate((0.25, 0.5, 0.8)):
                render_frame(fn, D * f, D, i).save(dst / f"s{i + 1}_{j}.png")
        return
    out = out_dir / "reel_ciudad_subterranea.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, (fn, D) in enumerate(SCENES):
        n = int(round(D * FPS))
        for f in range(n):
            proc.stdin.write(render_frame(fn, f / FPS, D, i).tobytes())
        print(f"escena {i + 1} lista", flush=True)
    proc.stdin.close()
    proc.wait()
    print(out)


if __name__ == "__main__":
    main()
