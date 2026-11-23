# "Tu casa en el Sahara" — explicativo estilo problema→solución, personita 2D POV en un desierto 3D detallado.
# Uso: blender -b -P sahara.py -- <toma> <carpeta_salida> [ancho] [frame_ini] [frame_fin]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math, random
from mathutils import Vector
import lib3d
from lib3d import *
from people import Person, outlined

argv = sys.argv[sys.argv.index('--') + 1:]
SHOT = argv[0]; OUT = argv[1]
RESX = int(argv[2]) if len(argv) > 2 else 540
FSTART = int(argv[3]) if len(argv) > 3 else 0
FEND = int(argv[4]) if len(argv) > 4 else 10 ** 6
PI = math.pi; FPS = 24
# inicio de cada toma según la voz (s) — duraciones nominales
CUTS = [('S1', 0.0), ('S2', 6.0), ('S3', 11.6), ('S4', 19.3), ('S5', 22.8), ('S6', 28.8), ('S7', 32.9),
        ('S8', 39.7), ('S9', 44.2), ('S10', 49.4), ('S11', 54.4), ('END', 63.4)]
SHOTS = {k: CUTS[i + 1][1] - t for i, (k, t) in enumerate(CUTS[:-1])}
EXPLORER = dict(shirt='#C9A86A', pants='#6B5A3E', hat='safari', mustache=False, collar='#A4844E')

def plight(loc, power=100, hexc='#FFC27A', radius=0.3, shadow=False):
    d = bpy.data.lights.new('p', 'POINT'); d.energy = power; d.color = lin(hexc); d.shadow_soft_size = radius; d.use_shadow = shadow
    o = link(bpy.data.objects.new('p', d)); o.location = loc; return o

# ------------------------------------------------------------------ terreno de dunas
def dune_h(x, y):
    r = math.hypot(x, y)
    flat = sm((r - 10) / 22)
    a = math.sin(0.045 * x + 0.8 * math.sin(0.018 * y) + 0.5)
    ridge = (1 - abs(a)) ** 2.2
    b = 0.5 + 0.5 * math.sin(0.07 * y + 0.03 * x)
    h = 6.5 * ridge * (0.6 + 0.4 * b) + 1.2 * math.sin(0.11 * x + 0.13 * y) + 0.6 * math.sin(0.23 * x - 0.17 * y)
    return flat * h - 0.05

def ground_z(x, y): return dune_h(x, y)

def sand_mat():
    if 'sand' in MATS: return MATS['sand']
    m = bpy.data.materials.new('sand'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.92
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.04; nz.inputs['Detail'].default_value = 3
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*lin('#D9A15A'), 1); ramp.color_ramp.elements[1].color = (*lin('#EBC07E'), 1)
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 0.9; wv.inputs['Distortion'].default_value = 3.0
    wv.inputs['Detail'].default_value = 1.5
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    MATS['sand'] = m; return m

def terrain(size=520, n=170):
    bm = bmesh.new(); step = size / n; vs = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x = -size / 2 + i * step; y = -size / 2 + j * step + 120
            row.append(bm.verts.new((x, y, dune_h(x, y))))
        vs.append(row)
    for j in range(n):
        for i in range(n):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new('dunes'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new('dunes', me)); me.materials.append(sand_mat())
    return o

# ------------------------------------------------------------------ decorado
def rock(x, y, s, rnd):
    return prim('ico_sphere', (x, y, ground_z(x, y) + s * 0.15), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3)),
                scale=(s, s * rnd.uniform(0.7, 1.0), s * rnd.uniform(0.45, 0.7)), m=mat(rnd.choice(['#A8673F', '#B97A4C', '#94583A']), 0.9), subdivisions=1, radius=1)

def palm(x, y, h, rnd):
    z = ground_z(x, y); T = mat('#8A6440', 0.9, key='palmt'); L = mat('#4E9A3C', 0.7, key='palml')
    lean = V(rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 0)
    for i in range(6):
        u = i / 6
        prim('cylinder', V(x, y, z) + lean * h * u * u + V(0, 0, h * (u + 1 / 12)), m=T, vertices=7, radius=0.24 - 0.07 * u, depth=h / 6 * 1.05)
    top = V(x, y, z) + lean * h + V(0, 0, h)
    for k in range(8):
        e = empty(top); e.rotation_euler = (0, 0, k / 8 * 2 * PI + rnd.uniform(-0.2, 0.2))
        prim('cube', (1.4, 0, -0.38), rot=(0, 0.45, 0), scale=(2.8, 0.6, 0.04), m=L, parent=e, size=1)
    prim('ico_sphere', top + V(0, 0, -0.15), m=mat('#6B4A2B', 0.8, key='coco'), subdivisions=1, radius=0.28)

def oasis(cx, cy, rnd):
    z = ground_z(cx, cy)
    prim('cylinder', (cx, cy, z + 0.25), scale=(1, 0.7, 1), m=mat('#2E9BB0', 0.08, key='pond'), vertices=24, radius=9, depth=0.1)
    prim('cylinder', (cx, cy, z + 0.2), scale=(1, 0.7, 1), m=mat('#7DAA4A', 0.9, key='oasisg'), vertices=24, radius=13, depth=0.08)
    for k in range(14):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(9, 14)
        palm(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7, rnd.uniform(6, 9), rnd)
    for k in range(10):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(9, 13)
        prim('ico_sphere', (cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7, z + 0.6), m=mat('#3F7F31', 0.8, key='bushd'), subdivisions=1, radius=rnd.uniform(0.8, 1.4))

ADOBE = '#C98A50'
def adobe_box(x, y, w, d, h, rnd, col=ADOBE, crenel=True):
    z = ground_z(x, y) - 0.3
    b = prim('cube', (x, y, z + h / 2), scale=(w, d, h), m=mat(col, 0.95), size=1)
    bv = b.modifiers.new('bv', 'BEVEL'); bv.width = 0.25; bv.segments = 2
    if crenel:
        for k in range(int(w / 1.2)):
            prim('cube', (x - w / 2 + 0.6 + k * 1.2, y - d / 2 + 0.2, z + h + 0.3), scale=(0.6, 0.4, 0.6), m=mat(col, 0.95), size=1)
    for k in range(int(w / 2.5)):
        prim('cube', (x - w / 2 + 1.25 + k * 2.5, y - d / 2 - 0.02, z + h * 0.62), scale=(0.5, 0.1, 0.7), m=mat('#3A2414', 0.9, key='win'), size=1)
    return b

def ksar(cx, cy, rnd):
    for k in range(16):
        x = cx + rnd.uniform(-22, 22); y = cy + rnd.uniform(-8, 14)
        adobe_box(x, y, rnd.uniform(5, 9), rnd.uniform(5, 8), rnd.uniform(4, 9), rnd, rnd.choice([ADOBE, '#B97A45', '#D49A62']))
    for (x, y) in [(cx - 24, cy - 9), (cx + 24, cy - 9)]:
        z = ground_z(x, y)
        prim('cylinder', (x, y, z + 6), m=mat('#B97A45', 0.95), vertices=12, radius=2.2, depth=12)
        prim('cone', (x, y, z + 12.8), m=mat('#A9693A', 0.95), vertices=12, radius1=2.4, depth=1.8)

class Camel:
    def __init__(s, scale=1.0):
        C = mat('#C69A62', 0.85, key='camel'); D = mat('#8E6A42', 0.85, key='camelD')
        s.root = empty(); s.root.scale = (scale,) * 3
        prim('uv_sphere', (0, 0, 1.9), scale=(0.55, 1.15, 0.5), m=C, smooth=True, parent=s.root, segments=16, ring_count=10, radius=1)
        prim('uv_sphere', (0, -0.1, 2.45), scale=(0.4, 0.5, 0.45), m=C, smooth=True, parent=s.root, segments=12, ring_count=8, radius=1)
        prim('cylinder', (0, 1.3, 2.5), rot=(-0.6, 0, 0), m=C, smooth=True, parent=s.root, vertices=10, radius=0.17, depth=1.2)
        prim('uv_sphere', (0, 1.75, 3.05), scale=(0.2, 0.42, 0.2), m=C, smooth=True, parent=s.root, segments=12, ring_count=8, radius=1)
        prim('cube', (0, -0.1, 2.15), scale=(1.15, 0.9, 0.12), m=mat('#B4362E', 0.8, key='blanket'), parent=s.root, size=1)
        s.legs = []
        for (lx, ly) in [(0.3, 0.8), (-0.3, 0.8), (0.3, -0.8), (-0.3, -0.8)]:
            h = empty((lx, ly, 1.6), s.root)
            prim('cylinder', (0, 0, -0.8), m=D, parent=h, vertices=8, radius=0.09, depth=1.6)
            s.legs.append(h)
    def set(s, pos, yaw, t):
        s.root.location = pos; s.root.rotation_euler = (0, 0, yaw)
        for i, h in enumerate(s.legs):
            h.rotation_euler = (0.35 * math.sin(t * 4 + (0 if i in (0, 3) else PI)), 0, 0)

def stars(n=350, R=450):
    S = mat('#FFFFFF', 0.5, emit=6.0, key='star'); rnd = random.Random(4)
    for _ in range(n):
        a = rnd.uniform(0, 2 * PI); e = rnd.uniform(0.08, 1.4)
        prim('ico_sphere', (math.cos(a) * math.cos(e) * R, math.sin(a) * math.cos(e) * R + 100, math.sin(e) * R), m=S, subdivisions=1, radius=rnd.uniform(0.6, 1.4))
    prim('uv_sphere', (-120, 380, 160), m=mat('#F4F1E0', 0.5, emit=3.0, key='moon'), segments=24, ring_count=12, radius=14)

def mountains(rnd):
    for i in range(10):
        x = -260 + i * 58 + rnd.uniform(-15, 15)
        prim('cone', (x, 360 + rnd.uniform(-20, 30), -4), rot=(0, 0, rnd.uniform(0, 3)), scale=(1, 0.7, 1),
             m=mat(rnd.choice(['#9C5F3C', '#8A5236', '#A8714A']), 0.95), vertices=6, radius1=rnd.uniform(45, 75), depth=rnd.uniform(50, 95))

def world(mode='day'):
    if mode == 'day': setup(world='#4FA6E8', strength=0.9, sun_rot=(42, 0, 30), sun_power=3.6, resx=RESX)
    elif mode == 'night': setup(world='#0C1A3A', strength=0.25, sun_rot=(60, 0, -40), sun_power=0.35, resx=RESX)
    else: setup(world='#E58A4E', strength=0.7, sun_rot=(82, 0, 10), sun_power=2.2, resx=RESX)
    if mode == 'night':
        for o in bpy.data.objects:
            if o.type == 'LIGHT' and o.data.type == 'SUN': o.data.color = (0.55, 0.65, 1.0)
    if mode == 'dusk':
        for o in bpy.data.objects:
            if o.type == 'LIGHT' and o.data.type == 'SUN': o.data.color = (1.0, 0.6, 0.35)
    rnd = random.Random(8)
    terrain(); mountains(rnd)
    for _ in range(70):
        x = rnd.uniform(-90, 90); y = rnd.uniform(-40, 160)
        if math.hypot(x, y) < 9: continue
        rock(x, y, rnd.uniform(0.3, 1.6), rnd)
    oasis(46, 78, rnd); ksar(-42, 92, rnd)
    camels = [Camel(1.0) for _ in range(4)]
    if mode == 'night': stars()
    else:
        if mode == 'day':
            prim('uv_sphere', (140, 420, 230), m=mat('#FFF6D8', 0.5, emit=8.0, key='sun'), segments=24, ring_count=12, radius=16)
        C = mat('#FFFFFF', 0.9, emit=0.5, key='cloudd'); C.shadow_method = 'NONE'
        for _ in range(5):
            x = rnd.uniform(-200, 200); y = rnd.uniform(250, 420); z = rnd.uniform(60, 110); s = rnd.uniform(8, 14)
            for i in range(6):
                prim('uv_sphere', (x + (i - 3) * s * 0.6, y, z + (s * 0.3 if i in (2, 3) else 0)), scale=(1, 0.8, 0.7), m=C, smooth=True, segments=12, ring_count=8, radius=s * rnd.uniform(0.5, 0.8))
    bpy.context.view_layer.update()
    return rnd, camels

def caravan(camels, t, y0=34.0):
    for i, c in enumerate(camels):
        x = -60 + t * 1.3 + i * 5.5; y = y0 + i * 0.6
        c.set(V(x, y, ground_z(x, y)), -PI / 2, t + i * 0.7)

# ------------------------------------------------------------------ construcciones
def shack():
    root = empty((0, 2.4, 0)); M = mat('#9AA3AA', 0.35, key='tin'); parts = []
    for (x, y, sx, sy, sz) in [(-1.6, 0, 0.08, 3.2, 2.4), (1.6, 0, 0.08, 3.2, 2.4), (0, 1.6, 3.2, 0.08, 2.4), (0, -1.6, 3.2, 0.08, 2.4)]:
        o = prim('cube', (x, y, 1.2), scale=(sx, sy, sz), m=M, parent=root, size=1); parts.append(o)
    rf = prim('cube', (0, 0, 2.45), rot=(0.06, 0, 0), scale=(3.6, 3.6, 0.08), m=mat('#8A939A', 0.35, key='tinr'), parent=root, size=1); parts.append(rf)
    door = prim('cube', (0.6, -1.65, 0.95), scale=(0.9, 0.04, 1.9), m=mat('#6E5A44', 0.7, key='door'), parent=root, size=1); parts.append(door)
    for o in parts: outlined(o, 1.02)
    return root, parts

def mud_house(cut=False, tower=False):
    root = empty((0, 2.4, 0)); M = mat('#C98A50', 0.95, key='mud'); W = 0.65; S = 4.6; H = 2.9
    walls = []
    spec = [(-S / 2 + W / 2, 0, W, S, H), (S / 2 - W / 2, 0, W, S, H), (0, S / 2 - W / 2, S, W, H)]
    if not cut: spec.append((0, -S / 2 + W / 2, S, W, H))
    for (x, y, sx, sy, sz) in spec:
        o = prim('cube', (x, y, sz / 2), scale=(sx, sy, sz), m=M, parent=root, size=1); walls.append(o)
        if not cut: outlined(o, 1.015)
    roof = prim('cube', (0, 0.0 if not cut else 0.6, H + 0.15), scale=(S + 0.2, S + 0.2 if not cut else S - 1.0, 0.3), m=M, parent=root, size=1)
    if cut:
        # corte: cara interior más clara para que se lea el grosor del muro
        for (x, y, sx, sy, sz) in spec:
            if sx < 1.0:
                prim('cube', (x, -S / 2 - 0.002, sz / 2), scale=(sx, 0.004, sz), m=mat('#E8BC86', 0.95, key='cutface'), parent=root, size=1)
        prim('cube', (0, 0.0, 0.02), scale=(S - 2 * W, S - W, 0.04), m=mat('#A9774A', 0.95, key='floor'), parent=root, size=1)
    else:
        prim('cube', (0.0, -S / 2 - 0.01, 1.0), scale=(0.95, 0.05, 2.0), m=mat('#5A3B22', 0.8, key='door2'), parent=root, size=1)
        for x in (-1.3, 1.3):
            prim('cube', (x, -S / 2 - 0.01, 2.1), scale=(0.45, 0.05, 0.45), m=mat('#3A2414', 0.9, key='win'), parent=root, size=1)
    tw = None
    if tower:
        tw = empty((1.2, 1.2, H), root)
        th = 3.4
        for (x, y, sx, sy) in [(-0.6, 0, 0.12, 1.3), (0.6, 0, 0.12, 1.3), (0, 0.6, 1.3, 0.12)] + ([] if cut else [(0, -0.6, 1.3, 0.12)]):
            prim('cube', (x, y, th / 2), scale=(sx, sy, th), m=M, parent=tw, size=1)
        prim('cube', (0, 0, th + 0.1), scale=(1.5, 1.5, 0.2), m=M, parent=tw, size=1)
        for (x, y, sx, sy) in [(-0.62, 0, 0.14, 0.7), (0.62, 0, 0.14, 0.7)]:
            prim('cube', (x, y, th - 0.7), scale=(sx, sy, 0.9), m=mat('#3A2414', 0.9, key='win'), parent=tw, size=1)
    return root, walls, tw

def arrow(col, length=1.6, r=0.09, emit=1.2):
    e = empty(); M = mat(col, 0.5, emit=emit, key='arr' + col)
    prim('cylinder', (0, 0, length / 2), m=M, parent=e, vertices=10, radius=r, depth=length)
    prim('cone', (0, 0, length + 0.22), m=M, parent=e, vertices=12, radius1=r * 2.6, depth=0.44)
    outlined(e.children[0], 1.15)
    return e

def aim(e, pos, direction, scale=1.0):
    e.location = pos; e.rotation_euler = direction.normalized().to_track_quat('Z', 'Y').to_euler(); e.scale = (scale,) * 3

def thermometer():
    root = empty()
    prim('cylinder', (0, 0, 1.6), m=mat('#E8F4FF', 0.1, alpha=0.45, key='glass'), parent=root, vertices=16, radius=0.22, depth=3.0)
    bulb = prim('uv_sphere', (0, 0, 0.0), m=mat('#E3342F', 0.3, key='merc'), parent=root, segments=16, ring_count=10, radius=0.38)
    outlined(bulb, 1.08)
    fluid = prim('cylinder', (0, 0, 0.0), m=mat('#E3342F', 0.3, key='merc'), parent=root, vertices=12, radius=0.12, depth=1.0)
    for k in range(6): prim('cube', (0.24, 0, 0.6 + k * 0.45), scale=(0.1, 0.02, 0.03), m=mat('#222222', 0.5, key='tick'), parent=root, size=1)
    return root, fluid

# ------------------------------------------------------------------ TOMAS
def hero(): return Person(EXPLORER)

def S1():
    rnd, camels = world('day'); p = hero(); sh, parts = shack()
    cam, tgt = make_cam(28)
    order = [3, 0, 1, 2, 4, 5]
    def anim(t):
        caravan(camels, t)
        for k, idx in enumerate(order):
            o = parts[idx]; u = eo((t - (0.9 + k * 0.55)) / 0.3)
            o.scale = tuple(v * max(u, 0.001) for v in o.scale) if False else o.scale
            o.hide_render = t < 0.9 + k * 0.55
        ham = math.sin(t * 14) if t < 4.4 else 0
        done = sm((t - 4.6) / 0.4)
        p.pose(pos=(2.6, -0.4, 0), yaw=-0.6 + 0.6 * done, armR=(-1.4 - 0.6 * ham * (1 - done), 0.2, 0, -0.6) if done < 0.5 else (-0.2, 0.9, 0, -1.8),
               armL=None if done < 0.5 else (-0.2, -0.9, 0, -1.8), smile=done, squint=0.3 * done, look=(-0.6 * (1 - done), 0))
        if t < 2.0:
            u = sm(t / 2.0); cam.location = V(-30, -70, 18).lerp(V(4, -10, 3.2), u); tgt.location = V(0, 40, 4).lerp(V(0.8, 2, 1.4), u)
        else:
            u = sm((t - 2.0) / 4.0); cam.location = V(4, -10, 3.2).lerp(V(5.5, -7.5, 2.6), u); tgt.location = V(0.8, 2, 1.4)
    return anim

def S2():
    rnd, camels = world('day'); p = hero(); sh, parts = shack()
    th, fluid = thermometer(); th.location = (-3.2, 0.2, 0.6)
    glow = mat('#9AA3AA', 0.35, key='tin'); bsdf = glow.node_tree.nodes['Principled BSDF']
    steam = [prim('uv_sphere', (rnd.uniform(-1.4, 1.4), 2.4 + rnd.uniform(-1.2, 1.2), 2.6), m=mat('#FFFFFF', 0.9, alpha=0.35, key='steam'), segments=10, ring_count=6, radius=0.3) for _ in range(14)]
    cam, tgt = make_cam(28)
    def anim(t):
        caravan(camels, t + 6)
        heat = sm((t - 1.0) / 3.0)
        fluid.scale.z = 0.4 + 2.6 * heat; fluid.location.z = fluid.scale.z / 2
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.25, 0.05, 1); bsdf.inputs['Emission Strength'].default_value = 1.6 * sm((t - 3.5) / 1.5)
        for k, s_ in enumerate(steam):
            u = ((t * 0.5 + k * 0.13) % 1.0); s_.location.z = 2.6 + u * 2.5; sc = 0.3 + u * 0.6
            s_.scale = (sc, sc, sc); s_.hide_render = t < 3.5
        melt = sm((t - 2.5) / 2.0)
        p.pose(pos=(2.6, -0.6, 0), yaw=-0.5, crouch=0.35 * melt, wide=1, mouth=0.4 + 0.4 * melt, worry=1, nod=-0.3 * (1 - melt) + 0.2 * melt,
               look=(0, 0.8 * (1 - melt)), armL=(-0.3, -0.5, 0, -0.8 - 0.8 * melt), armR=(-0.3, 0.5, 0, -0.8 - 0.8 * melt))
        if t < 1.6:
            u = sm(t / 1.6); cam.location = V(3, -9, 1.5); tgt.location = V(30, 400, 180).lerp(V(0, 2, 1.5), u)
        else:
            u = sm((t - 1.6) / 4.0); cam.location = V(3, -9, 1.5).lerp(V(1.5, -7, 2.0), u); tgt.location = V(-0.5, 1.0, 1.6)
    return anim

def cutaway_scene(mode, tower=False):
    rnd, camels = world(mode); root, walls, tw = mud_house(cut=True, tower=tower)
    return rnd, camels, root, walls, tw

def S3():
    rnd, camels, root, walls, tw = cutaway_scene('day'); p = hero()
    arrows = [arrow('#FF5A1F') for _ in range(5)]
    cool = plight((0, 2.4, 2.0), power=40, hexc='#9FD3FF', radius=1.0)
    cam, tgt = make_cam(28)
    def anim(t):
        caravan(camels, t + 12)
        for i, a in enumerate(arrows):
            z = 0.5 + i * 0.55
            prog = sm((t - 1.4 - i * 0.12) / 5.0)
            x = -5.0 + 2.45 * prog
            aim(a, V(x, 0.2 - 0.05, z), V(1, 0, -0.08), 0.9)
            a.hide_render = t < 1.4 + i * 0.12
        p.pose(pos=(0.4, 2.2, 0), yaw=0.0, smile=sm((t - 3) / 0.5), squint=0.3, armL=(-0.2, -0.9, 0, -1.8), armR=(-0.2, 0.9, 0, -1.8))
        u = sm(t / 7.7)
        cam.location = V(-1.0, -9.5, 3.0).lerp(V(-0.6, -8.0, 2.4), u); tgt.location = V(-0.8, 2.4, 1.4)
    return anim

def S4():
    rnd, camels = world('night'); p = hero(); root, walls, tw = mud_house(cut=False)
    puffs = [prim('uv_sphere', (0, 0, 0), m=mat('#FFFFFF', 0.9, alpha=0.4, key='breath'), segments=8, ring_count=6, radius=0.12) for _ in range(5)]
    plight((2.6, -1.6, 2.8), power=25, hexc='#9FB8FF', radius=2.0)
    cam, tgt = make_cam(28)
    def anim(t):
        caravan(camels, t + 19)
        sh = 0.04 * math.sin(t * 45)
        p.pose(pos=(2.6 + sh, -2.2, 0), yaw=-0.4, crouch=0.2, wide=1, worry=1, mouth=0.3, armL=(-0.9, -0.2, 0.9, -2.2), armR=(-0.9, 0.2, -0.9, -2.2))
        bpy.context.view_layer.update()
        hp = p.head.matrix_world.translation
        for k, b in enumerate(puffs):
            u = (t * 1.1 + k * 0.2) % 1.0
            b.location = hp + V(-0.1 - 0.6 * u, -0.45 - 0.6 * u, -0.15 + 0.3 * u); s = 0.6 + u * 1.6; b.scale = (s, s, s); b.hide_render = u > 0.9
        u = sm(t / 3.5)
        cam.location = V(-12, -30, 14).lerp(V(5.2, -7.5, 2.0), u); tgt.location = V(0, 30, 10).lerp(V(2.5, -1.8, 1.4), u)
    return anim

def S5():
    rnd, camels, root, walls, tw = cutaway_scene('night'); p = hero()
    warm = plight((0, 2.4, 2.0), power=0, hexc='#FFB36B', radius=1.2)
    arrows = [arrow('#FF7A2F') for _ in range(5)]
    cam, tgt = make_cam(28)
    def anim(t):
        caravan(camels, t + 23)
        k = sm((t - 0.6) / 2.0)
        warm.data.energy = 140 * k
        for i, a in enumerate(arrows):
            z = 0.6 + i * 0.5; prog = ((t * 0.45 + i * 0.2) % 1.0)
            aim(a, V(-1.95 + prog * 1.2, 0.2, z), V(1, 0, 0), 0.6 * k + 0.001)
            a.hide_render = k < 0.05
        p.pose(pos=(0.4, 2.2, 0), yaw=0.0, smile=k, squint=0.6 * k, armL=(-0.2, -0.9, 0, -1.8), armR=(-0.2, 0.9, 0, -1.8), worry=1 - k, wide=1 - k)
        u = sm(t / 6.0)
        cam.location = V(-0.6, -8.0, 2.4).lerp(V(-0.2, -6.4, 2.1), u); tgt.location = V(-0.5, 2.4, 1.3)
    return anim

def S6():
    rnd, camels, root, walls, tw = cutaway_scene('day'); p = hero()
    dust = [prim('ico_sphere', (random.uniform(-1.6, 1.6), random.uniform(0.6, 4.0), random.uniform(0.3, 2.6)), m=mat('#F2D7A8', 0.9, alpha=0.6, key='dust'), subdivisions=1, radius=0.03) for _ in range(60)]
    haze = prim('cube', (0, 2.4, 1.4), scale=(3.2, 3.2, 2.8), m=mat('#F4B26A', 1.0, alpha=0.12, key='haze'), size=1)
    cam, tgt = make_cam(30)
    def anim(t):
        caravan(camels, t + 29)
        fan = math.sin(t * 16)
        p.pose(pos=(0.2, 2.0, 0), yaw=0.1, worry=1, mouth=0.5, squint=0.4, look=(0.3, 0.5),
               armR=(-1.6, 0.2 + 0.4 * fan, 0, -1.6), armL=(-0.3, -0.4, 0, -0.6))
        for k, d in enumerate(dust): d.location.z += 0.0005 * math.sin(t + k)
        u = sm(t / 4.1)
        cam.location = V(0.2, -4.8, 1.9).lerp(V(0.3, -3.6, 1.8), u); tgt.location = V(0.2, 2.0, 1.55)
    return anim

def S7():
    rnd, camels, root, walls, tw = cutaway_scene('day', tower=True); p = hero()
    arrows = [arrow('#3FA9F5', length=1.2) for _ in range(7)]
    cam, tgt = make_cam(28)
    path = [V(-3.5, 3.6, 6.9), V(0.6, 3.6, 6.9), V(1.2, 3.6, 6.0), V(1.2, 3.6, 3.6), V(1.2, 3.6, 1.6), V(0.0, 3.0, 1.0)]
    def along(u):
        u = max(0.0, min(0.999, u)) * (len(path) - 1); i = int(u); f = u - i
        return path[i].lerp(path[i + 1], f), (path[i + 1] - path[i])
    def anim(t):
        caravan(camels, t + 33)
        rise = eo(t / 1.2)
        tw.scale = (1, 1, max(0.01, rise))
        for i, a in enumerate(arrows):
            u = ((t - 1.0) * 0.22 + i / 7.0) % 1.0
            pos, d = along(u); aim(a, pos, d, 0.55); a.hide_render = t < 1.0
        relief = sm((t - 3.6) / 0.6)
        p.pose(pos=(0.0, 2.4, 0), yaw=0.1, smile=relief, squint=0.4 * relief, worry=1 - relief, nod=-0.2 * relief,
               armL=(-0.2, -0.9 * relief, 0, -1.8 * relief), armR=(-0.2, 0.9 * relief, 0, -1.8 * relief))
        u = sm(t / 6.8)
        cam.location = V(-1.5, -11.5, 6.0).lerp(V(-0.5, -9.5, 4.2), u); tgt.location = V(0.2, 2.6, 3.2).lerp(V(0.4, 2.6, 2.2), u)
    return anim

def S8():
    rnd, camels = world('day'); p = hero(); root, walls, tw = mud_house(cut=False, tower=True)
    bucket = empty()
    prim('cylinder', (0, 0, 0), m=mat('#7E8A92', 0.3, key='bucket'), parent=bucket, vertices=16, radius=0.22, depth=0.4)
    prim('torus', (0, 0, 0.2), m=mat('#5B666E', 0.3, key='bucketr'), parent=bucket, major_radius=0.22, minor_radius=0.02, major_segments=16, minor_segments=4)
    drop = prim('uv_sphere', (0, 0, 0), scale=(0.05, 0.05, 0.08), m=mat('#4FB3E8', 0.1, key='drop'), segments=10, ring_count=6, radius=1)
    cracks = []
    for k in range(9):
        a = k / 9 * 2 * PI
        r0 = rnd.uniform(1.0, 2.2)
        cracks.append(prim('cube', (2.6 + math.cos(a) * r0, -1.6 + math.sin(a) * r0, ground_z(2.6, -1.6) + 0.01), rot=(0, 0, a + rnd.uniform(-0.6, 0.6)), scale=(rnd.uniform(0.3, 0.6), 0.025, 0.01), m=mat('#9A6236', 0.9, key='crack'), size=1))
    cam, tgt = make_cam(30)
    def anim(t):
        caravan(camels, t + 40)
        flip = sm((t - 0.6) / 0.6)
        p.pose(pos=(2.6, -1.6, 0), yaw=-0.3, armR=(-1.2 - 0.9 * flip, 0.2, 0, -0.4), armL=(-1.2 - 0.9 * flip, -0.2, 0, -0.4),
               wide=sm((t - 2.0) / 0.3), mouth=0.2, worry=sm((t - 2.0) / 0.3), nod=0.3 * flip, look=(0, -0.6 * flip))
        hp = p.hand_pos('R').lerp(p.hand_pos('L'), 0.5)
        bucket.location = hp + V(0, -0.15, 0.1); bucket.rotation_euler = (PI * flip, 0, 0)
        du = (t - 1.4) / 0.6
        drop.hide_render = not (0 < du < 1)
        drop.location = hp + V(0, -0.15, -0.1 - 1.6 * max(0, du) ** 2)
        u = sm(t / 4.5)
        cam.location = V(5.5, -6.5, 2.0).lerp(V(4.3, -4.8, 1.8), u); tgt.location = V(2.4, -1.4, 1.2)
    return anim

def S9():
    setup(world='#4FA6E8', strength=0.9, sun_rot=(40, 0, 10), sun_power=3.2, resx=RESX)
    rnd = random.Random(3)
    L = 38
    layers = [(-3.0, 0.0, '#E3B26E'), (-9.0, -3.0, '#C9894F'), (-17.0, -9.0, '#A86A45'), (-40.0, -17.0, '#8C5A3C')]
    for (z0, z1, col) in layers:
        prim('cube', (0, 0, (z0 + z1) / 2), scale=(L, 6, z1 - z0), m=mat(col, 0.95), size=1)
    for i in range(4):
        prim('cone', (-17 + i * 3.2, 0, 0), rot=(0, 0, 0.3 * i), scale=(1, 0.5, 1), m=mat('#9C5F3C', 0.95), vertices=6, radius1=5.5 - i * 0.7, depth=13 - i * 2.4)
    prim('cube', (-13, 0, -12.5), scale=(12, 6.05, 3.0), m=mat('#3D8FD1', 0.3, key='aquifer'), size=1)
    tun0 = V(-9, -3.02, -11.8); tun1 = V(14.5, -3.02, -2.2)
    d = tun1 - tun0; mid = (tun0 + tun1) / 2; ang = -math.atan2(d.z, d.x)
    prim('cube', mid, rot=(0, ang, 0), scale=(d.length, 0.06, 1.0), m=mat('#3A2414', 0.9, key='tunnel'), size=1)
    water = prim('cube', mid, rot=(0, ang, 0), scale=(d.length, 0.08, 0.4), m=mat('#4FB3E8', 0.1, emit=0.5, key='water'), size=1)
    for k in range(7):
        pt = tun0.lerp(tun1, (k + 0.5) / 7)
        prim('cube', (pt.x, -3.02, pt.z / 2), scale=(0.5, 0.06, -pt.z), m=mat('#3A2414', 0.9, key='tunnel'), size=1)
        prim('torus', (pt.x, 0, 0.05), scale=(1, 1, 0.5), m=mat('#C9894F', 0.95, key='mound'), major_radius=0.9, minor_radius=0.35, major_segments=12, minor_segments=6)
    house = empty((16, 0, 0))
    hb = prim('cube', (0, 0, 1.4), scale=(4, 4, 2.8), m=mat('#C98A50', 0.95, key='mud'), parent=house, size=1); outlined(hb, 1.02)
    prim('cube', (1.2, 1.2, 4.2), scale=(1.2, 1.2, 2.8), m=mat('#C98A50', 0.95, key='mud'), parent=house, size=1)
    for x in (-8, 4, 10): palm(x, 1.5, 5, rnd)
    p = hero(); cam, tgt = make_cam(30)
    def anim(t):
        flow = sm((t - 1.2) / 3.0)
        water.scale.x = max(0.01, d.length * flow)
        water.location = tun0.lerp(tun1, flow / 2) + V(0, -0.01, 0.1)
        dig = math.sin(t * 9)
        p.pose(pos=(12, -1.0, 0), yaw=-1.2, crouch=0.25, lean=0.4 + 0.2 * dig, armR=(-1.2 + 0.8 * dig, 0.2, 0, -0.4), armL=(-1.2 + 0.8 * dig, -0.2, 0, -0.4),
               smile=sm((t - 4.0) / 0.4), worry=0.3)
        u = sm(t / 5.2)
        cam.location = V(11, -8, 1.6).lerp(V(-1.5, -56, -6), u); tgt.location = V(12, 0, 0.8).lerp(V(-1.5, 0, -6), u)
    return anim

def S10():
    rnd, camels = world('day')
    for k in range(40):
        x = 46 - k * 3.2 + 2.0 * math.sin(k * 0.3); y = 78 - 12 - k * 3.6
        z = ground_z(x, y)
        prim('torus', (x, y, z + 0.1), scale=(1, 1, 0.5), m=mat('#C9894F', 0.95, key='mound'), major_radius=1.0, minor_radius=0.4, major_segments=12, minor_segments=6)
        prim('cylinder', (x, y, z + 0.05), m=mat('#2A1A0E', 0.9, key='hole'), vertices=10, radius=0.55, depth=0.08)
    cam, tgt = make_cam(28)
    def anim(t):
        caravan(camels, t + 49, y0=10)
        u = sm(t / 5.0)
        cam.location = V(-60, -110, 45).lerp(V(20, 20, 18), u); tgt.location = V(-20, -40, 0).lerp(V(46, 78, 2), u)
    return anim

def S11():
    rnd, camels = world('dusk'); p = hero()
    yx, yy = 0.0, 30.0; z = ground_z(yx, yy)
    Y = mat('#B9773F', 0.95, key='yakh')
    for i in range(9):
        prim('cylinder', (yx, yy, z + 0.9 + i * 1.6), m=Y, vertices=24, radius=9.5 - i * 1.05, depth=1.7)
    prim('cone', (yx, yy, z + 15.5), m=Y, vertices=24, radius1=1.2, depth=1.6)
    prim('cube', (yx - 14, yy + 2, z + 5), scale=(10, 1.4, 10), m=mat('#A9693A', 0.95), size=1)
    prim('cube', (yx, yy - 9.6, z + 1.2), scale=(1.4, 0.4, 2.4), m=mat('#2A1A0E', 0.9, key='hole'), size=1)
    cam, tgt = make_cam(28)
    def anim(t):
        caravan(camels, t + 54, y0=60)
        k = min(t / 3.0, 1.0)
        p.pose(pos=(0.5, 8 + 4 * sm(t / 4), 0), yaw=PI, walk=sm(t / 4) * 8, amp=0.8 * (1 - sm((t - 3.5) / 0.5)),
               nod=-0.45 * sm((t - 4) / 0.6), wide=sm((t - 4) / 0.4))
        u = sm(t / 9.0)
        cam.location = V(4.0, -2.0, 1.6).lerp(V(1.5, 2.0, 1.0), u); tgt.location = V(0, 30, 6).lerp(V(0, 30, 9), u)
    return anim

# ------------------------------------------------------------------ render
bpy.ops.wm.read_factory_settings(use_empty=True)
lib3d.MATS.clear(); lib3d.OUTLINE = None
anim = globals()[SHOT]()
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
n = int(round(SHOTS[SHOT] * FPS))
for f in range(FSTART, min(FEND, n)):
    anim(f / FPS)
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, 'f%04d.jpg' % f)
    bpy.ops.render.render(write_still=True)
