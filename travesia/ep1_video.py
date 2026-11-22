# LA GRAN TRAVESÍA DE AMÉRICA — Episodio 1: EL DESAFÍO (animación 2D countryballs con cairo)
# Uso: python3 ep1_video.py <lines.json> <audio.wav> <salida.mp4> [--preview t1,t2,...  carpeta]
import math, random, sys, json, subprocess, os
import cairo
from balls import ball, hexc
from ep1_timeline import T, NARR, HIGHLIGHT

W, H, FPS = 1080, 1920, 24
PI = math.pi
FONT = 'Luckiest Guy'

# ------------------------------------------------------------------ utilidades
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def sm(x): x = cl(x); return x * x * (3 - 2 * x)
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def lerp(a, b, u): return a + (b - a) * u
def keys(t, ks):
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            u = sm((t - t0) / (t1 - t0))
            if isinstance(v0, tuple): return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return lerp(v0, v1, u)
    return ks[-1][1]
def nz(t, s=0.0): return 0.5 * math.sin(t * 1.7 + s) + 0.3 * math.sin(t * 3.1 + s * 2.3) + 0.2 * math.sin(t * 7.3 + s * 1.1)
def shake(t, t0, dur, amp):
    if t < t0 or t > t0 + dur: return (0.0, 0.0)
    k = amp * (1 - (t - t0) / dur)
    return (k * math.sin(t * 83), k * math.sin(t * 67 + 1.3))
def hop(t, t0, dur=0.45, h=60):
    u = (t - t0) / dur
    if u < 0 or u > 1: return 0.0, 1.0, 1.0
    y = -h * math.sin(u * PI)
    sq = 1 + 0.18 * math.sin(u * PI * 2) if u > 0.5 else 1 - 0.12 * math.sin(u * PI)
    return y, 2 - sq, sq

class Cam:
    def __init__(s, x=W / 2, y=H / 2, z=1.0, rot=0.0): s.x, s.y, s.z, s.rot = x, y, z, rot
    def apply(s, c):
        c.translate(W / 2, H / 2); c.rotate(s.rot); c.scale(s.z, s.z); c.translate(-s.x, -s.y)

def grad(c, x0, y0, x1, y1, stops, gx=False):
    g = cairo.LinearGradient(x0, y0, x1 if gx else x0, y0 if gx else y1)
    for o, col in stops: g.add_color_stop_rgba(o, *(hexc(col) if isinstance(col, str) else col))
    c.set_source(g); c.rectangle(x0, y0, x1 - x0, y1 - y0); c.fill()

def poly(c, pts):
    c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    c.close_path()

# ------------------------------------------------------------------ elementos del mundo
RNG = random.Random(7)
CLOUDS = [(RNG.uniform(-1500, 3500), RNG.uniform(-200, 600), RNG.uniform(260, 520),
           [(RNG.uniform(-0.5, 0.5), RNG.uniform(-0.15, 0.05), RNG.uniform(0.14, 0.28)) for _ in range(9)]) for _ in range(22)]

def clouds(c, cam, t, top='#3A4658', bot='#1E2633', par=0.35, drift=12, alpha=1.0, yoff=0):
    c.save()
    for i, (x, y, w, blobs) in enumerate(CLOUDS):
        sx = (x + t * drift * (1 + i % 3) - cam.x * par) % 5000 - 1500
        sy = y + yoff - cam.y * par * 0.5 + 150
        c.new_path()
        for dx, dy, r in blobs:
            c.new_sub_path(); c.arc(sx + dx * w, sy + dy * w, r * w, 0, 2 * PI)
        g = cairo.LinearGradient(0, sy - 0.3 * w, 0, sy + 0.2 * w)
        g.add_color_stop_rgba(0, *hexc(top, alpha)); g.add_color_stop_rgba(1, *hexc(bot, alpha))
        c.set_source(g); c.fill()
    c.restore()

def wave_y(x, t, base, amp, k=0.006, sp=1.4, seed=0.0):
    return base + amp * (0.6 * math.sin(x * k + t * sp + seed) + 0.4 * math.sin(x * k * 2.3 - t * sp * 1.5 + seed * 2))

def sea_surface(c, t, x0, x1, base, amp, bottom, stops, foam=0.35, seed=0.0, k=0.006, sp=1.4):
    c.move_to(x0, bottom)
    pts = [(x, wave_y(x, t, base, amp, k, sp, seed)) for x in range(int(x0), int(x1) + 24, 24)]
    for p in pts: c.line_to(*p)
    c.line_to(x1, bottom); c.close_path()
    g = cairo.LinearGradient(0, base - amp, 0, bottom)
    for o, col in stops: g.add_color_stop_rgba(o, *hexc(col))
    c.set_source(g); c.fill()
    if foam > 0:
        c.set_source_rgba(1, 1, 1, foam); c.set_line_width(5)
        c.move_to(*pts[0])
        for p in pts[1:]: c.line_to(*p)
        c.stroke()

def giant_wave(c, t, x0, width, base, h):
    if h <= 1: return
    xc = x0 + width * 0.45
    lip = math.sin(t * 2.5) * 12
    c.move_to(x0 - 300, base + 40)
    c.curve_to(x0, base, xc - width * 0.25, base - h * 0.6, xc, base - h)
    c.curve_to(xc + width * 0.18, base - h * 1.05, xc + width * 0.32 + lip, base - h * 0.88, xc + width * 0.3 + lip, base - h * 0.68)
    c.curve_to(xc + width * 0.22, base - h * 0.8, xc + width * 0.15, base - h * 0.7, xc + width * 0.12, base - h * 0.55)
    c.curve_to(xc + width * 0.2, base - h * 0.25, xc + width * 0.45, base - 20, x0 + width + 300, base + 40)
    c.close_path()
    g = cairo.LinearGradient(0, base - h, 0, base)
    g.add_color_stop_rgba(0, *hexc('#3F8FA8')); g.add_color_stop_rgba(0.5, *hexc('#1D5873')); g.add_color_stop_rgba(1, *hexc('#0E2E44'))
    c.set_source(g); c.fill()
    c.set_source_rgba(1, 1, 1, 0.85)
    for i in range(14):
        a = i / 13
        fx = lerp(xc - width * 0.12, xc + width * 0.3 + lip, a)
        fy = base - h * (1.0 - 0.32 * a * a) + math.sin(t * 6 + i) * 6
        c.arc(fx, fy, 18 + 10 * math.sin(i * 1.7 + t * 4) ** 2, 0, 2 * PI); c.fill()
    c.set_source_rgba(1, 1, 1, 0.25); c.set_line_width(6)
    for i in range(4):
        yy = base - h * (0.25 + 0.15 * i)
        c.move_to(xc - width * 0.2 - i * 30, yy); c.curve_to(xc - 60, yy - 40, xc + 40, yy - 20, xc + 90, yy + 10); c.stroke()

def palm(c, x, y, s, t, lean=0.15):
    c.set_source_rgba(*hexc('#5B3A1E')); c.set_line_width(10 * s); c.set_line_cap(cairo.LINE_CAP_ROUND)
    tx, ty = x + lean * 120 * s, y - 120 * s
    c.move_to(x, y); c.curve_to(x, y - 60 * s, tx - 10 * s, ty + 40 * s, tx, ty); c.stroke()
    c.set_source_rgba(*hexc('#1F5E2E'))
    for i in range(6):
        a = -PI / 2 + (i - 2.5) * 0.55 + 0.05 * math.sin(t * 2 + i)
        c.move_to(tx, ty)
        c.curve_to(tx + math.cos(a - 0.4) * 50 * s, ty + math.sin(a - 0.4) * 50 * s, tx + math.cos(a) * 80 * s, ty + math.sin(a) * 80 * s + 25 * s,
                   tx + math.cos(a) * 95 * s, ty + math.sin(a) * 95 * s + 40 * s)
        c.curve_to(tx + math.cos(a) * 70 * s, ty + math.sin(a) * 70 * s + 30 * s, tx + math.cos(a + 0.3) * 40 * s, ty + math.sin(a + 0.3) * 40 * s, tx, ty)
        c.fill()

def island(c, x, y, s, t, fog=1.0):
    """Isla misteriosa: x,y = centro de la base."""
    c.set_source_rgba(*hexc('#D8C48E')); c.save(); c.translate(x, y); c.scale(560 * s, 60 * s); c.arc(0, 0, 1, 0, 2 * PI); c.restore(); c.fill()
    mts = [(-300, 330, '#1E4A2C'), (-80, 470, '#173B24'), (170, 380, '#1E4A2C'), (360, 250, '#245834')]
    for mx, mh, col in mts:
        c.set_source_rgba(*hexc(col))
        poly(c, [(x + (mx - 260) * s, y), (x + (mx - 70) * s, y - mh * 0.65 * s), (x + mx * s, y - mh * s), (x + (mx + 90) * s, y - mh * 0.7 * s), (x + (mx + 260) * s, y)]); c.fill()
        c.set_source_rgba(1, 1, 1, 0.07)
        poly(c, [(x + mx * s, y - mh * s), (x + (mx + 90) * s, y - mh * 0.7 * s), (x + (mx + 260) * s, y), (x + (mx + 60) * s, y)]); c.fill()
    # zona central oscura
    g = cairo.RadialGradient(x - 60 * s, y - 220 * s, 10 * s, x - 60 * s, y - 220 * s, 170 * s)
    g.add_color_stop_rgba(0, 0.02, 0.03, 0.04, 0.95); g.add_color_stop_rgba(1, 0.02, 0.03, 0.04, 0)
    c.set_source(g); c.arc(x - 60 * s, y - 220 * s, 170 * s, 0, 2 * PI); c.fill()
    for i, px in enumerate([-470, -420, 380, 440, 500]):
        palm(c, x + px * s, y - 10 * s, 0.9 * s, t + i, lean=0.2 if px < 0 else -0.2)
    # niebla
    for i in range(9):
        fx = x + ((i * 170 + t * 25) % 1300 - 650) * s; fy = y - (60 + (i % 3) * 90) * s
        g = cairo.RadialGradient(fx, fy, 0, fx, fy, 230 * s)
        g.add_color_stop_rgba(0, 0.85, 0.9, 0.95, 0.28 * fog); g.add_color_stop_rgba(1, 0.85, 0.9, 0.95, 0)
        c.set_source(g); c.arc(fx, fy, 230 * s, 0, 2 * PI); c.fill()

def lightning(c, x, y, length, seed, alpha=1.0, width=9):
    rng = random.Random(seed); pts = [(x, y)]; cx, cy = x, y
    while cy < y + length:
        cx += rng.uniform(-70, 70); cy += rng.uniform(40, 90); pts.append((cx, cy))
    for wdt, a in ((width * 4, 0.25), (width * 2, 0.5), (width, 1.0)):
        c.set_source_rgba(0.85, 0.92, 1, a * alpha); c.set_line_width(wdt); c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.move_to(*pts[0])
        for p in pts[1:]: c.line_to(*p)
        c.stroke()

def rain(c, t, alpha=0.35, n=140, ang=0.25, seed=3):
    rng = random.Random(seed)
    c.set_source_rgba(0.8, 0.88, 1, alpha); c.set_line_width(3)
    for i in range(n):
        x = rng.uniform(-200, W + 200); sp = rng.uniform(1800, 2600); ph = rng.uniform(0, 1)
        y = ((t * sp / H + ph) % 1.0) * (H + 300) - 150
        x2 = x - ang * 300 * (t * sp / H % 1) * 0
        c.move_to(x2, y); c.line_to(x2 - ang * 70, y + 70); c.stroke()

BUB = [(RNG.uniform(-200, 1400), RNG.uniform(0, 1), RNG.uniform(60, 180), RNG.uniform(4, 16)) for _ in range(70)]
def bubbles(c, t, x0, y_top, y_bot, alpha=0.5):
    for bx, ph, sp, r in BUB:
        span = y_bot - y_top
        y = y_bot - ((t * sp + ph * span) % span)
        x = x0 + bx + math.sin(t * 2 + ph * 10) * 12
        c.set_source_rgba(0.8, 0.95, 1, alpha * 0.6); c.set_line_width(2.5); c.arc(x, y, r, 0, 2 * PI); c.stroke()
        c.set_source_rgba(1, 1, 1, alpha * 0.6); c.arc(x - r * 0.35, y - r * 0.35, r * 0.25, 0, 2 * PI); c.fill()

def fish(c, x, y, s, flip, col='#F2B544'):
    c.save(); c.translate(x, y); c.scale(-s if flip else s, s)
    c.set_source_rgba(*hexc(col)); c.save(); c.scale(26, 13); c.arc(0, 0, 1, 0, 2 * PI); c.restore(); c.fill()
    poly(c, [(20, 0), (40, -14), (40, 14)]); c.fill()
    c.set_source_rgba(0, 0, 0, 1); c.arc(-12, -3, 3, 0, 2 * PI); c.fill()
    c.restore()

def god_rays(c, t, x0, x1, y0, length, alpha=0.08):
    for i in range(9):
        x = lerp(x0, x1, i / 8) + math.sin(t * 0.6 + i) * 40
        wdt = 60 + 40 * math.sin(i * 2.1)
        g = cairo.LinearGradient(0, y0, 0, y0 + length)
        g.add_color_stop_rgba(0, 0.9, 0.97, 1, alpha); g.add_color_stop_rgba(1, 0.9, 0.97, 1, 0)
        c.set_source(g); poly(c, [(x - wdt * 0.3, y0), (x + wdt * 0.3, y0), (x + wdt * 1.4 + 200, y0 + length), (x - wdt * 0.6 + 200, y0 + length)]); c.fill()

def creature_shadow(c, x, y, s, t, alpha):
    """Silueta enorme sin revelar: cuerpo largo, aletas y cola ondulante, bordes suaves."""
    if alpha <= 0: return
    for k, a in ((1.12, 0.18), (1.06, 0.3), (1.0, 0.75)):
        c.save(); c.translate(x, y); c.scale(s * k, s * k)
        w = math.sin(t * 1.3) * 0.12
        c.move_to(-520, 0)
        c.curve_to(-480, -130, -150, -170, 120, -120)
        c.curve_to(300, -90, 420, -40 + 60 * w, 560, -120 + 140 * w)
        c.line_to(600, 20 + 140 * w)
        c.curve_to(470, 30 + 60 * w, 320, 90, 120, 110)
        c.curve_to(-120, 150, -440, 120, -520, 0)
        c.close_path()
        c.move_to(-120, 60); c.curve_to(-60, 200, 40, 230, 80, 200); c.curve_to(40, 150, 0, 100, -40, 80); c.close_path()
        c.move_to(-60, -140); c.curve_to(0, -260, 80, -250, 120, -230); c.curve_to(90, -180, 60, -150, 40, -130); c.close_path()
        c.restore()
        c.set_source_rgba(0.0, 0.03, 0.07, alpha * a); c.fill()

# ------------------------------------------------------------------ mundo costa (escenas 1, 2, 4 y 5)
SURF = 1550; HORIZON = 1060; SHORE = 950

def coast_world(c, t, cam, mood='storm', island_at=None, giant=0.0, ripples=0.0, shadow=None, flash=0.0):
    sky = {'storm': ('#141B27', '#4B5A6E'), 'overcast': ('#24344A', '#7F93A8'), 'dusk': ('#0D1522', '#33465E')}[mood]
    grad(c, 0, 0, W, H, [(0, sky[0]), (1, sky[1])])
    clouds(c, cam, t, top='#4A5870' if mood != 'storm' else '#353F52', bot='#222B3A', par=0.3)
    c.save(); cam.apply(c)
    # mar lejano
    grad(c, -4000, HORIZON, 6000, SURF + 50, [(0, '#2B465E'), (1, '#173149')])
    c.set_source_rgba(1, 1, 1, 0.12); c.set_line_width(3)
    for i in range(10):
        yy = HORIZON + 30 + i * 45
        for j in range(30):
            xx = (j * 330 + i * 97 + t * (20 + i * 4)) % 9000 - 3500
            c.move_to(xx, yy); c.line_to(xx + 60 + i * 6, yy); c.stroke()
    if island_at is not None:
        island(c, island_at[0], island_at[1], island_at[2], t)
    giant_wave(c, t, 820, 1300, SURF + 20, giant)
    # agua (sección) con superficie ondulada
    sea_surface(c, t, SHORE - 200, 6000, SURF, 22 + 10 * (mood == 'storm'), 4200,
                [(0, '#2A6E8F'), (0.18, '#1A4C6B'), (0.6, '#08243A'), (1, '#020B14')], foam=0.45, seed=1.0)
    god_rays(c, t, 1100, 3400, SURF + 30, 1700, alpha=0.06)
    if shadow is not None:
        creature_shadow(c, shadow[0], shadow[1], shadow[2], t, shadow[3])
    if ripples > 0:
        for i in range(4):
            r = ((t * 120 + i * 90) % 360)
            c.set_source_rgba(1, 1, 1, ripples * 0.5 * (1 - r / 360)); c.set_line_width(4)
            c.save(); c.translate(1500, SURF); c.scale(1, 0.18); c.arc(0, 0, 80 + r, 0, 2 * PI); c.restore(); c.stroke()
    # playa (con su sección de tierra)
    c.move_to(-4000, SURF)
    for x in range(-4000, SHORE, 60): c.line_to(x, SURF + 6 * math.sin(x * 0.01))
    c.curve_to(SHORE + 80, SURF + 10, SHORE + 220, SURF + 120, SHORE + 380, SURF + 380)
    c.line_to(SHORE + 700, 4200); c.line_to(-4000, 4200); c.close_path()
    g = cairo.LinearGradient(0, SURF, 0, SURF + 900)
    g.add_color_stop_rgba(0, *hexc('#D9C08A')); g.add_color_stop_rgba(0.08, *hexc('#B99B66')); g.add_color_stop_rgba(1, *hexc('#4A3A28'))
    c.set_source(g); c.fill()
    c.set_source_rgba(*hexc('#6E6658'))
    for (rx, ry, rr) in [(-500, SURF + 10, 70), (-380, SURF + 25, 45), (1020, SURF + 70, 55), (60, SURF + 18, 30)]:
        poly(c, [(rx - rr, ry + 10), (rx - rr * 0.6, ry - rr * 0.7), (rx + rr * 0.4, ry - rr * 0.85), (rx + rr, ry + 10)]); c.fill()
    c.set_source_rgba(*hexc('#4E7A3A')); c.set_line_width(6)
    for gx in (-700, -260, 120, 480):
        for k in range(5):
            c.move_to(gx + k * 9, SURF + 4); c.line_to(gx + k * 9 + (k - 2) * 8 + 5 * math.sin(t * 3 + k), SURF - 30 - k % 2 * 10); c.stroke()
    c.restore()
    if flash > 0:
        c.set_source_rgba(0.9, 0.95, 1, flash); c.paint()

def post(c, tint=None, vign=0.55):
    if tint: c.set_source_rgba(*tint); c.paint()
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.72)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, vign)
    c.set_source(g); c.paint()

# ------------------------------------------------------------------ ESCENA 1 — el desafío
def scene1(c, t):
    cam = Cam()
    if t < 1.5: cam.x, cam.y, cam.z = keys(t, [(0, (1900.0, 1050.0, 0.55)), (1.5, (1750.0, 1150.0, 0.62))])
    elif t < 3.0: cam.x, cam.y, cam.z = keys(t, [(1.5, (1750.0, 1150.0, 0.62)), (3.0, (430.0, 1400.0, 1.35))])
    elif t < 4.6: cam.x, cam.y, cam.z = keys(t, [(3.0, (430.0, 1400.0, 1.35)), (4.6, (460.0, 1400.0, 1.42))])
    else: cam.x, cam.y, cam.z = keys(t, [(4.6, (460.0, 1400.0, 1.42)), (5.6, (980.0, 1050.0, 0.74)), (6.8, (1010.0, 1070.0, 0.76))])
    dx, dy = shake(t, 4.9, 1.2, 28); cam.x += dx / cam.z; cam.y += dy / cam.z
    gw = 1050 * eo((t - 4.6) / 1.0)
    fl = max(0.0, 1 - abs(t - 4.75) * 6) * 0.6 + max(0.0, 1 - abs(t - 1.0) * 8) * 0.5
    coast_world(c, t, cam, 'storm', giant=gw, flash=0)
    c.save(); cam.apply(c)
    if 0.8 < t < 1.2: lightning(c, 2300, 300, 700, 5, alpha=1 - abs(t - 1.0) * 5)
    if 4.6 < t < 5.0: lightning(c, 1300, 250, 750, 9, alpha=1 - abs(t - 4.75) * 4)
    wave_hit = sm((t - 4.7) / 0.3)
    cast = [('arg', 60), ('usa', 230), ('mex', 420), ('bra', 600), ('can', 770)]
    for i, (code, x) in enumerate(cast):
        r = 72; y = SURF - r
        hy, sx, sy = hop(t, 4.9 + i * 0.05, 0.5, 70) if code not in ('usa',) else (0, 1, 1)
        bl = 1.0 if (t * 0.7 + i * 0.37) % 3.1 < 0.07 else 0.0
        if code == 'usa':
            ball(c, code, x, y, r, 'smug', look=(0.7, -0.2), glasses=1.0, mouth='smirk' if t > 3.4 else None)
        elif code == 'mex':
            ex = 'surprised' if wave_hit > 0.5 else 'worried'
            ball(c, code, x, y + hy, r, ex, look=(0.9, -0.6 * wave_hit), sx=sx, sy=sy, blink=bl, mouth='o' if wave_hit > 0.5 else None)
        else:
            ex = 'scared' if wave_hit > 0.5 else 'worried'
            ball(c, code, x, y + hy, r, ex, look=(0.9, -0.4 * wave_hit), sx=sx, sy=sy, blink=bl, sweat=wave_hit)
    c.restore()
    rain(c, t, 0.3)
    if fl > 0: c.set_source_rgba(0.92, 0.96, 1, fl); c.paint()
    post(c, (0.05, 0.1, 0.2, 0.12))

# ------------------------------------------------------------------ ESCENA 2 — la misión / la isla
S2CAST = [('usa', 150), ('mex', 360), ('bra', 570), ('arg', 780), ('col', 990), ('can', 1180), ('per', 1360), ('chi', 1530)]
S2NAME = {'usa': 7.0, 'mex': 7.89, 'bra': 8.33, 'arg': 8.77, 'col': 9.38}

def scene2(c, t):
    g = t + T['s2']
    if g < T['isla']:
        cam = Cam()
        focus = [(7.0, 150), (7.89, 360), (8.33, 570), (8.77, 780), (9.38, 990)]
        fx = 150
        for tt, x in focus:
            if g >= tt - 0.15: fx = x
        prev = [x for tt, x in focus if g >= tt - 0.15]
        if g < 9.95:
            # pan rápido entre personajes
            idx = len(prev) - 1
            t0 = focus[max(idx, 0)][0] - 0.15
            x0 = focus[max(idx - 1, 0)][1]; x1 = focus[max(idx, 0)][1]
            cam.x = lerp(x0, x1, eo((g - t0) / 0.3)); cam.y = SURF - 200; cam.z = 1.75
        else:
            u = sm((g - 9.95) / 1.1)
            cam.x = lerp(990, 1500, u); cam.y = lerp(SURF - 200, 1300, u); cam.z = lerp(1.75, 0.62, u)
        coast_world(c, g, cam, 'overcast', island_at=(2700, 1110, 0.55))
        c.save(); cam.apply(c)
        for code, x in S2CAST:
            r = 78; y = SURF - r
            hy, sx, sy = hop(g, S2NAME.get(code, 9.9 + x * 0.0004), 0.42, 55)
            look = (0.85, -0.25)
            if code == 'usa':
                ball(c, code, x, y + hy, r, 'smug', look=look, rot=-0.12, sx=sx, sy=sy, glasses=1.0, mouth='smirk')
            elif code == 'mex':
                ball(c, code, x, y + hy, r, 'normal', look=(1.0, -0.4), rot=0.12 * math.sin(g * 2), sx=sx, sy=sy)
            elif code == 'bra':
                b = abs(math.sin(g * 7)) * 22
                ball(c, code, x, y - b + hy, r, 'happy', look=look, sx=sx, sy=sy, mouth='smile')
            elif code == 'arg':
                ball(c, code, x, y + hy, r, 'smug', look=look, rot=-0.18, sx=sx, sy=sy)
            elif code == 'col':
                ball(c, code, x, y + hy, r, 'sly', look=(1.0, -0.2), sx=sx, sy=sy)
            else:
                ball(c, code, x, y + hy, r, 'normal', look=look, sx=sx, sy=sy, blink=1.0 if (g * 1.3 + x) % 2.7 < 0.08 else 0)
        c.restore()
        post(c, (0.05, 0.1, 0.2, 0.08))
    else:
        u = g - T['isla']
        grad(c, 0, 0, W, H, [(0, '#1D2C42'), (0.5, '#6E8399'), (0.52, '#2C4C66'), (1, '#0D2236')])
        cam = Cam(540, 1100, lerp(0.9, 1.9, sm(u / 2.7)))
        cam.y = lerp(1100, 860, sm(u / 2.7))
        clouds(c, cam, g, top='#56667E', bot='#2A3548', par=0.2, alpha=0.9, yoff=-200)
        c.save(); cam.apply(c)
        c.set_source_rgba(1, 1, 1, 0.12); c.set_line_width(3)
        for i in range(30):
            yy = 980 + i * 35
            for j in range(12):
                xx = (j * 240 + i * 77 + g * 30) % 2600 - 800
                c.move_to(xx, yy); c.line_to(xx + 50 + i * 3, yy); c.stroke()
        island(c, 540, 1000, 1.0, g, fog=1.2)
        c.restore()
        post(c, (0.03, 0.06, 0.12, 0.15), vign=0.7)

# ------------------------------------------------------------------ barco
def ship(c, x, y, ang, s, t, crew):
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    # mástil y vela
    c.set_source_rgba(*hexc('#5A3A1E')); c.rectangle(-12, -560, 24, 560); c.fill()
    bil = 40 + 25 * math.sin(t * 5)
    c.move_to(-10, -540); c.curve_to(120 + bil, -470, 140 + bil, -250, -10, -170); c.close_path()
    c.set_source_rgba(*hexc('#E8DDC0')); c.fill_preserve(); c.set_source_rgba(0, 0, 0, 0.6); c.set_line_width(5); c.stroke()
    c.move_to(-14, -500); c.curve_to(-170 - bil * 0.6, -440, -190 - bil * 0.6, -260, -14, -200); c.close_path()
    c.set_source_rgba(*hexc('#DCCFAE')); c.fill_preserve(); c.set_source_rgba(0, 0, 0, 0.6); c.stroke()
    c.set_source_rgba(*hexc('#C0392B')); poly(c, [(12, -560), (90 + 20 * math.sin(t * 9), -545), (12, -525)]); c.fill()
    # tripulación sobre cubierta (y = 0 es la cubierta)
    for args in crew: ball(c, *args[0], **args[1])
    # casco
    c.move_to(-420, 0); c.line_to(420, 0); c.curve_to(400, 90, 330, 170, 260, 190); c.line_to(-280, 190); c.curve_to(-360, 160, -410, 90, -420, 0); c.close_path()
    g = cairo.LinearGradient(0, 0, 0, 190); g.add_color_stop_rgba(0, *hexc('#8A5A30')); g.add_color_stop_rgba(1, *hexc('#4E2F16'))
    c.set_source(g); c.fill_preserve(); c.set_source_rgba(0, 0, 0, 1); c.set_line_width(7); c.stroke()
    c.set_source_rgba(0, 0, 0, 0.35); c.set_line_width(4)
    for yy in (45, 90, 135):
        c.move_to(-400 + yy * 0.4, yy); c.line_to(400 - yy * 0.5, yy); c.stroke()
    c.set_source_rgba(*hexc('#6B4423')); c.rectangle(-430, -22, 860, 24); c.fill()
    for i in range(5):
        c.set_source_rgba(*hexc('#2D2016')); c.arc(-250 + i * 125, 70, 16, 0, 2 * PI); c.fill()
    c.restore()

def scene3a(c, t):
    g = t + T['s3a']
    cam = Cam(540, 1050, 0.9)
    if t > 3.0:
        u = eo((t - 3.0) / 0.6); cam.x = lerp(540, 330, u); cam.y = lerp(1050, 760, u); cam.z = lerp(0.9, 1.25, u)
    dx, dy = shake(t, 3.0, 1.6, 26); cam.x += dx; cam.y += dy
    grad(c, 0, 0, W, H, [(0, '#0F1622'), (1, '#3A4A5E')])
    clouds(c, cam, g, top='#2E384A', bot='#151C28', par=0.4, drift=40)
    fl = max(0.0, 1 - abs(t - 1.2) * 7) * 0.55
    c.save(); cam.apply(c)
    if 1.05 < t < 1.35: lightning(c, 820, 50, 650, 21, alpha=1)
    sea_surface(c, g, -800, 2000, 1080, 60, 2600, [(0, '#2C5F7A'), (1, '#0A1B29')], foam=0.4, seed=3, k=0.004, sp=2.0)
    gw = 900 * eo((t - 2.6) / 1.3)
    giant_wave(c, g, -900, 1100, 1250, gw)
    # barco sube y baja
    by = wave_y(540, g, 1230, 70, 0.004, 2.0, 1.0) - 20
    ang = 0.2 * math.sin(g * 2.0) + 0.08 * math.sin(g * 3.7)
    crew = []
    for code, x in (('mex', -280), ('col', -130), ('per', 210)):
        crew.append(((code, x, -52, 52, 'scared'), dict(look=(-0.8, -0.3) if t > 2.6 else (0.5, 0.0), sweat=1.0, shadow=False,
                                                       sy=1 + 0.05 * math.sin(g * 9 + x), mouth='o' if t > 3.0 else 'wavy')))
    roll = keys(t, [(0, 0.0), (1.4, 0.0), (2.2, 330.0), (3.0, 250.0), (3.7, -330.0), (4.8, -200.0)])
    crew.append((('can', roll, -52, 52, 'scared'), dict(rot=roll / 52.0, sweat=1.0, shadow=False, mouth='shout')))
    ship(c, 600, by, ang, 0.95, g, crew)
    sea_surface(c, g + 0.4, -800, 2000, 1320, 45, 2600, [(0, '#24546E'), (1, '#071521')], foam=0.5, seed=5, k=0.005, sp=2.3)
    c.restore()
    rain(c, g, 0.38, n=170)
    if fl > 0: c.set_source_rgba(0.92, 0.96, 1, fl); c.paint()
    post(c, (0.02, 0.06, 0.15, 0.15))

# ------------------------------------------------------------------ avión
def plane(c, x, y, ang, s, t, light_on):
    c.save(); c.translate(x, y); c.rotate(ang); c.scale(s, s)
    c.set_source_rgba(*hexc('#9AA4B0')); poly(c, [(-60, 20), (140, 20), (40, 230), (-60, 230)]); c.fill()     # ala trasera (al fondo)
    c.move_to(-520, -40); c.curve_to(-560, -40, -580, 40, -520, 50); c.line_to(420, 60)
    c.curve_to(520, 55, 560, 10, 560, -10); c.curve_to(540, -60, 470, -70, 420, -70); c.line_to(-480, -70); c.close_path()
    g = cairo.LinearGradient(0, -70, 0, 60); g.add_color_stop_rgba(0, *hexc('#FFFFFF')); g.add_color_stop_rgba(1, *hexc('#B7C1CC'))
    c.set_source(g); c.fill_preserve(); c.set_source_rgba(0, 0, 0, 1); c.set_line_width(6); c.stroke()
    c.set_source_rgba(*hexc('#2D6FB5')); c.rectangle(-500, 5, 960, 16); c.fill()
    poly(c, [(-470, -70), (-560, -230), (-470, -230), (-380, -70)]); c.set_source_rgba(*hexc('#2D6FB5')); c.fill()
    codes = ['usa', 'arg', 'bra', 'chi', 'per', 'mex']
    for i in range(8):
        wx = -330 + i * 95
        c.set_source_rgba(*hexc('#BFE3FF')); c.arc(wx, -25, 22, 0, 2 * PI); c.fill()
        if i < 6:
            c.save(); c.arc(wx, -25, 21, 0, 2 * PI); c.clip()
            ball(c, codes[i], wx, -20 + 3 * math.sin(t * 20 + i), 16, 'scared', shadow=False); c.restore()
        c.set_source_rgba(0, 0, 0, 1); c.set_line_width(4); c.arc(wx, -25, 22, 0, 2 * PI); c.stroke()
    c.set_source_rgba(*hexc('#7E8996')); poly(c, [(-80, 30), (160, 30), (0, 260), (-120, 260)]); c.fill()
    c.set_source_rgba(0, 0, 0, 1); c.set_line_width(5); poly(c, [(-80, 30), (160, 30), (0, 260), (-120, 260)]); c.stroke()
    c.set_source_rgba(*hexc('#59636F')); c.rectangle(-40, 120, 110, 50); c.fill()
    if light_on:
        c.set_source_rgba(1, 0.2, 0.2, 1); c.arc(-60, 260, 10, 0, 2 * PI); c.fill()
    c.restore()

def scene3b(c, t):
    g = t + T['s3b']
    if g < T['cabina']:
        cam = Cam(540, 960, 1.0)
        dx, dy = shake(t, 0.5, 0.6, 18); cam.x += dx; cam.y += dy
        grad(c, 0, 0, W, H, [(0, '#0A0F1A'), (1, '#273347')])
        clouds(c, cam, g, top='#2B3446', bot='#131925', par=1.0, drift=-600)
        flashes = [0.45, 1.3, 1.75]
        fl = sum(max(0.0, 1 - abs(t - f) * 7) for f in flashes) * 0.5
        c.save(); cam.apply(c)
        for f, sd, lx in zip(flashes, (31, 32, 33), (300, 820, 180)):
            if abs(t - f) < 0.15: lightning(c, lx, 150, 900, sd)
        turb = 0.06 * math.sin(g * 11) + 0.04 * math.sin(g * 17)
        plane(c, lerp(560, 520, t / 2.2), 940 + 30 * math.sin(g * 9), turb, 0.95, g, (g * 4) % 1 < 0.5)
        c.restore()
        for i in range(10):
            cx_ = ((i * 260 - g * 2200) % (W + 1600)) - 600; cy_ = 300 + (i * 397) % 1300
            c.set_source_rgba(0.75, 0.8, 0.9, 0.35); c.save(); c.translate(cx_, cy_); c.scale(260, 90); c.arc(0, 0, 1, 0, 2 * PI); c.restore(); c.fill()
        rain(c, g, 0.4, n=180, seed=8)
        if fl > 0: c.set_source_rgba(0.92, 0.96, 1, min(0.8, fl)); c.paint()
        post(c, (0.02, 0.05, 0.12, 0.12))
    else:
        u = g - T['cabina']
        sh = 14 * math.sin(g * 23) + 9 * math.sin(g * 31)
        c.save(); c.translate(sh, sh * 0.6)
        grad(c, -50, -50, W + 50, H + 50, [(0, '#3B4250'), (1, '#1C212B')])
        flash = max(0.0, 1 - abs(u - 0.5) * 6)
        for wx in (130, 950):
            for wy in (620, 1120):
                c.set_source_rgba(*hexc('#0D1424')); c.save(); c.translate(wx, wy); c.scale(85, 120); c.arc(0, 0, 1, 0, 2 * PI); c.restore(); c.fill()
                c.set_source_rgba(0.85, 0.9, 1, 0.8 * flash); c.save(); c.translate(wx, wy); c.scale(85, 120); c.arc(0, 0, 1, 0, 2 * PI); c.restore(); c.fill()
                c.set_source_rgba(*hexc('#C7CDD6')); c.set_line_width(14); c.save(); c.translate(wx, wy); c.scale(85, 120); c.arc(0, 0, 1, 0, 2 * PI); c.restore(); c.stroke()
        # panel con luz de combustible
        c.set_source_rgba(*hexc('#14181F')); c.rectangle(300, 250, 480, 170); c.fill()
        c.set_source_rgba(*hexc('#5B6470')); c.set_line_width(8); c.rectangle(300, 250, 480, 170); c.stroke()
        on = u > 0.7 and (u * 3) % 1 < 0.55
        gx, gy = 440, 335
        c.set_source_rgba(1, 0.75, 0.2, 1); c.rectangle(gx - 30, gy - 30, 44, 62); c.fill()
        c.rectangle(gx + 14, gy - 12, 18, 8); c.fill(); c.rectangle(gx + 26, gy - 12, 8, 34); c.fill()
        c.set_source_rgba(0, 0, 0, 1); c.rectangle(gx - 22, gy - 22, 28, 18); c.fill()
        lc = (1, 0.15, 0.1) if on else (0.35, 0.08, 0.08)
        if on:
            gr = cairo.RadialGradient(640, 335, 10, 640, 335, 130); gr.add_color_stop_rgba(0, 1, 0.2, 0.1, 0.8); gr.add_color_stop_rgba(1, 1, 0.2, 0.1, 0)
            c.set_source(gr); c.arc(640, 335, 130, 0, 2 * PI); c.fill()
        c.set_source_rgba(*lc, 1); c.arc(640, 335, 42, 0, 2 * PI); c.fill()
        c.set_source_rgba(0, 0, 0, 1); c.set_line_width(5); c.arc(640, 335, 42, 0, 2 * PI); c.stroke()
        c.set_source_rgba(0.6, 0.65, 0.7, 1)
        for i in range(5): c.arc(330 + i * 0 + 20, 285 + i * 0, 0, 0, 0)
        # asientos y pasajeros
        seats = [(250, 1450, 'usa', 1), (540, 1450, 'arg', -1), (830, 1450, 'bra', -1)]
        for i, (sx, sy, code, side) in enumerate(seats):
            c.set_source_rgba(*hexc('#2C4E8A')); c.move_to(sx - 135, sy + 260); c.line_to(sx - 135, sy - 150)
            c.curve_to(sx - 135, sy - 260, sx + 135, sy - 260, sx + 135, sy - 150); c.line_to(sx + 135, sy + 260); c.close_path(); c.fill()
            c.set_source_rgba(*hexc('#E9ECF2')); c.rectangle(sx - 90, sy - 230, 180, 50); c.fill()
            look = (0.0, -1.0)
            if u > 1.3:
                look = (side * 1.0, 0.0) if (u * 2.2 + i) % 2 < 1 else (-side * 1.0, -0.2)
            bob = 10 * math.sin(g * 25 + i)
            ball(c, code, sx, sy + bob, 115, 'scared', look=look, sweat=1.0, shadow=False, mouth='wavy' if i != 1 else 'o',
                 glasses=0.0)
            c.set_source_rgba(*hexc('#21396A')); c.rectangle(sx - 150, sy + 120, 300, 150); c.fill()
        c.set_source_rgba(*hexc('#9BA3AE')); c.rectangle(-60, 1700, W + 120, 40); c.fill()
        c.restore()
        if u > 0.7 and on:
            c.set_source_rgba(1, 0.1, 0.05, 0.12); c.paint()
        post(c, None, 0.6)

# ------------------------------------------------------------------ ESCENA 3C — bajo el agua
def scene3c(c, t):
    g = t + T['s3c']
    cam = Cam(540, keys(t, [(0, 700.0), (2.2, 1250.0), (4.6, 1500.0)]), keys(t, [(0, 1.1), (2.2, 0.95), (4.6, 1.15)]))
    grad(c, 0, 0, W, H, [(0, '#0B3A5E'), (1, '#020C17')])
    c.save(); cam.apply(c)
    grad(c, -2000, -400, 3000, 4000, [(0, '#2F86B8'), (0.25, '#155A86'), (0.6, '#062A47'), (1, '#01070F')])
    c.set_source_rgba(0.85, 0.95, 1, 0.5); c.set_line_width(6)
    c.move_to(-1000, wave_y(-1000, g, 120, 14))
    for x in range(-1000, 2100, 30): c.line_to(x, wave_y(x, g, 120, 14))
    c.stroke()
    god_rays(c, g, -200, 1300, 120, 1900, alpha=0.1)
    sha = sm((t - 1.6) / 1.4)
    creature_shadow(c, 560 + 140 * math.sin(g * 0.35), 2050, 1.25, g, sha)
    for i in range(8):
        fx = (i * 150 + g * 90) % 1600 - 300; fy = 900 + 60 * math.sin(i * 1.3 + g)
        fish(c, fx, fy, 0.9, False, '#F2B544' if i % 2 else '#7DD3E8')
    bubbles(c, g, -100, 150, 1900, 0.5)
    stop = sm((t - 2.3) / 0.5)
    cast = [('mex', 230, 0), ('chi', 430, 1), ('per', 640, 2), ('col', 850, 3)]
    for code, x, i in cast:
        sw = (1 - stop)
        y = 760 + 30 * math.sin(g * 3 + i) * sw + i % 2 * 40
        rot = 0.15 * math.sin(g * 4 + i) * sw
        look = (0.6 * math.sin(g + i), 0.2) if stop < 0.5 else (0.0, 1.0)
        ex = 'determined' if stop < 0.5 else 'scared'
        ball(c, code, x + 15 * math.sin(g * 2 + i) * sw, y, 70, ex, look=look, rot=rot, shadow=False, sweat=stop,
             mouth='o' if stop > 0.5 else None)
        for k in range(3):
            by = y - 80 - ((g * 160 + k * 60 + i * 33) % 220)
            c.set_source_rgba(0.85, 0.95, 1, 0.6); c.set_line_width(2.5); c.arc(x + 30 + 8 * math.sin(g * 5 + k), by, 7 + k * 2, 0, 2 * PI); c.stroke()
    c.restore()
    post(c, (0.0, 0.08, 0.18, 0.18), vign=0.75)

# ------------------------------------------------------------------ ESCENA 4 — la discusión
S4POS = {'arg': 120, 'usa': 290, 'bra': 450, 'can': 610, 'col': 760, 'mex': 900}

def shot4(g):
    shots = [(28.6, 31.0, (500.0, 1330.0, 1.05), (520.0, 1350.0, 1.15)),
             (31.0, 32.3, (300.0, 1380.0, 1.6), (300.0, 1380.0, 1.75)),
             (32.3, 33.6, (150.0, 1400.0, 2.1), (160.0, 1400.0, 2.25)),
             (33.6, 35.2, (450.0, 1410.0, 2.4), (450.0, 1410.0, 2.6)),
             (35.2, 36.2, (610.0, 1410.0, 2.3), (610.0, 1410.0, 2.45)),
             (36.2, 37.2, (790.0, 1380.0, 2.0), (820.0, 1370.0, 2.1)),
             (37.2, 40.4, (760.0, 1360.0, 1.25), (900.0, 1440.0, 3.0))]
    for a, b, p0, p1 in shots:
        if a <= g < b:
            u = (g - a) / (b - a)
            if b == 40.4: u = sm(u) ** 1.3
            x, y, z = (lerp(p0[i], p1[i], u) for i in range(3))
            return Cam(x, y, z)
    return Cam(500, 1330, 1.05)

def scene4(c, t):
    g = t + T['s4']
    cam = shot4(g)
    coast_world(c, g, cam, 'overcast')
    c.save(); cam.apply(c)
    r = 72
    for code, x0 in S4POS.items():
        x = x0; y = SURF - r; ex = 'angry'; look = (0.0, 0.0); mouth = None; kw = {}
        if g < 31.0:
            hy, sx, sy = hop(g, 28.7 + (x0 % 7) * 0.12, 0.35, 40)
            hy2, _, _ = hop(g, 29.9 + (x0 % 5) * 0.1, 0.35, 35)
            y += hy + hy2; kw = dict(sx=sx, sy=sy)
            mouth = 'shout' if int(g * 5 + x0) % 2 else None
            look = (math.sin(g * 3 + x0), 0)
            if code == 'can': ex = 'worried'; mouth = 'wavy'
            if code == 'bra': ex = 'sly'; mouth = 'smirk'
            if code == 'usa': ex = 'smug'; kw['glasses'] = 1.0
        else:
            if code == 'usa':
                x = lerp(x0, 230, sm((g - 31.0) / 0.5)); ex = 'smug'; kw['glasses'] = 1.0; mouth = 'smirk'; look = (0.4, -0.3)
                kw['rot'] = -0.12
            elif code == 'arg':
                ex = 'angry'; mouth = 'shout'; look = (1.0, 0.0)
                x = x0 + 6 * math.sin(g * 40); hy, _, _ = hop(g, 32.4, 0.3, 30); y += hy
            elif code == 'bra':
                ex = 'sly'; mouth = 'smirk'; look = (-1.0, 0.1) if g < 34.6 else (1.0, 0.1)
            elif code == 'can':
                ex = 'worried'; mouth = 'wavy'; kw['sweat'] = 1.0; x = x0 + 4 * math.sin(g * 50); look = (-0.6, 0)
            elif code == 'col':
                ex = 'normal'; look = (1.0, -0.2)
            elif code == 'mex':
                if g < 37.2: ex = 'normal'; look = (-0.8, 0)
                else:
                    surprised = sm((g - 38.6) / 0.25)
                    ex = 'surprised' if surprised > 0.5 else 'normal'; look = (1.0, 0.5 * surprised)
                    mouth = 'o' if surprised > 0.5 else None
                    kw['sy'] = 1 + 0.08 * surprised; kw['sx'] = 1 - 0.05 * surprised
        ball(c, code, x, y, r, ex, look=look, mouth=mouth, **kw)
    c.restore()
    if g > 38.6:
        dx, dy = shake(g, 38.6, 0.8, 10)
        c.translate(dx, dy)
    post(c, (0.05, 0.1, 0.2, 0.06))

# ------------------------------------------------------------------ ESCENA 5 — el misterio bajo el agua
def scene5(c, t):
    g = t + T['s5']
    sh_x = 1700 + 160 * math.sin(g * 0.3); sh_y = 2500
    sh_alpha = sm((g - 43.0) / 2.0)
    react = None
    if g < 43.0:
        cam = Cam(lerp(860, 980, sm(t / 2.6)), 1420, lerp(2.2, 1.9, sm(t / 2.6)))
    elif g < 47.5:
        u = sm((g - 43.0) / 4.5)
        cam = Cam(lerp(980, 1500, u), lerp(1420, 2250, u), lerp(1.9, 0.75, u))
    elif g < 50.0:
        shots = [(47.5, 48.35, 'usa', 290), (48.35, 49.2, 'bra', 450), (49.2, 50.0, 'can', 610)]
        for a, b, code, x in shots:
            if a <= g < b:
                react = code; cam = Cam(x, SURF - 80, lerp(2.6, 2.8, (g - a) / (b - a)))
    else:
        u = (g - 50.0) / 5.0
        cam = Cam(lerp(1550, sh_x - 150, sm(u)), lerp(2300, sh_y - 60, sm(u)), lerp(0.85, 1.6, u * u))
        cam.x += 8 * math.sin(g * 20) * u; cam.y += 8 * math.sin(g * 17) * u
    coast_world(c, g, cam, 'dusk', ripples=sm((g - 43.5) / 1.0), shadow=(sh_x, sh_y, 2.2, sh_alpha))
    c.save(); cam.apply(c)
    r = 72
    for code, x0 in S4POS.items():
        y = SURF - r; ex = 'worried'; mouth = None; kw = {}; look = (1.0, 0.3)
        if code == 'mex':
            ex = 'scared'; kw['sweat'] = 1.0; look = (0.9, 0.9); mouth = 'o'
            x0 = 900 + 3 * math.sin(g * 30)
        elif code == 'usa':
            off = g >= 47.7
            ex = 'surprised' if off else 'smug'; kw['glasses'] = 0.0 if off else 1.0
            mouth = 'line' if off else 'smirk'
        elif code == 'bra':
            ex = 'sly'; look = (1.0, 0.4)
        elif code == 'can':
            ex = 'scared'; kw['sweat'] = 1.0; mouth = 'wavy'; x0 = x0 + 4 * math.sin(g * 45)
        elif code == 'arg':
            ex = 'surprised'
        ball(c, code, x0, y, r, ex, look=look, mouth=mouth, **kw)
        if code == 'usa' and g > 47.7:
            d = sm((g - 47.7) / 0.5)
            if d > 0:
                c.save(); c.translate(x0, y - 9 + d * 70); c.rotate(d * 0.6)
                c.set_source_rgba(0.02, 0.02, 0.02, 1)
                for side in (-1, 1):
                    cx = side * 0.33 * r
                    poly(c, [(cx - 0.27 * r, -0.1 * r), (cx + 0.27 * r, -0.1 * r), (cx + 0.2 * r, 0.17 * r), (cx - 0.2 * r, 0.17 * r)]); c.fill()
                c.set_line_width(0.06 * r); c.move_to(-0.62 * r, -0.08 * r); c.line_to(0.62 * r, -0.08 * r); c.stroke(); c.restore()
    c.restore()
    post(c, (0.02, 0.06, 0.14, 0.12), vign=0.7)
    # iconos de rutas (barco / avión / nadar)
    for i, (t0, kind) in enumerate([(47.1, 'barco'), (47.9, 'avion'), (48.8, 'nadar')]):
        if g >= t0 and g < 50.0:
            k = eo((g - t0) / 0.25); x = 230 + i * 310; y = 420
            route_icon(c, kind, x, y, 105 * (0.6 + 0.4 * k), k)

def route_icon(c, kind, x, y, s, alpha=1.0):
    c.save(); c.translate(x, y)
    c.set_source_rgba(*hexc('#FFD23F', alpha)); c.arc(0, 0, s, 0, 2 * PI); c.fill_preserve()
    c.set_source_rgba(0, 0, 0, alpha); c.set_line_width(s * 0.08); c.stroke()
    c.scale(s / 100, s / 100); c.set_source_rgba(*hexc('#1B2433', alpha))
    if kind == 'barco':
        c.move_to(-55, 15); c.line_to(55, 15); c.line_to(35, 45); c.line_to(-38, 45); c.close_path(); c.fill()
        c.rectangle(-4, -55, 8, 70); c.fill(); poly(c, [(6, -50), (45, 8), (6, 8)]); c.fill(); poly(c, [(-6, -40), (-40, 8), (-6, 8)]); c.fill()
    elif kind == 'avion':
        c.rotate(-0.5)
        c.move_to(-60, 0); c.curve_to(-60, -12, 50, -12, 62, 0); c.curve_to(50, 12, -60, 12, -60, 0); c.fill()
        poly(c, [(-10, -5), (25, -60), (40, -60), (15, -5)]); c.fill(); poly(c, [(-10, 5), (25, 60), (40, 60), (15, 5)]); c.fill()
        poly(c, [(-60, -3), (-45, -30), (-35, -30), (-42, -3)]); c.fill()
    else:
        c.set_line_width(11); c.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(2):
            yy = 10 + k * 28; c.move_to(-60, yy)
            for i in range(1, 7): c.curve_to(-60 + i * 20 - 10, yy - 14, -60 + i * 20 - 10, yy + 0, -60 + i * 20, yy - 2)
            c.stroke()
        c.arc(-5, -30, 22, 0, 2 * PI); c.fill()
    c.restore()

# ------------------------------------------------------------------ cierre
def text(c, s, x, y, size, col='#FFFFFF', stroke=None, font=FONT, alpha=1.0, anchor='c'):
    c.select_font_face(font); c.set_font_size(size)
    e = c.text_extents(s)
    xx = x - e.width / 2 - e.x_bearing if anchor == 'c' else x
    c.move_to(xx, y); c.text_path(s)
    c.set_source_rgba(0, 0, 0, alpha); c.set_line_width(stroke or size * 0.17); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke_preserve()
    c.set_source_rgba(*hexc(col, alpha)); c.fill()

def scene_black(c, t):
    c.set_source_rgb(0, 0, 0); c.paint()
    if t > 0.12:
        k = eo((t - 0.12) / 0.25); s = 1.35 - 0.35 * k
        c.save(); c.translate(W / 2 + 4 * math.sin(t * 60) * (1 - k), H / 2); c.scale(s, s)
        text(c, '¿QUIÉN', 0, -40, 150, '#FFFFFF', alpha=k); text(c, 'SOBREVIVIRÁ?', 0, 120, 128, '#E63946', alpha=k)
        c.restore()

def scene_end(c, t):
    g = t + T['final']
    grad(c, 0, 0, W, H, [(0, '#0E1B33'), (0.6, '#1F4E79'), (1, '#0C1626')])
    cam = Cam(); clouds(c, cam, g, top='#2E4566', bot='#16243A', par=0.1, alpha=0.6)
    k = eo(t / 0.4)
    c.save(); c.translate(W / 2, 330); c.scale(0.7 + 0.3 * k, 0.7 + 0.3 * k)
    text(c, '¡TÚ DECIDES', 0, -60, 104, '#FFD23F', alpha=k); text(c, 'EL DESTINO', 0, 60, 104, '#FFFFFF', alpha=k)
    text(c, 'DE AMÉRICA!', 0, 180, 104, '#FFFFFF', alpha=k)
    c.restore()
    for i, kind in enumerate(['barco', 'avion', 'nadar']):
        kk = eo((t - 0.25 - i * 0.12) / 0.3)
        if kk > 0:
            x = 220 + i * 320; route_icon(c, kind, x, 790, 110 * kk, 1.0)
            text(c, ['BARCO', 'AVIÓN', 'NADAR'][i], x, 960, 56, '#FFFFFF', alpha=kk)
    cast = ['usa', 'mex', 'bra', 'arg', 'col', 'can']
    for i, code in enumerate(cast):
        kk = eo((t - 0.4 - i * 0.07) / 0.3)
        x = 120 + i * 168; y = 1260 + (1 - kk) * 400 + 10 * math.sin(g * 4 + i)
        ball(c, code, x, y, 74, 'determined' if code != 'usa' else 'smug', look=(0, -0.4), glasses=1.0 if code == 'usa' else 0)
    if t > 0.8:
        a = eo((t - 0.8) / 0.3); bob = 12 * math.sin(g * 6)
        text(c, 'COMENTA TU EQUIPO', W / 2, 1560, 72, '#FFFFFF', alpha=a)
        c.set_source_rgba(*hexc('#FFD23F', a)); poly(c, [(W / 2 - 60, 1630 + bob), (W / 2 + 60, 1630 + bob), (W / 2, 1720 + bob)]); c.fill()
        c.set_source_rgba(0, 0, 0, a); c.set_line_width(8); poly(c, [(W / 2 - 60, 1630 + bob), (W / 2 + 60, 1630 + bob), (W / 2, 1720 + bob)]); c.stroke()
    post(c, None, 0.5)

# ------------------------------------------------------------------ subtítulos y rótulos
def build_subs(lines):
    subs = []
    for blk, i, start in NARR:
        L = lines[blk][i]; words = L['text'].split(); dur = L['dur']
        chunks = []; cur = []
        for w in words:
            cur.append(w)
            if len(cur) >= 3 or w.endswith((',', ':', '!', '?', '...')):
                chunks.append(cur); cur = []
        if cur: chunks.append(cur)
        total = sum(len(' '.join(ch)) for ch in chunks); t = start
        for ch in chunks:
            d = dur * len(' '.join(ch)) / total
            subs.append((t, t + d, ch)); t += d
    for k in range(len(subs) - 1):
        a, b, ch = subs[k]
        if subs[k + 1][0] - b < 0.5: subs[k] = (a, subs[k + 1][0], ch)
    return subs

def clean(w): return w.strip('¡!¿?,.:;…').upper()

def draw_sub(c, ch, age):
    k = eo(age / 0.12); s = 1.15 - 0.15 * k
    c.select_font_face(FONT); size = 86
    words = [w.upper().replace('...', '…') for w in ch]
    c.set_font_size(size)
    widths = [c.text_extents(w + ' ').x_advance for w in words]
    total = sum(widths);
    lines = [words]; lw = [widths]
    if total > 960:
        lines = [words[:-1], words[-1:]] if len(words) > 1 else [words]
        lw = [widths[:-1], widths[-1:]] if len(words) > 1 else [widths]
    c.save(); c.translate(W / 2, 1390); c.scale(s, s)
    for li, (ws, wd) in enumerate(zip(lines, lw)):
        x = -sum(wd) / 2; y = li * 100 - (len(lines) - 1) * 50
        for w, wdt in zip(ws, wd):
            hl = clean(w) in HIGHLIGHT
            c.move_to(x, y); c.text_path(w)
            c.set_source_rgba(0, 0, 0, 1); c.set_line_width(15); c.set_line_join(cairo.LINE_JOIN_ROUND); c.stroke_preserve()
            c.set_source_rgba(*(hexc('#FFD23F') if hl else (1, 1, 1, 1))); c.fill()
            x += wdt
    c.restore()

def frame(c, g, subs):
    if g < T['s2']: scene1(c, g)
    elif g < T['s3a']: scene2(c, g - T['s2'])
    elif g < T['s3b']: scene3a(c, g - T['s3a'])
    elif g < T['s3c']: scene3b(c, g - T['s3b'])
    elif g < T['s4']: scene3c(c, g - T['s3c'])
    elif g < T['s5']: scene4(c, g - T['s4'])
    elif g < T['negro']: scene5(c, g - T['s5'])
    elif g < T['final']: scene_black(c, g - T['negro'])
    else: scene_end(c, g - T['final'])
    if 0.2 < g < 3.2:
        a = sm((g - 0.2) / 0.3) * (1 - sm((g - 2.8) / 0.4))
        text(c, 'LA GRAN TRAVESÍA DE AMÉRICA', W / 2, 250, 54, '#FFD23F', alpha=a)
        text(c, 'EPISODIO 1: EL DESAFÍO', W / 2, 320, 40, '#FFFFFF', alpha=a)
    for (a, b, kind, label) in ((T['s3a'], T['s3b'], 'barco', 'RUTA 1: BARCO'), (T['s3b'], T['s3c'], 'avion', 'RUTA 2: AVIÓN'),
                                (T['s3c'], T['s4'], 'nadar', 'RUTA 3: NADAR')):
        b = a + 2.2
        if a <= g < b:
            k = eo((g - a) / 0.3) * (1 - sm((g - (b - 0.3)) / 0.3))
            route_icon(c, kind, 175, 300, 88 * (0.5 + 0.5 * k), k)
            text(c, label, 300, 330, 74, '#FFD23F', alpha=k, anchor='l')
    if g < T['negro']:
        for a, b, ch in subs:
            if a <= g < b: draw_sub(c, ch, g - a)

def main():
    lines = json.load(open(sys.argv[1]))
    subs = build_subs(lines)
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    if '--preview' in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index('--preview') + 1].split(',')]
        od = sys.argv[sys.argv.index('--preview') + 2]; os.makedirs(od, exist_ok=True)
        for g in ts:
            c = cairo.Context(surf); c.set_source_rgb(0, 0, 0); c.paint(); frame(c, g, subs)
            surf.write_to_png(os.path.join(od, 'p%05.1f.png' % g))
        return
    audio, outp = sys.argv[2], sys.argv[3]
    n = int(round(T['fin'] * FPS))
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr0', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', outp], stdin=subprocess.PIPE)
    for f in range(n):
        g = f / FPS
        c = cairo.Context(surf); c.set_source_rgb(0, 0, 0); c.paint(); frame(c, g, subs)
        surf.flush(); ff.stdin.write(bytes(surf.get_data()))
        if f % 120 == 0: print('frame', f, '/', n, flush=True)
    ff.stdin.close(); ff.wait(); print('ok', outp)

if __name__ == '__main__':
    main()
