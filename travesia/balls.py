# La Gran Travesía de América — biblioteca de Countryballs (dibujo vectorial con cairo)
# Todas las banderas se dibujan en un cuadrado [-1,1]x[-1,1] recortado por el círculo del personaje.
import math, cairo

def hexc(h, a=1.0):
    h = h.lstrip('#'); return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

def rect(ctx, x0, y0, x1, y1, col):
    ctx.set_source_rgba(*hexc(col)); ctx.rectangle(x0, y0, x1 - x0, y1 - y0); ctx.fill()

def star(ctx, cx, cy, r, col, rot=-math.pi / 2):
    ctx.set_source_rgba(*hexc(col))
    for i in range(10):
        a = rot + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.4
        (ctx.move_to if i == 0 else ctx.line_to)(cx + rr * math.cos(a), cy + rr * math.sin(a))
    ctx.close_path(); ctx.fill()

MAPLE = [(0, -1.0), (0.12, -0.78), (0.25, -0.84), (0.2, -0.45), (0.42, -0.62), (0.47, -0.5), (0.68, -0.55), (0.6, -0.33),
         (0.68, -0.28), (0.38, -0.05), (0.45, 0.12), (0.06, 0.06), (0.06, 0.5)]

# ------------------------------------------------------------------ banderas
def flag_usa(ctx):
    for i in range(13):
        rect(ctx, -1.2, -1.2 + i * 2.4 / 13, 1.2, -1.2 + (i + 1) * 2.4 / 13 + 0.002, '#B22234' if i % 2 == 0 else '#FFFFFF')
    cy1 = -1.2 + 7 * 2.4 / 13
    rect(ctx, -1.2, -1.2, 0.1, cy1, '#3C3B6E')
    for row in range(9):
        n = 6 if row % 2 == 0 else 5
        for c in range(n):
            x = -1.2 + (c + (0.5 if row % 2 == 0 else 1.0)) * (1.3 / 6)
            y = -1.2 + (row + 0.6) * ((cy1 + 1.2) / 9.2)
            star(ctx, x, y, 0.045, '#FFFFFF')

def flag_mexico(ctx):
    rect(ctx, -1.2, -1.2, -0.38, 1.2, '#006847'); rect(ctx, -0.38, -1.2, 0.38, 1.2, '#FFFFFF'); rect(ctx, 0.38, -1.2, 1.2, 1.2, '#CE1126')
    # escudo simplificado: águila sobre nopal con corona de laurel
    ctx.set_source_rgba(*hexc('#2E8B3A')); ctx.set_line_width(0.045)
    ctx.arc(0, 0.02, 0.24, math.radians(20), math.radians(160)); ctx.stroke()
    ctx.set_source_rgba(*hexc('#3C8D2F')); ctx.arc(0.0, 0.1, 0.09, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*hexc('#8B5A2B'))
    ctx.move_to(-0.15, 0.02); ctx.curve_to(-0.2, -0.22, 0.05, -0.28, 0.12, -0.12); ctx.curve_to(0.18, -0.02, 0.08, 0.06, -0.15, 0.02); ctx.fill()
    ctx.arc(0.1, -0.17, 0.055, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*hexc('#E0A526')); ctx.move_to(0.15, -0.18); ctx.line_to(0.22, -0.15); ctx.line_to(0.15, -0.13); ctx.fill()

def flag_brazil(ctx):
    rect(ctx, -1.2, -1.2, 1.2, 1.2, '#009C3B')
    ctx.set_source_rgba(*hexc('#FFDF00'))
    ctx.move_to(-0.9, 0); ctx.line_to(0, -0.62); ctx.line_to(0.9, 0); ctx.line_to(0, 0.62); ctx.close_path(); ctx.fill()
    ctx.save(); ctx.arc(0, 0, 0.36, 0, 2 * math.pi); ctx.clip()
    rect(ctx, -1, -1, 1, 1, '#002776')
    ctx.set_source_rgba(1, 1, 1, 1); ctx.set_line_width(0.07)
    ctx.arc(-0.12, 0.95, 1.0, math.radians(235), math.radians(310)); ctx.stroke()
    for (x, y) in [(0.12, 0.12), (-0.1, 0.18), (0.0, 0.24), (0.2, 0.2), (-0.2, 0.08), (0.08, 0.3), (-0.05, 0.12)]:
        star(ctx, x, y, 0.025, '#FFFFFF')
    ctx.restore()

def flag_argentina(ctx):
    rect(ctx, -1.2, -1.2, 1.2, -0.36, '#74ACDF'); rect(ctx, -1.2, -0.36, 1.2, 0.36, '#FFFFFF'); rect(ctx, -1.2, 0.36, 1.2, 1.2, '#74ACDF')
    ctx.set_source_rgba(*hexc('#F6B40E'))
    for i in range(16):
        a = i * math.pi / 8; r1 = 0.3 if i % 2 == 0 else 0.25
        ctx.move_to(0.11 * math.cos(a - 0.17), 0.11 * math.sin(a - 0.17)); ctx.line_to(r1 * math.cos(a), r1 * math.sin(a))
        ctx.line_to(0.11 * math.cos(a + 0.17), 0.11 * math.sin(a + 0.17)); ctx.close_path(); ctx.fill()
    ctx.arc(0, 0, 0.13, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*hexc('#85340A')); ctx.set_line_width(0.015); ctx.arc(0, 0, 0.13, 0, 2 * math.pi); ctx.stroke()

def flag_canada(ctx):
    rect(ctx, -1.2, -1.2, -0.55, 1.2, '#D52B1E'); rect(ctx, -0.55, -1.2, 0.55, 1.2, '#FFFFFF'); rect(ctx, 0.55, -1.2, 1.2, 1.2, '#D52B1E')
    ctx.set_source_rgba(*hexc('#D52B1E')); s = 0.42
    pts = MAPLE + [(-x, y) for (x, y) in reversed(MAPLE)]
    for i, (x, y) in enumerate(pts):
        (ctx.move_to if i == 0 else ctx.line_to)(x * s, y * s + 0.02)
    ctx.close_path(); ctx.fill()

def flag_colombia(ctx):
    rect(ctx, -1.2, -1.2, 1.2, 0.0, '#FCD116'); rect(ctx, -1.2, 0.0, 1.2, 0.6, '#003893'); rect(ctx, -1.2, 0.6, 1.2, 1.2, '#CE1126')

def flag_peru(ctx):
    rect(ctx, -1.2, -1.2, -0.38, 1.2, '#D91023'); rect(ctx, -0.38, -1.2, 0.38, 1.2, '#FFFFFF'); rect(ctx, 0.38, -1.2, 1.2, 1.2, '#D91023')

def flag_chile(ctx):
    rect(ctx, -1.2, -1.2, 1.2, 0.0, '#FFFFFF'); rect(ctx, -1.2, 0.0, 1.2, 1.2, '#D52B1E'); rect(ctx, -1.2, -1.2, -0.25, 0.0, '#0039A6')
    star(ctx, -0.72, -0.55, 0.2, '#FFFFFF')

FLAGS = {'usa': flag_usa, 'mex': flag_mexico, 'bra': flag_brazil, 'arg': flag_argentina, 'can': flag_canada,
         'col': flag_colombia, 'per': flag_peru, 'chi': flag_chile}
NAMES = {'usa': 'ESTADOS UNIDOS', 'mex': 'MÉXICO', 'bra': 'BRASIL', 'arg': 'ARGENTINA', 'can': 'CANADÁ',
         'col': 'COLOMBIA', 'per': 'PERÚ', 'chi': 'CHILE'}

# ------------------------------------------------------------------ ojos / expresiones
# lid: (c, m) => tapa superior y = c + m*x (coords del ojo, x hacia el centro positivo); bottom: (c, m) tapa inferior
EXPR = {
    'normal': dict(lid=None, bot=None, size=1.0),
    'smug': dict(lid=(-0.05, 0.0), bot=None, size=1.0),          # presumido: párpados a media asta
    'angry': dict(lid=(-0.45, 0.75), bot=None, size=1.0),        # cejas hacia el centro
    'worried': dict(lid=(-0.35, -0.6), bot=None, size=1.05),
    'scared': dict(lid=None, bot=None, size=1.3),
    'surprised': dict(lid=None, bot=None, size=1.25),
    'sly': dict(lid=(-0.1, 0.25), bot=(0.45, 0.0), size=1.0),     # mirada misteriosa
    'happy': dict(happy=True, size=1.0),
    'determined': dict(lid=(-0.5, 0.45), bot=None, size=1.0),
}

def eye(ctx, ex, ey, rx, ry, inner_sign, look, e, blink):
    if e.get('happy'):
        ctx.set_source_rgba(0, 0, 0, 1); ctx.set_line_width(rx * 0.42); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.arc(ex, ey + ry * 0.35, rx * 0.85, math.pi * 1.12, math.pi * 1.88); ctx.stroke(); return
    s = e['size']; rx *= s; ry *= s * max(0.06, 1 - blink)
    lid = e.get('lid'); bot = e.get('bot')
    pts = []
    for i in range(48):
        a = i / 48 * 2 * math.pi
        x = math.cos(a); y = math.sin(a)
        xi = x * inner_sign
        if lid is not None: y = max(y, lid[0] + lid[1] * xi)
        if bot is not None: y = min(y, bot[0] + bot[1] * xi)
        pts.append((ex + x * rx, ey + y * ry))
    for i, (x, y) in enumerate(pts):
        (ctx.move_to if i == 0 else ctx.line_to)(x, y)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 1); ctx.fill_preserve()
    ctx.set_source_rgba(0, 0, 0, 1); ctx.set_line_width(rx * 0.2); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()

def ball(ctx, code, x, y, r, expr='normal', look=(0.0, 0.0), rot=0.0, sx=1.0, sy=1.0, blink=0.0,
         mouth=None, sweat=0.0, glasses=0.0, shadow=True, alpha=1.0, flip=False):
    """Dibuja un countryball. (x, y) = centro; r = radio. sx/sy = squash & stretch. glasses 0..1 = gafas bajando."""
    ctx.save()
    if shadow:
        ctx.set_source_rgba(0, 0, 0, 0.28 * alpha); ctx.save(); ctx.translate(x, y + r * sy * 0.98); ctx.scale(r * 0.95, r * 0.2)
        ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    ctx.translate(x, y + r * (1 - sy)); ctx.rotate(rot); ctx.scale(sx, sy)
    if alpha < 1: ctx.push_group()
    ctx.save(); ctx.arc(0, 0, r, 0, 2 * math.pi); ctx.clip()
    ctx.save(); ctx.scale(r, r); FLAGS[code](ctx); ctx.restore()
    g = cairo.RadialGradient(-0.35 * r, -0.45 * r, 0.05 * r, -0.2 * r, -0.2 * r, 1.25 * r)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.35); g.add_color_stop_rgba(0.45, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.8, 0, 0, 0, 0.0); g.add_color_stop_rgba(1, 0, 0, 0, 0.32)
    ctx.set_source(g); ctx.paint()
    ctx.restore()
    ctx.arc(0, 0, r, 0, 2 * math.pi); ctx.set_source_rgba(0, 0, 0, 1); ctx.set_line_width(r * 0.05); ctx.stroke()
    e = EXPR[expr]
    fx = -1 if flip else 1
    lx, ly = look
    for side in (-1, 1):
        ex = (side * 0.33 + lx * 0.16) * r; ey = (-0.12 + ly * 0.12) * r
        eye(ctx, ex, ey, 0.2 * r, 0.25 * r, -side, look, e, blink)
    if mouth:
        mx = lx * 0.15 * r; my = (0.38 + ly * 0.08) * r
        ctx.set_source_rgba(0, 0, 0, 1); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_width(r * 0.06)
        if mouth == 'smile':
            ctx.arc(mx, my - 0.18 * r, 0.22 * r, math.radians(25), math.radians(155)); ctx.stroke()
        elif mouth == 'smirk':
            ctx.move_to(mx - 0.16 * r, my); ctx.curve_to(mx - 0.05 * r, my + 0.06 * r, mx + 0.1 * r, my + 0.02 * r, mx + 0.2 * r, my - 0.1 * r); ctx.stroke()
        elif mouth == 'frown':
            ctx.arc(mx, my + 0.2 * r, 0.18 * r, math.radians(205), math.radians(335)); ctx.stroke()
        elif mouth == 'o':
            ctx.save(); ctx.translate(mx, my); ctx.scale(0.09 * r, 0.13 * r); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()
        elif mouth == 'shout':
            ctx.save(); ctx.translate(mx, my); ctx.scale(0.17 * r, 0.12 * r); ctx.arc(0, 0, 1, 0, math.pi); ctx.close_path(); ctx.restore()
            ctx.fill_preserve(); ctx.stroke()
        elif mouth == 'line':
            ctx.move_to(mx - 0.12 * r, my); ctx.line_to(mx + 0.12 * r, my); ctx.stroke()
        elif mouth == 'wavy':
            ctx.move_to(mx - 0.18 * r, my)
            for i in range(1, 7): ctx.line_to(mx - 0.18 * r + i * 0.06 * r, my + (0.03 if i % 2 else -0.03) * r)
            ctx.stroke()
    if glasses > 0:
        gy = (-0.12 - 0.0) * r - (1 - glasses) * 1.6 * r if glasses < 1 else -0.12 * r
        ctx.set_source_rgba(0.02, 0.02, 0.02, 1)
        for side in (-1, 1):
            cx = (side * 0.33 + lx * 0.16) * r
            ctx.move_to(cx - 0.27 * r, gy - 0.1 * r); ctx.line_to(cx + 0.27 * r, gy - 0.1 * r)
            ctx.line_to(cx + 0.2 * r, gy + 0.17 * r); ctx.line_to(cx - 0.2 * r, gy + 0.17 * r); ctx.close_path(); ctx.fill()
        ctx.set_line_width(0.06 * r); ctx.move_to(-0.62 * r, gy - 0.08 * r); ctx.line_to(0.62 * r, gy - 0.08 * r); ctx.stroke()
        ctx.set_source_rgba(1, 1, 1, 0.75); ctx.set_line_width(0.03 * r)
        for side in (-1, 1):
            cx = (side * 0.33 + lx * 0.16) * r
            ctx.move_to(cx - 0.12 * r, gy - 0.04 * r); ctx.line_to(cx - 0.02 * r, gy + 0.08 * r); ctx.stroke()
    if sweat > 0:
        sx_, sy_ = 0.72 * r, -0.55 * r + (1 - sweat) * 0.1 * r
        ctx.set_source_rgba(0.75, 0.9, 1, sweat); ctx.move_to(sx_, sy_ - 0.2 * r)
        ctx.curve_to(sx_ + 0.12 * r, sy_, sx_ + 0.1 * r, sy_ + 0.12 * r, sx_, sy_ + 0.12 * r)
        ctx.curve_to(sx_ - 0.1 * r, sy_ + 0.12 * r, sx_ - 0.12 * r, sy_, sx_, sy_ - 0.2 * r); ctx.fill_preserve()
        ctx.set_source_rgba(0, 0, 0, sweat); ctx.set_line_width(0.025 * r); ctx.stroke()
    if alpha < 1:
        ctx.pop_group_to_source(); ctx.paint_with_alpha(alpha)
    ctx.restore()


if __name__ == '__main__':
    # Hoja de referencia de personajes (biblioteca)
    import sys
    W, H = 1080, 1920
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H); c = cairo.Context(s)
    g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgb(0, *hexc('#1B2A4A')[:3]); g.add_color_stop_rgb(1, *hexc('#3E6FA3')[:3])
    c.set_source(g); c.paint()
    c.select_font_face('Luckiest Guy'); c.set_font_size(62)
    def text(t, x, y, size, col='#FFFFFF'):
        c.set_font_size(size); e = c.text_extents(t); c.move_to(x - e.width / 2 - e.x_bearing, y)
        c.text_path(t); c.set_source_rgba(0, 0, 0, 1); c.set_line_width(size * 0.16); c.stroke_preserve(); c.set_source_rgba(*hexc(col)); c.fill()
    text('LA GRAN TRAVESÍA', W / 2, 120, 76, '#FFD23F'); text('DE AMÉRICA', W / 2, 200, 76, '#FFD23F')
    text('PERSONAJES', W / 2, 270, 40)
    order = [('usa', 'smug', 1, None), ('mex', 'normal', 0, None), ('bra', 'happy', 0, 'smile'), ('arg', 'angry', 0, None),
             ('can', 'worried', 0, None), ('col', 'sly', 0, None), ('per', 'normal', 0, None), ('chi', 'surprised', 0, None)]
    for i, (code, ex, gl, mo) in enumerate(order):
        col = i % 2; row = i // 2
        x = 290 + col * 500; y = 470 + row * 400
        ball(c, code, x, y, 135, ex, glasses=gl, mouth=mo)
        text(NAMES[code], x, y + 215, 38)
    s.write_to_png(sys.argv[1])
    # hoja de expresiones de México
    s2 = cairo.ImageSurface(cairo.FORMAT_RGB24, W, 900); c = cairo.Context(s2); c.set_source_rgb(0.85, 0.9, 0.95); c.paint()
    c.select_font_face('Luckiest Guy')
    for i, ex in enumerate(['normal', 'smug', 'angry', 'worried', 'scared', 'surprised', 'sly', 'happy', 'determined']):
        x = 180 + (i % 3) * 360; y = 150 + (i // 3) * 290
        ball(c, 'mex', x, y, 100, ex, sweat=1.0 if ex == 'scared' else 0, mouth='o' if ex == 'surprised' else None)
        text(ex.upper(), x, y + 150, 30, '#FFFFFF')
    s2.write_to_png(sys.argv[2])
