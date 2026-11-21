# Derinkuyu - Parte 4: "Las otras ciudades bajo Capadocia"
# Escenas 3D low-poly renderizadas con Blender (Eevee).
# Uso: blender -b -P reel.py -- <escena 1-6> <carpeta_salida> [frame_ini] [frame_fin] [ancho]
import bpy, math, random, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SCN = int(argv[0]); OUT = argv[1]
FSTART = int(argv[2]) if len(argv) > 2 else 0
FEND = int(argv[3]) if len(argv) > 3 else 10 ** 6
RESX = int(argv[4]) if len(argv) > 4 else 540
FPS = 24
DUR = {1: 4, 2: 11, 3: 12, 4: 13, 5: 15, 6: 10}
PI = math.pi

# ---------------------------------------------------------------- utilidades
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

MATS = {}
def mat(h, rough=0.85, emit=0.0, alpha=1.0):
    key = f'{h}_{rough}_{emit}_{alpha}'
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    c = (*lin(h), 1)
    b.inputs['Base Color'].default_value = c
    b.inputs['Roughness'].default_value = rough
    if emit > 0:
        b.inputs['Emission Color'].default_value = c
        b.inputs['Emission Strength'].default_value = emit
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'; m.shadow_method = 'NONE'
    MATS[key] = m
    return m

def link(o):
    bpy.context.scene.collection.objects.link(o); return o

def prim(kind, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), m=None, smooth=False, parent=None, **kw):
    getattr(bpy.ops.mesh, 'primitive_%s_add' % kind)(**kw)
    o = bpy.context.object
    if parent: o.parent = parent
    o.location = loc; o.rotation_euler = rot; o.scale = scale
    if m:
        o.data.materials.clear(); o.data.materials.append(m)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    return o

def box(x0, x1, y0, y1, z0, z1, m=None, rot=(0, 0, 0)):
    return prim('cube', ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), rot=rot,
                scale=(x1 - x0, y1 - y0, z1 - z0), m=m, size=1)

def empty(loc=(0, 0, 0), parent=None, name='e'):
    o = link(bpy.data.objects.new(name, None))
    if parent: o.parent = parent
    o.location = loc
    return o

def carve(target, cutter):
    md = target.modifiers.new('b', 'BOOLEAN'); md.operation = 'DIFFERENCE'
    md.object = cutter; md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def arch_cut(target, x0, x1, y0, y1, z0, z1, axis='x'):
    carve(target, box(x0, x1, y0, y1, z0, z1))
    if axis == 'x':
        r = (y1 - y0) / 2
        c = prim('cylinder', ((x0 + x1) / 2, (y0 + y1) / 2, z1), rot=(0, PI / 2, 0), vertices=20, radius=r, depth=x1 - x0)
    else:
        r = (x1 - x0) / 2
        c = prim('cylinder', ((x0 + x1) / 2, (y0 + y1) / 2, z1), rot=(PI / 2, 0, 0), vertices=20, radius=r, depth=y1 - y0)
    carve(target, c)

def plight(loc, power=100, hexc='#FFC27A', radius=0.3, shadow=False):
    d = bpy.data.lights.new('p', 'POINT'); d.energy = power; d.color = lin(hexc)
    d.shadow_soft_size = radius; d.use_shadow = shadow
    o = link(bpy.data.objects.new('p', d)); o.location = loc
    return o

def sm(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def keys(t, ks):
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            u = sm((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return ks[-1][1]

def spline(t, ks):
    """Catmull-Rom suave (sin paradas) entre puntos (tiempo, vector)."""
    if t <= ks[0][0]: return Vector(ks[0][1])
    if t >= ks[-1][0]: return Vector(ks[-1][1])
    for i in range(len(ks) - 1):
        if ks[i][0] <= t <= ks[i + 1][0]: break
    p0 = Vector(ks[max(i - 1, 0)][1]); p1 = Vector(ks[i][1]); p2 = Vector(ks[i + 1][1]); p3 = Vector(ks[min(i + 2, len(ks) - 1)][1])
    u = (t - ks[i][0]) / (ks[i + 1][0] - ks[i][0])
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

def shake(t, t0, t1, amp):
    if t < t0 or t > t1: return Vector((0, 0, 0))
    k = amp * (1 - (t - t0) / (t1 - t0))
    return Vector((math.sin(t * 71) * k, math.sin(t * 53 + 1) * k * 0.5, math.sin(t * 89 + 2) * k))

# ---------------------------------------------------------------- escena / cámara
def setup(world='#9ED6FF', strength=0.75, sun=True, sun_rot=(50, 0, 25), sun_power=2.5):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = RESX; sc.render.resolution_y = RESX * 16 // 9
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    e = sc.eevee
    e.taa_render_samples = 10; e.use_gtao = True; e.gtao_distance = 1.2
    e.use_soft_shadows = True; e.shadow_cascade_size = '2048'; e.shadow_cube_size = '512'
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 93
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*lin(world), 1); bg.inputs[1].default_value = strength
    if sun:
        d = bpy.data.lights.new('sun', 'SUN'); d.energy = sun_power; d.angle = math.radians(4)
        d.color = (1.0, 0.96, 0.9); d.shadow_cascade_max_distance = 90
        o = link(bpy.data.objects.new('sun', d))
        o.rotation_euler = tuple(math.radians(a) for a in sun_rot)

def make_cam(lens=28):
    cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.clip_start = 0.05; cd.clip_end = 600
    cam = link(bpy.data.objects.new('cam', cd))
    tgt = empty(name='tgt')
    c = cam.constraints.new('TRACK_TO'); c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam, tgt

# ---------------------------------------------------------------- personaje
class Hero:
    def __init__(s):
        W = mat('#F8F8F4', 0.4); K = mat('#1E1E24', 0.55); KG = mat('#141418', 0.12)
        BL = mat('#2F7FE8', 0.65); HL = mat('#FFFFFF', 0.3, emit=2.0)
        s.root = empty(name='hero')
        s.pelvis = empty((0, 0, 0.80), s.root)
        s.chest = empty((0, 0, 0.05), s.pelvis)
        prim('uv_sphere', (0, 0, 0), scale=(0.215, 0.16, 0.14), m=K, smooth=True, parent=s.pelvis, segments=16, ring_count=10, radius=1)
        prim('uv_sphere', (0, 0, 0.22), scale=(0.235, 0.175, 0.30), m=BL, smooth=True, parent=s.chest, segments=18, ring_count=12, radius=1)
        s.neck = empty((0, 0, 0.50), s.chest)
        prim('cylinder', (0, 0, 0.04), m=K, smooth=True, parent=s.neck, vertices=10, radius=0.035, depth=0.14)
        s.head = empty((0, 0, 0.30), s.neck)
        prim('uv_sphere', (0, 0, 0), m=W, smooth=True, parent=s.head, segments=32, ring_count=20, radius=0.34)
        s.eyes = []; s.brows = []
        for sx in (1, -1):
            ex = 0.12 * sx
            s.eyes.append(prim('uv_sphere', (ex, -0.300, 0.04), scale=(0.072, 0.04, 0.10), m=KG, smooth=True, parent=s.head, segments=16, ring_count=10, radius=1))
            prim('uv_sphere', (ex + 0.025, -0.336, 0.085), m=HL, smooth=True, parent=s.head, segments=8, ring_count=6, radius=0.022)
            bp = empty((ex, -0.262, 0.19), s.head)
            prim('cylinder', (0, 0, 0), rot=(0, PI / 2, 0), m=K, smooth=True, parent=bp, vertices=8, radius=0.015, depth=0.11)
            s.brows.append((bp, sx))
        s.mouth = prim('uv_sphere', (0, -0.312, -0.13), scale=(0.055, 0.03, 0.018), m=K, smooth=True, parent=s.head, segments=12, ring_count=8, radius=1)
        s.sh = {}; s.el = {}; s.hand = {}; s.hip = {}; s.knee = {}
        for side, sx in (('L', 1), ('R', -1)):
            sh = empty((0.25 * sx, 0, 0.42), s.chest)
            prim('uv_sphere', (0, 0, 0), m=BL, smooth=True, parent=sh, segments=12, ring_count=8, radius=0.085)
            prim('cylinder', (0, 0, -0.15), m=K, smooth=True, parent=sh, vertices=8, radius=0.034, depth=0.30)
            el = empty((0, 0, -0.30), sh)
            prim('cylinder', (0, 0, -0.14), m=K, smooth=True, parent=el, vertices=8, radius=0.032, depth=0.28)
            prim('uv_sphere', (0, 0, -0.30), m=K, smooth=True, parent=el, segments=10, ring_count=8, radius=0.055)
            s.hand[side] = empty((0, 0, -0.32), el)
            s.sh[side] = sh; s.el[side] = el
            hp = empty((0.10 * sx, 0, -0.02), s.pelvis)
            prim('cylinder', (0, 0, -0.18), m=K, smooth=True, parent=hp, vertices=8, radius=0.045, depth=0.36)
            kn = empty((0, 0, -0.36), hp)
            prim('cylinder', (0, 0, -0.17), m=K, smooth=True, parent=kn, vertices=8, radius=0.042, depth=0.34)
            prim('uv_sphere', (0, -0.045, -0.37), scale=(0.065, 0.115, 0.045), m=K, smooth=True, parent=kn, segments=12, ring_count=8, radius=1)
            s.hip[side] = hp; s.knee[side] = kn

    def pose(s, pos=(0, 0, 0), yaw=0.0, walk=0.0, amp=0.0, lean=0.0, twist=0.0, nod=0.0, turn=0.0, tilt=0.0,
             armL=None, armR=None, mouth=0.0, worry=0.0, browup=0.0, crouch=0.0, wide=0.0):
        s.root.location = pos; s.root.rotation_euler = (0, 0, yaw)
        p = walk; a = amp
        hl = -0.6 * a * math.sin(p); hr = -hl
        kl = 0.9 * a * max(0.0, math.cos(p)); kr = 0.9 * a * max(0.0, -math.cos(p))
        hl -= 0.9 * crouch; hr -= 0.9 * crouch; kl += 1.6 * crouch; kr += 1.6 * crouch
        s.hip['L'].rotation_euler = (hl, 0, 0); s.hip['R'].rotation_euler = (hr, 0, 0)
        s.knee['L'].rotation_euler = (kl, 0, 0); s.knee['R'].rotation_euler = (kr, 0, 0)
        drop = 0.72 - (0.36 * math.cos(0.9 * crouch) + 0.36 * math.cos(0.7 * crouch))
        bob = 0.035 * a * abs(math.cos(p))
        s.pelvis.location = (0, 0, 0.80 - drop + bob)
        s.chest.rotation_euler = (lean + 0.06 * a, 0, twist)
        s.neck.rotation_euler = (nod, tilt, turn)
        defL = (0.4 * a * math.sin(p), -0.08, 0, -0.25 - 0.2 * a)
        defR = (-0.4 * a * math.sin(p), 0.08, 0, -0.25 - 0.2 * a)
        for side, arm in (('L', armL or defL), ('R', armR or defR)):
            s.sh[side].rotation_euler = arm[:3]
            s.el[side].rotation_euler = (arm[3], 0, 0)
        s.mouth.scale = (0.055 - 0.012 * mouth, 0.03, 0.018 + 0.062 * mouth)
        for bp, sx in s.brows:
            bp.rotation_euler = (0, sx * 0.45 * worry, 0)
            bp.location.z = 0.19 + 0.045 * browup
        for e in s.eyes:
            e.scale = (0.072 * (1 + 0.1 * wide), 0.04, 0.10 * (1 + 0.22 * wide))

    def hand_pos(s, side):
        bpy.context.view_layer.update()
        return s.hand[side].matrix_world.translation.copy()

# ---------------------------------------------------------------- decorado
SAND = '#E3C08C'; ROCK = '#EBD3AA'; CAP = '#A0714F'; GREEN = '#8FC255'; DGREEN = '#6FA23F'

def chimney(x, y, rnd, scale=1.0):
    h = rnd.uniform(3, 7) * scale; r = rnd.uniform(0.7, 1.3) * scale
    prim('cone', (x, y, h / 2), rot=(0, 0, rnd.uniform(0, 6)), m=mat(ROCK), vertices=7, radius1=r, radius2=r * 0.32, depth=h)
    prim('cone', (x, y, h + 0.2 * r), rot=(0, 0, rnd.uniform(0, 6)), m=mat(CAP), vertices=7, radius1=r * 0.62, radius2=r * 0.08, depth=0.8 * r)

def bush(x, y, s=0.45, z=0.0):
    return prim('ico_sphere', (x, y, z + s * 0.6), scale=(s, s, s * 0.8), m=mat(GREEN), subdivisions=1, radius=1)

def stone(x, y, s, rnd, hexc='#DCC199', z=None):
    return prim('ico_sphere', (x, y, s * 0.35 if z is None else z), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3)),
                scale=(s, s * 0.85, s * 0.65), m=mat(hexc), subdivisions=1, radius=1)

def cmat():
    m = mat('#FFFFFF', 0.95, emit=0.35); m.shadow_method = 'NONE'; return m

def cloud(x, y, z, s, rnd):
    for i in range(5):
        prim('ico_sphere', (x + (i - 2) * s * 0.75, y + rnd.uniform(-0.3, 0.3) * s, z + rnd.uniform(-0.2, 0.3) * s),
             m=cmat(), subdivisions=1, radius=s * rnd.uniform(0.6, 1.0) * (1.2 if i == 2 else 1)).visible_shadow = False

def hill(x, y, r, h, hexc='#DDC193', verts=9):
    return prim('cone', (x, y, h / 2 - 0.3), m=mat(hexc), vertices=verts, radius1=r, radius2=r * 0.25, depth=h)

def scenery(rnd, ymin=6, ymax=60, n=30, xspan=40, clouds=True):
    for _ in range(n):
        chimney(rnd.uniform(-xspan, xspan), rnd.uniform(ymin, ymax), rnd)
    for _ in range(n):
        bush(rnd.uniform(-xspan, xspan), rnd.uniform(ymin - 3, ymax), rnd.uniform(0.3, 0.6))
    for i in range(6):
        hill(rnd.uniform(-70, 70), rnd.uniform(80, 120), rnd.uniform(18, 30), rnd.uniform(8, 16), rnd.choice(['#DCC08F', '#D3B486', '#C9D99A']))
    if clouds:
        for _ in range(7):
            cloud(rnd.uniform(-40, 40), rnd.uniform(50, 90), rnd.uniform(16, 30), rnd.uniform(2, 3.5), rnd)

class Burst:
    def __init__(s, center, n, t0, dur, speed, size, hexc='#EFE0C4', up=1.0, spread=1.0, seed=0, grav=1.0):
        rnd = random.Random(seed); s.p = []
        m = mat(hexc, 0.95)
        for _ in range(n):
            o = prim('ico_sphere', center, m=m, subdivisions=1, radius=1); o.scale = (0, 0, 0)
            v = Vector((rnd.uniform(-1, 1) * spread, rnd.uniform(-1, 1) * spread, rnd.uniform(0.2, 1) * up))
            v = v.normalized() * speed * rnd.uniform(0.4, 1.0)
            s.p.append((o, v, size * rnd.uniform(0.5, 1.3)))
        s.c = Vector(center); s.t0 = t0; s.dur = dur; s.g = grav

    def update(s, t):
        u = t - s.t0
        for o, v, sz in s.p:
            if u < 0 or u > s.dur:
                o.scale = (0, 0, 0); continue
            k = u / s.dur
            o.location = s.c + v * (u * (1 - 0.45 * k)) + Vector((0, 0, -0.5 * s.g * u * u))
            g = sz * (1 - k) * min(1.0, u * 10) * (1 + k)
            o.scale = (g, g, g)

# ---------------------------------------------------------------- corte transversal (rejilla)
STRATA = ['#ECD7B2', '#E4C79E', '#DBB88C', '#E8CEA6', '#D6AE80', '#E2C297']

def cutaway(x0, x1, z0, z1, cell, yf, depth, shapes, inner='#F2D3A2', top='#C9A57A'):
    def carved(x, z):
        for sh in shapes:
            if sh[0] == 'r':
                if sh[1] <= x <= sh[2] and sh[3] <= z <= sh[4]: return True
            else:
                _, a0, a1, b0, b1, ah = sh
                if a0 <= x <= a1 and b0 <= z <= b1: return True
                if a0 <= x <= a1 and b1 < z <= b1 + ah:
                    cx = (a0 + a1) / 2; hw = (a1 - a0) / 2
                    if ((x - cx) / hw) ** 2 + ((z - b1) / ah) ** 2 <= 1: return True
        return False
    nx = round((x1 - x0) / cell); nz = round((z1 - z0) / cell)
    C = [[carved(x0 + (i + .5) * cell, z0 + (k + .5) * cell) for k in range(nz)] for i in range(nx)]
    verts = []; vid = {}
    def V(i, k, b):
        key = (i, k, b)
        if key not in vid:
            vid[key] = len(verts); verts.append((x0 + i * cell, yf + b * depth, z0 + k * cell))
        return vid[key]
    faces = []; mi = []
    mats = [mat(h) for h in STRATA] + [mat(inner, 0.9), mat(top)]
    INNER = len(STRATA); TOP = INNER + 1
    for i in range(nx):
        for k in range(nz):
            z = z0 + (k + .5) * cell; x = x0 + (i + .5) * cell
            if not C[i][k]:
                faces.append((V(i, k, 0), V(i + 1, k, 0), V(i + 1, k + 1, 0), V(i, k + 1, 0)))
                if z > z1 - 0.5: mi.append(TOP)
                else: mi.append(int((-(z) + 0.8 * math.sin(x * 0.3)) / 3.3) % len(STRATA))
            else:
                faces.append((V(i, k, 1), V(i + 1, k, 1), V(i + 1, k + 1, 1), V(i, k + 1, 1))); mi.append(INNER)
                if i == 0 or not C[i - 1][k]: faces.append((V(i, k, 0), V(i, k + 1, 0), V(i, k + 1, 1), V(i, k, 1))); mi.append(INNER)
                if i == nx - 1 or not C[i + 1][k]: faces.append((V(i + 1, k, 0), V(i + 1, k + 1, 0), V(i + 1, k + 1, 1), V(i + 1, k, 1))); mi.append(INNER)
                if k == 0 or not C[i][k - 1]: faces.append((V(i, k, 0), V(i + 1, k, 0), V(i + 1, k, 1), V(i, k, 1))); mi.append(INNER)
                if k == nz - 1 or not C[i][k + 1]: faces.append((V(i, k + 1, 0), V(i + 1, k + 1, 0), V(i + 1, k + 1, 1), V(i, k + 1, 1))); mi.append(INNER)
    me = bpy.data.meshes.new('cut'); me.from_pydata(verts, [], faces); me.update()
    for m in mats: me.materials.append(m)
    me.polygons.foreach_set('material_index', mi)
    return link(bpy.data.objects.new('cut', me))

class Shapes:
    def __init__(s): s.list = []; s.rooms = []
    def R(s, x0, x1, z0, z1): s.list.append(('r', x0, x1, z0, z1))
    def A(s, x0, x1, z0, z1, ah): s.list.append(('a', x0, x1, z0, z1, ah))
    def room(s, x0, x1, z0, h, ah=0.7):
        s.A(x0, x1, z0, z0 + h, ah); s.rooms.append((x0, x1, z0, h))
    def stairs(s, xa, za, xb, zb, h=1.9, w=0.8):
        n = max(2, int(abs(xb - xa) / 0.25))
        for j in range(n + 1):
            x = xa + (xb - xa) * j / n; z = za + (zb - za) * j / n
            s.R(x - w / 2, x + w / 2, z, z + h)

def city(S, cx, ztop, nlev, rnd, half=3.8):
    floor = ztop
    for L in range(nlev):
        x0 = cx - half * rnd.uniform(0.75, 1.0); x1 = cx + half * rnd.uniform(0.75, 1.0)
        S.R(x0, x1, floor, floor + 1.6)
        for _ in range(rnd.randint(1, 2)):
            w = rnd.uniform(1.6, 2.6); rx = rnd.uniform(x0, x1 - w)
            S.room(rx, rx + w, floor, 2.1, 0.6)
        if L < nlev - 1:
            nf = floor - 3.6; dirn = rnd.choice([-1, 1])
            sx = cx - dirn * 1.6
            S.stairs(sx, nf, sx + dirn * 3.2, floor - 0.2)
            floor = nf

def props_in_rooms(S, yf, rnd, maxn=60):
    clay = mat('#C9763F', 0.7); clay2 = mat('#B5603A', 0.7)
    for (x0, x1, z0, h) in S.rooms[:maxn]:
        for _ in range(rnd.randint(1, 3)):
            x = rnd.uniform(x0 + 0.3, x1 - 0.3); y = yf + rnd.uniform(1.2, 2.6); r = rnd.uniform(0.14, 0.22)
            m = rnd.choice([clay, clay2])
            prim('cylinder', (x, y, z0 + r * 1.2), m=m, vertices=8, radius=r, depth=r * 2.4)
            prim('uv_sphere', (x, y, z0 + r * 2.4), scale=(r * 0.9, r * 0.9, r * 0.6), m=m, segments=8, ring_count=6, radius=1)
        plight(((x0 + x1) / 2, yf + 1.3, z0 + h * 0.7), power=70, radius=0.4)

# ================================================================ ESCENA 1
def scene1():
    setup()
    rnd = random.Random(11)
    yf = -3.0
    S = Shapes()
    city(S, -4.8, -4.0, 3, rnd)
    city(S, 4.6, -9.5, 3, rnd)
    city(S, -1.5, -19.5, 2, rnd, half=4.5)
    S.R(-5.2, -4.6, -2.4, 0)          # pozo desde la superficie
    S.R(4.3, 4.9, -7.9, -2.0)          # ventilación
    S.R(-6.5, -6.0, -13, -9)
    cut = cutaway(-14, 14, -34, 0, 0.25, yf, 3.0, S.list)
    props_in_rooms(S, yf, rnd)
    prim('plane', (0, yf + 150, 0), m=mat(SAND), size=300)
    scenery(rnd, ymin=5)
    for _ in range(10): bush(rnd.uniform(-6, 6), rnd.uniform(-2.5, 4), rnd.uniform(0.25, 0.4))
    # tapa de tierra que se cae
    cover = box(-40, 40, yf - 0.6, yf, -60, 0, m=mat('#D9BC90'))
    fg = prim('plane', (0, yf - 0.6 - 100, 0), m=mat(SAND), size=200)
    fgb = [bush(rnd.uniform(-8, 8), rnd.uniform(-12, -4.5), 0.35) for _ in range(6)]
    hero = Hero(); cam, tgt = make_cam(28)
    hp = (0.0, -2.1, 0.0)

    def anim(t):
        fall = 0.0 if t < 1.0 else -22.0 * (t - 1.0) ** 2
        cover.location.z = -30 + fall; fg.location.z = fall
        cover.rotation_euler.x = 0 if t < 1 else -0.25 * (t - 1)
        for o in fgb: o.location.z = 0.27 + fall  # arbustos con el suelo
        shock = sm((t - 0.35) / 0.3)
        point = sm((t - 0.55) / 0.35)
        hero.pose(pos=hp, yaw=0, turn=keys(t, [(0, 0.35), (0.4, -0.2), (0.7, 0)]),
                  nod=0.35 * point, lean=0.15 * point,
                  armR=(-0.9 * point, 0.08 - 0.25 * point, 0, -0.25 * (1 - point)),
                  armL=(0.0, -0.08 - 0.5 * shock, 0, -0.25 - 1.2 * shock),
                  mouth=shock, browup=shock, wide=shock)
        sh = shake(t, 0.9, 1.6, 0.12)
        p = spline(t, [(0, (0.6, -7.4, 1.9)), (1.0, (0.4, -8.4, 1.6)), (2.2, (0.2, -16, -2.0)), (4.0, (0.0, -27, -6.5))])
        g = spline(t, [(0, (0, -2.1, 1.45)), (1.0, (0, -2.1, 1.2)), (2.2, (0, -3, -5)), (4.0, (0, -3, -10.5))])
        cam.location = p + sh; tgt.location = g
    return anim

# ================================================================ ESCENA 2
def scene2():
    setup()
    rnd = random.Random(22)
    prim('plane', (0, 0, 0), m=mat(SAND), size=400)
    for _ in range(18):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(18, 34)
        chimney(r * math.cos(a), r * math.sin(a), rnd)
    for _ in range(40):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(4, 30)
        bush(r * math.cos(a), r * math.sin(a), rnd.uniform(0.25, 0.5))
    for _ in range(25):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(3, 25)
        stone(r * math.cos(a), r * math.sin(a), rnd.uniform(0.15, 0.4), rnd)
    for i in range(10):
        a = i / 10 * 2 * PI; hill(70 * math.cos(a), 70 * math.sin(a), rnd.uniform(18, 28), rnd.uniform(8, 15), rnd.choice(['#DCC08F', '#D3B486', '#C9D99A']))
    for _ in range(8): cloud(rnd.uniform(-50, 50), rnd.uniform(-50, 50), rnd.uniform(18, 26), rnd.uniform(2, 3.5), rnd)
    ents = []
    n = 15
    for i in range(n):
        a = -PI / 2 + (i * 2.39996) % (2 * PI)  # ángulo dorado
        rad = 3.6 + i * 0.75
        big = i >= 11
        r = rnd.uniform(2.0, 2.8) if big else rnd.uniform(0.6, 1.25)
        pos = (rad * math.cos(a), rad * math.sin(a), 0)
        if big: pos = ((rad + 3) * math.cos(a), (rad + 3) * math.sin(a), 0)
        e = empty(pos)
        prim('cylinder', (0, 0, 0.02), m=mat('#6E4B31', 0.95), parent=e, vertices=14, radius=1, depth=0.03)
        prim('cylinder', (0, 0, 0.03), m=mat('#8A6240', 0.95), parent=e, vertices=14, radius=0.8, depth=0.03, scale=(1, 1, 1))
        prim('torus', (0, 0, 0.03), m=mat('#D8BD92'), parent=e, major_segments=14, minor_segments=5, major_radius=1.05, minor_radius=0.13)
        for j in range(3):
            prim('cube', (0, 0.55 - j * 0.28, 0.045 - j * 0.004), m=mat('#B98E63'), parent=e, size=1, scale=(0.7, 0.22, 0.02))
        e.rotation_euler.z = math.atan2(-pos[1], -pos[0]) + PI / 2
        t0 = 0.8 + i * 0.58
        ents.append((e, r, t0, pos, Burst((pos[0], pos[1], 0.1), 10, t0, 0.9, 2.2 * r ** 0.5, 0.16 * r ** 0.5, seed=i, up=1.2)))
    hero = Hero(); cam, tgt = make_cam(28)

    def anim(t):
        cur = None
        for e, r, t0, pos, b in ents:
            u = t - t0
            if u <= 0: s = 0.0
            elif u < 0.35: s = sm(u / 0.35) * 1.15
            elif u < 0.55: s = 1.15 - 0.15 * sm((u - 0.35) / 0.2)
            else: s = 1.0
            e.scale = (r * s + 1e-4, r * s + 1e-4, 1)
            b.update(t)
            if u > -0.2: cur = pos
        look = math.atan2(cur[0], -cur[1]) if cur else 0.0
        # el cuerpo sigue al último agujero (suavizado)
        body = keys(t, [(0, 0.0), (11, 0.0)])
        yaw_target = look
        hero_yaw = getattr(anim, 'yaw', 0.0)
        d = (yaw_target - hero_yaw + PI) % (2 * PI) - PI
        hero_yaw += d * 0.12
        anim.yaw = hero_yaw
        count = sm((t - 5.0) / 0.5) * (1 - sm((t - 9.6) / 0.5))
        bounce = 0.25 * max(0, math.sin((t - 5.0) / 0.58 * PI)) * count
        amazed = sm((t - 0.9) / 0.5)
        hero.pose(pos=(0, 0, 0), yaw=hero_yaw, mouth=0.6 * amazed, browup=amazed, wide=amazed,
                  armR=(-0.35 - 0.3 * count, 0.08 + 0.1 * count, 0, -0.25 - 1.5 * count - bounce),
                  armL=(0.0, -0.08 - 0.25 * amazed * (1 - count), 0, -0.25 - 0.4 * amazed),
                  nod=-0.12 * count + 0.1 * (1 - count), turn=0.0)
        ang = math.radians(-100 + t * 10.5)
        R = 9.5 + t * 0.45; h = 5.5 + t * 0.4
        cam.location = (R * math.cos(ang), R * math.sin(ang), h)
        tgt.location = (0, 0, 0.9)
    anim.yaw = 0.0
    return anim

# ================================================================ ESCENA 3
def scene3():
    setup(sun_rot=(52, 0, -35))
    rnd = random.Random(33)
    G = box(-60, 60, -60, 80, -5, 0, m=mat(SAND))
    carve(G, box(-1.3, 1.3, -1.25, 0.25, -2.3, 0.5))
    carve(G, box(-0.75, 0.75, -0.5, 9, -2.3, -0.95))
    carve(G, prim('cylinder', (0, 4.2, -0.95), rot=(PI / 2, 0, 0), vertices=18, radius=0.75, depth=9.4))
    plight((0, 2.0, -1.5), power=260, radius=0.5, hexc='#FFC983')
    plight((0, 5.5, -1.5), power=200, radius=0.5, hexc='#FFC983')
    plight((0, -0.4, -1.6), power=60, radius=0.4, hexc='#FFD6A0')
    # tapa (4 piezas) sobre el hoyo
    lids = []
    for i, (a0, a1) in enumerate([(-1.3, 0.0), (0.0, 1.3)]):
        for j, (b0, b1) in enumerate([(-1.25, -0.5), (-0.5, 0.25)]):
            o = box(a0 + 0.01, a1 - 0.01, b0 + 0.01, b1 - 0.01, -0.14, 0.0, m=mat(SAND))
            lids.append((o, Vector(o.location), (i - 0.5, j - 0.5)))
    cracks = [box(-1.3, 1.3, -0.52, -0.48, -0.005, 0.012, m=mat('#7A5A3E')), box(-0.02, 0.02, -1.25, 0.25, -0.005, 0.012, m=mat('#7A5A3E'))]
    # casa vieja medio derrumbada
    sto = [mat('#E3CFAA'), mat('#D8C098'), mat('#EAD9B8')]
    mort = mat('#B9A07C')
    box(-3.0, 3.0, 0.32, 0.62, 0, 2.9, m=mort); box(-3.0, -2.7, 0.3, 4.4, 0, 2.9, m=mort); box(2.7, 3.0, 0.3, 4.4, 0, 1.6, m=mort)
    box(-3.0, 3.0, 4.1, 4.4, 0, 2.9, m=mort)
    for row in range(6):
        for col in range(10):
            x = -3.0 + col * 0.6 + (0.3 if row % 2 else 0); z = row * 0.5
            if x > 2.7: continue
            if row >= 3 and x > 0.3 + rnd.uniform(-0.6, 0.6): continue
            if rnd.random() < 0.06: continue
            box(x + 0.02, x + 0.58, 0.25, 0.66, z + 0.02, z + 0.48, m=rnd.choice(sto))
    for k in range(4):
        box(-2.6 + k * 1.3, -2.45 + k * 1.3, 0.35, 4.4, 2.9, 3.05, m=mat('#8C6545'), rot=(0, 0, 0))
    for k in range(10):
        stone(rnd.uniform(1.0, 3.5), rnd.uniform(-0.2, 0.2) - 0.3 + rnd.uniform(-1, 0.2), rnd.uniform(0.15, 0.3), rnd, '#DCC69F')
    stones = []
    for (x, y) in [(-0.55, -0.95), (0.15, -0.98), (0.75, -0.92)]:
        stones.append((stone(x, y, 0.2, rnd, '#E0C9A0', z=0.14), Vector((x, y, 0.14))))
    # otras casas, colina con castillo
    for (x, y, w, d, h) in [(-9, 4, 3.5, 3, 2.6), (-14, 9, 4, 3.2, 3.2), (8, 6, 3.6, 3, 2.4), (12, 12, 4, 3, 3.0), (-6, 14, 3, 3, 2.8)]:
        box(x - w / 2, x + w / 2, y - d / 2, y + d / 2, 0, h, m=mat(rnd.choice(['#F1E4C8', '#EBD6B3', '#F4ECDA'])))
        box(x - w / 2 - 0.1, x + w / 2 + 0.1, y - d / 2 - 0.1, y + d / 2 + 0.1, h, h + 0.2, m=mat('#D9C29C'))
    hill(4, 34, 17, 10, '#D8BE8E', verts=10)
    cz = 9.6; C = mat('#E8D6B4')
    box(0.5, 7.5, 31, 37, cz, cz + 3, m=C)
    for (tx, ty) in [(0.5, 31), (7.5, 31), (0.5, 37), (7.5, 37)]:
        prim('cylinder', (tx, ty, cz + 2.2), m=C, vertices=10, radius=1.0, depth=4.4)
        for q in range(6):
            a = q / 6 * 2 * PI
            box(tx + math.cos(a) * 0.85 - 0.15, tx + math.cos(a) * 0.85 + 0.15, ty + math.sin(a) * 0.85 - 0.15, ty + math.sin(a) * 0.85 + 0.15, cz + 4.4, cz + 4.8, m=C)
    for q in range(8):
        box(1.2 + q * 0.8, 1.5 + q * 0.8, 30.85, 31.15, cz + 3, cz + 3.4, m=C)
    scenery(rnd, ymin=18, ymax=70, n=22, xspan=45)
    for _ in range(12): bush(rnd.uniform(-8, 8), rnd.uniform(-8, -2), rnd.uniform(0.25, 0.45))
    dust = Burst((0, -0.5, 0.0), 45, 5.95, 2.2, 2.6, 0.22, seed=5, up=1.4, spread=1.2, grav=0.6)
    hero = Hero(); cam, tgt = make_cam(28)

    def anim(t):
        # 3 piedras: agacharse, coger, lanzar a la izquierda
        hx = -0.55; crouch = lean = 0.0; arm = None; carrying = None
        for i, (so, sp) in enumerate(stones):
            b = i * 1.8
            if t >= b - 0.4: hx = keys(t, [(b - 0.4, [-0.55, 0.15, 0.75][max(i - 1, 0)]), (b + 0.05, sp.x)])
            if b <= t < b + 1.8:
                u = t - b
                down = sm(u / 0.6) * (1 - sm((u - 0.7) / 0.45))
                crouch = 0.55 * down; lean = 0.65 * down
                throw = sm((u - 1.15) / 0.25)
                arm = (-0.9 * down - 1.9 * sm((u - 0.8) / 0.35) * (1 - throw) + 0.4 * throw, 0.08 + 0.3 * throw, 0, -0.3 - 0.9 * sm((u - 0.8) / 0.3) * (1 - throw))
            # posición de la piedra
            if t < b + 0.65: so.location = sp
            elif t < b + 1.35:
                carrying = i
            else:
                u = min(t - (b + 1.35), 0.7)
                start = anim.rel.get(i, sp)
                end = Vector((-3.2 + i * 0.4, -2.6 - i * 0.3, 0.14))
                k = u / 0.7
                pos = start.lerp(end, k); pos.z += 2.2 * k * (1 - k) * 1.2
                if k >= 1: pos = end
                so.location = pos; so.rotation_euler.x = 6 * k
        yawh = PI; posz = 0.0; posy = -1.85; mouth = browup = wide = worry = 0.0; turn = nod = 0.0; armL = None
        # grietas y derrumbe
        crk = sm((t - 5.4) / 0.45)
        cracks[0].scale.x = 2.6 * crk + 1e-4; cracks[1].scale.y = 1.5 * crk + 1e-4
        if t > 5.9:
            for c in cracks: c.location.z = -10
        for o, p0, (di, dj) in lids:
            if t < 5.9: o.location = p0; o.rotation_euler = (0, 0, 0)
            else:
                u = t - 5.9; d = min(1.0, 2.2 * u * u + 0.4 * u)
                o.location = p0 + Vector((0, 0, -2.0 * d))
                o.rotation_euler = (dj * 1.2 * d, -di * 1.2 * d, 0)
        dust.update(t)
        # reacción: salta hacia atrás girando hacia la cámara
        if t >= 5.4:
            look = sm((t - 5.4) / 0.4)
            nod = 0.45 * look; mouth = 0.3 * look
        if t >= 5.95:
            j = sm((t - 5.95) / 0.7)
            posy = -1.85 - 1.4 * j
            posz = 0.6 * math.sin(min(1.0, (t - 5.95) / 0.7) * PI)
            yawh = PI - 2.4 * sm((t - 5.95) / 0.5) * (1 - sm((t - 7.4) / 0.6))
            sc = 1 - sm((t - 7.6) / 0.8) * 0.6
            mouth = sc; browup = sc; wide = sc; nod = 0.0
            arm = (-2.4 * sc, 0.4 * sc, 0, -0.4 * sc); armL = (-2.4 * sc, -0.4 * sc, 0, -0.4 * sc)
        walkp = 0.0; amp = 0.0
        if t >= 7.6:
            k = sm((t - 7.8) / 1.6)
            posy = -3.25 + 0.95 * k
            amp = 0.7 * math.sin(k * PI); walkp = k * 2 * PI
            peer = sm((t - 9.2) / 0.8)
            lean = 0.4 * peer; nod = 0.35 * peer; worry = 0.0; browup = 0.4 * peer; wide = 0.5 * peer; mouth = 0.25 * peer
            arm = (-0.25 * peer, 0.08, 0, -0.6 * peer); armL = (-0.25 * peer, -0.08, 0, -0.6 * peer)
            turn = 0.12 * math.sin(t * 1.6) * peer
        hero.pose(pos=(hx, posy, posz), yaw=yawh, crouch=crouch, lean=lean, armR=arm, armL=armL,
                  mouth=mouth, browup=browup, wide=wide, worry=worry, nod=nod, turn=turn, walk=walkp, amp=amp)
        if carrying is not None:
            so = stones[carrying][0]
            so.location = hero.hand_pos('R') + Vector((0, 0, -0.08))
            anim.rel[carrying] = so.location.copy()
        sh = shake(t, 5.9, 6.6, 0.07)
        p = keys(t, [(0, (-4.6, -6.6, 2.7)), (12, (-1.4, -4.4, 1.25))])
        g = keys(t, [(0, (0, -0.6, 0.8)), (12, (0, 0.4, -1.0))])
        cam.location = Vector(p) + sh; tgt.location = g
    anim.rel = {}
    return anim

# ================================================================ ESCENA 4
def scene4():
    setup(world='#FFDDB0', strength=0.42, sun=False)
    rnd = random.Random(44)
    B = box(-6, 30, -10, 10, -1, 7, m=mat('#E6CBA0'))
    arch_cut(B, -7, 27, -1.15, 1.15, 0, 2.3, 'x')
    arch_cut(B, 3.5, 9.5, 1.8, 6.5, 0, 2.9, 'x')
    arch_cut(B, 5.6, 7.4, 0.6, 2.3, 0, 2.0, 'y')
    arch_cut(B, 10, 17, -8, -2, 0, 3.3, 'x')
    carve(B, prim('cylinder', (13.5, -8.2, 1.8), vertices=16, radius=2.0, depth=3.6))
    arch_cut(B, 12, 15, -2.4, -0.5, 0, 2.2, 'y')
    carve(B, box(20, 30, 1.2, 3.4, 0, 2.3, rot=(0, 0, 0.55)))
    carve(B, box(20, 30, -3.4, -1.2, 0, 2.3, rot=(0, 0, -0.55)))
    for x in (0.5, 2.3, 10.4, 17.5, 19.0):
        for sgn in (1, -1):
            if sgn < 0 and 11.5 < x < 15.5: continue
            carve(B, box(x - 0.35, x + 0.35, sgn * 1.0 - 0.35, sgn * 1.0 + 0.35 + (0.3 if sgn > 0 else -0.3) * 0, 0.9, 1.55))
    for (sx, sy, r) in [(2.0, 0, 0.42), (11.0, 0, 0.42), (19.0, 0, 0.42), (6.5, 4.15, 0.5), (13.5, -5.0, 0.55)]:
        carve(B, prim('cylinder', (sx, sy, 5), vertices=12, radius=r, depth=8))
        if sy != 0:
            prim('cylinder', (sx, sy, 2.6), m=mat('#FFF2D6', 1.0, emit=1.5, alpha=0.07), vertices=12, radius=r * 0.95, depth=5.2)
        plight((sx, sy, 3.4), power=110, hexc='#FFF0D0', radius=0.4)
    for x in range(-4, 27, 5):
        plight((x, 0, 2.6), power=70, radius=0.35)
    plight((6.5, 4.2, 2.2), 160); plight((13.5, -4.5, 2.4), 200); plight((13.5, -7.6, 1.6), 120, hexc='#FFB867')
    plight((24, 4, 1.8), 120); plight((24, -4, 1.8), 120)
    clay = mat('#C9763F', 0.7)
    for (x, y) in [(4.3, 5.8), (4.9, 6.0), (8.6, 5.7), (9.0, 2.7), (4.2, 2.6)]:
        r = rnd.uniform(0.2, 0.3)
        prim('cylinder', (x, y, r * 1.2), m=clay, vertices=8, radius=r, depth=r * 2.4)
        prim('uv_sphere', (x, y, r * 2.4), scale=(r * 0.9, r * 0.9, r * 0.6), m=clay, segments=8, ring_count=6, radius=1)
    box(5.8, 7.4, 4.2, 5.2, 0, 0.8, m=mat('#D4B183'))
    for (x, y) in [(0.5, 1.15), (2.3, 1.15), (17.5, 1.15), (0.5, -1.15), (19.0, -1.15)]:
        prim('cylinder', (x, y, 1.08), m=clay, vertices=8, radius=0.13, depth=0.3)
    COL = mat('#EAD3AC')
    for (x, y) in [(11.6, -3.6), (15.4, -3.6), (11.6, -6.4), (15.4, -6.4)]:
        prim('cylinder', (x, y, 1.7), m=COL, vertices=10, radius=0.28, depth=3.4)
        box(x - 0.4, x + 0.4, y - 0.4, y + 0.4, 3.2, 3.45, m=COL); box(x - 0.38, x + 0.38, y - 0.38, y + 0.38, 0, 0.2, m=COL)
    box(12.6, 14.4, -9.0, -8.3, 0, 1.0, m=mat('#E1C496'))
    box(13.35, 13.65, -8.9, -8.6, 1.0, 1.6, m=mat('#D2AE7E'))
    for k in range(3): box(11.5, 15.5, -2.1 + k * 0.0 - 0.01, -2.0, 0, 0.12, m=mat('#D9BC8E'))
    hero = Hero(); cam, tgt = make_cam(22)
    stride = 0.88

    def hx(t):
        return keys(t, [(0, -1.0), (10.5, 19.3)]) if t < 10.5 else 19.3

    def anim(t):
        x = hx(t); dt = 1 / FPS
        sp = (hx(min(t + dt, 13)) - hx(max(t - dt, 0))) / (2 * dt)
        amp = min(1.0, sp / 1.9)
        phase = (x + 1.0) / stride * PI
        tl = sm((t - 2.6) / 0.6) * (1 - sm((t - 4.6) / 0.6)) * 1.0
        tr = sm((t - 6.0) / 0.6) * (1 - sm((t - 8.2) / 0.6)) * 1.0
        lr = 0.0
        if t > 10.6: lr = keys(t, [(10.6, 0), (11.3, 1.1), (12.2, 1.1), (12.8, -1.0)])
        wow = max(tl, tr)
        hero.pose(pos=(x, 0, 0), yaw=PI / 2, walk=phase, amp=amp, turn=1.0 * tl - 1.0 * tr + lr,
                  nod=-0.15 * wow, mouth=0.45 * wow + 0.3 * (t > 10.6) * sm((t - 10.6) / 0.5), browup=wow + sm((t - 10.6) / 0.5) * 0.6,
                  wide=wow * 0.8 + 0.4 * sm((t - 10.6) / 0.5))
        # cámara: detrás -> pasa por encima -> delante en diagonal
        hz = 1.55
        behind = Vector((x - 3.6, 0.3, 2.05)); front = Vector((x + 2.8, -0.65, 1.75))
        k = sm((t - 6.3) / 2.2)
        p = behind.lerp(front, k); p.z += 1.0 * math.sin(k * PI)
        if t > 10.5:
            p = Vector((19.3 + 2.8, -0.65, 1.75))
        cam.location = p
        tgt.location = Vector((x + 1.6 * (1 - k), 0, hz))
    return anim

# ================================================================ ESCENA 5
def scene5():
    setup(sun_rot=(48, 0, 18), sun_power=2.4)
    rnd = random.Random(55)
    yf = -3.0
    S = Shapes()
    S.A(-4.5, 5.5, -3.8, -1.6, 0.6)                    # túnel del protagonista
    S.rooms.append((-4.5, 5.5, -3.8, 2.4))
    levels = [-3.8 - 4.6 * i for i in range(11)]
    for li, fz in enumerate(levels):
        x = -34.0
        while x < 34:
            L = rnd.uniform(5, 16); g = rnd.uniform(0.8, 4)
            if li == 0 and -6 < x + L / 2 < 7: x += L + g; continue
            S.R(x, min(x + L, 34), fz, fz + rnd.uniform(1.5, 2.0))
            if rnd.random() < 0.6:
                w = rnd.uniform(2, 4.5); rx = rnd.uniform(x, x + max(0.1, L - w))
                S.room(rx, rx + w, fz, rnd.uniform(2.2, 3.0), rnd.uniform(0.5, 0.9))
            x += L + g
        if li < len(levels) - 1:
            for _ in range(rnd.randint(2, 4)):
                sx = rnd.uniform(-30, 30); d = rnd.choice([-1, 1])
                S.stairs(sx, fz - 4.6, sx + d * 3.6, fz - 0.15)
            for _ in range(rnd.randint(1, 3)):
                vx = rnd.uniform(-30, 30); S.R(vx - 0.35, vx + 0.35, fz - 4.6, fz + 0.5)
    S.stairs(5.0, -3.8, 8.5, -0.1, w=0.8)              # salida hacia la superficie
    S.R(-0.9, -0.3, -8.4, -3.5)
    cut = cutaway(-34, 34, -58, 0, 0.4, yf, 3.0, S.list)
    props_in_rooms(S, yf, rnd, maxn=45)
    prim('plane', (0, yf + 150, 0), m=mat('#E2CDA5'), size=300)
    # pueblo moderno arriba
    box(-40, 40, yf, yf + 1.2, 0, 0.03, m=mat('#A9A6A0'))
    box(-40, 40, yf + 5.0, yf + 6.2, 0, 0.03, m=mat('#A9A6A0'))
    walls = ['#F3E5C8', '#EBD4B0', '#F6EFDF', '#E6CDB0', '#DCE7EE', '#F2D7C4']
    for row, yc in enumerate([yf + 3.0, yf + 8.5, yf + 12.5, yf + 17]):
        x = -40.0
        while x < 40:
            w = rnd.uniform(1.8, 3.0); d = rnd.uniform(1.8, 2.6); h = rnd.uniform(1.6, 3.6)
            box(x, x + w, yc - d / 2, yc + d / 2, 0, h, m=mat(rnd.choice(walls)))
            if rnd.random() < 0.6:
                prim('cone', (x + w / 2, yc, h + 0.45), rot=(0, 0, PI / 4), scale=(w * 0.75, d * 0.75, 1), m=mat('#C8653C'), vertices=4, radius1=1, radius2=0, depth=0.9)
            else:
                box(x - 0.05, x + w + 0.05, yc - d / 2 - 0.05, yc + d / 2 + 0.05, h, h + 0.15, m=mat('#D7C4A4'))
            for wi in range(int(w / 0.8)):
                box(x + 0.35 + wi * 0.8, x + 0.75 + wi * 0.8, yc - d / 2 - 0.02, yc - d / 2, h * 0.5, h * 0.5 + 0.45, m=mat('#6FA9D8', 0.3))
            x += w + rnd.uniform(0.3, 1.5)
            if rnd.random() < 0.35:
                prim('cylinder', (x - 0.2, yc - 1.6, 0.4), m=mat('#8B6A4A'), vertices=6, radius=0.08, depth=0.8)
                prim('ico_sphere', (x - 0.2, yc - 1.6, 1.1), m=mat(GREEN), subdivisions=1, radius=0.5)
    scenery(rnd, ymin=25, ymax=80, n=14)
    hero = Hero(); cam, tgt = make_cam(28)
    hp = (0.6, -1.7, -3.8)

    def anim(t):
        up = sm((t - 0.6) / 0.8)
        step = sm((t - 3.0) / 1.0)
        hero.pose(pos=(hp[0] - 0.35 * step, hp[1], hp[2]), yaw=0.25, nod=-0.65 * up, worry=up, wide=0.4 * up, mouth=0.25 * up,
                  armL=(-0.3 * up, -0.2 * up, 0, -1.2 * up), armR=(-0.2 * up, 0.15 * up, 0, -1.0 * up),
                  turn=0.2 * math.sin(t * 1.3) * up, walk=step * PI, amp=0.3 * math.sin(step * PI))
        p = spline(t, [(0, (1.6, -6.0, -2.2)), (2.5, (1.3, -7.2, -2.4)), (6, (0.6, -20, -5.5)), (10, (0.2, -42, -12)), (15, (0, -62, -17))])
        g = spline(t, [(0, (0.6, -1.7, -2.1)), (2.5, (0.6, -1.7, -2.0)), (6, (0.4, -3, -5)), (10, (0.2, -3, -12)), (15, (0, -3, -17))])
        cam.location = p; tgt.location = g
    return anim

# ================================================================ ESCENA 6
def scene6():
    setup(world='#FFDDB0', strength=0.42, sun=False)
    B = box(-5, 5, -14, 24, -1, 6, m=mat('#E6CBA0'))
    arch_cut(B, -1.3, 1.3, -15, 25, 0, 2.2, 'y')
    carve(B, box(1.0, 2.4, -1.7, 2.0, 0, 3.4))
    for y in (-8, -3, 3.5, 9, 15):
        plight((0, y, 2.6), power=120, radius=0.35)
    plight((0.2, -2.8, 2.0), power=70, hexc='#FFE8C8', radius=0.8)
    lg = prim('plane', (0, 23.9, 1.6), rot=(PI / 2, 0, 0), m=mat('#FFF7E6', 1.0, emit=3.0), size=5)
    plight((0, 21, 1.6), power=500, hexc='#FFF4DC', radius=1.0)
    D = mat('#C9BBA2', 0.9)
    door = prim('cylinder', (1.45, 0.25, 1.55), rot=(0, PI / 2, 0), m=D, vertices=18, radius=1.55, depth=0.5)
    prim('cylinder', (1.18, 0.25, 1.55), rot=(0, PI / 2, 0), m=mat('#8F7A5E'), vertices=12, radius=0.28, depth=0.06)
    for k in range(5):
        a = k / 5 * 2 * PI
        prim('cube', (1.19, 0.25 + 1.0 * math.cos(a), 1.55 + 1.0 * math.sin(a)), m=mat('#B5A68B'), size=0.12)
    rnd = random.Random(6)
    for _ in range(8): stone(rnd.uniform(-1.1, 1.1), rnd.uniform(-10, 12), rnd.uniform(0.08, 0.18), rnd, '#D2B78E')
    hero = Hero(); cam, tgt = make_cam(30)
    hp = (-0.25, 0.4, 0)

    def anim(t):
        back = sm((t - 0.8) / 0.9) * (1 - sm((t - 4.6) / 0.9))
        face = sm((t - 4.6) / 0.9)
        hero.pose(pos=hp, yaw=0.0, twist=0.7 * back, turn=1.5 * back + 0.12 * face, tilt=-0.15 * face,
                  nod=-0.05 * back, worry=0.6 * back, wide=0.3 * back + 0.9 * face, browup=0.9 * face,
                  mouth=0.2 * back + 0.35 * face,
                  armL=(-0.2 * back, -0.25 * back, 0, -0.7 * back), armR=(-0.1, 0.12, 0, -0.35))
        k = sm((t - 1.0) / 8.5)
        p = Vector((0.2, -5.2, 1.45)).lerp(Vector((-0.2, -1.35, 1.65)), k)
        g = Vector((0.4, 0.6, 1.25)).lerp(Vector((-0.25, 0.4, 1.62)), k)
        cam.location = p; tgt.location = g
    return anim

# ================================================================ render
bpy.ops.wm.read_factory_settings(use_empty=True)
anim = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6}[SCN]()
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
n = int(round(DUR[SCN] * FPS))
for f in range(FSTART, min(FEND, n)):
    anim(f / FPS)
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, 'f%04d.jpg' % f)
    bpy.ops.render.render(write_still=True)
