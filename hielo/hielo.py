# "El congelador de 2.000 años" (yakhchal) — explicativo problema→solución en un desierto 3D.
# Uso: blender -b -P hielo.py -- <toma> <carpeta_salida> [ancho] [frame_ini] [frame_fin]
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'sahara'))
import bpy, bmesh, math, random
from mathutils import Vector
import lib3d
from lib3d import *
import sahara as SA
from people import Person, outlined

argv = sys.argv[sys.argv.index('--') + 1:]
SHOT = argv[0]; OUT = argv[1]
RESX = int(argv[2]) if len(argv) > 2 else 540
FSTART = int(argv[3]) if len(argv) > 3 else 0
FEND = int(argv[4]) if len(argv) > 4 else 10 ** 6
PI = math.pi; FPS = 24
CUTS = [('H', 0.0), ('A1', 8.5), ('A2', 13.8), ('A3', 17.7), ('A4', 22.4), ('A5', 28.3), ('A6', 33.3), ('A7', 40.9),
        ('A8', 49.2), ('A9', 59.8), ('A10', 63.3), ('A11', 72.9), ('END', 79.2)]
SHOTS = {k: CUTS[i + 1][1] - t for i, (k, t) in enumerate(CUTS[:-1])}
PERSIAN = dict(shirt='#3E6FA8', pants='#E8E0CC', hat=None, mustache=True, collar='#C9A44A')
HELPER = dict(shirt='#A8463E', pants='#E8E0CC', hat=None, mustache=False, collar='#E8E0CC')
gz = SA.ground_z
V = Vector if False else lib3d.V

MUD = '#C2814A'
def yakhchal(cx, cy, cut=False, scale=1.0, rise=1.0):
    """Cúpula escalonada (yakhchal). cut=True la parte por la mitad para ver el interior y el pozo."""
    root = empty((cx, cy, gz(cx, cy))); M = mat(MUD, 0.95, key='yakh')
    rings = []
    for i in range(9):
        r = (9.5 - i * 1.05) * scale; h = 1.7 * scale
        o = prim('cylinder', (0, 0, (0.9 + i * 1.6) * scale), m=M, parent=root, vertices=28, radius=r, depth=h)
        rings.append(o)
    top = prim('cone', (0, 0, 15.5 * scale), m=M, parent=root, vertices=24, radius1=1.2 * scale, depth=1.6 * scale)
    rings.append(top)
    if cut:
        # vaciar el interior y cortar la mitad frontal
        inner = prim('cone', (0, 0, 6.5 * scale), m=None, parent=root, vertices=28, radius1=7.6 * scale, radius2=0.6 * scale, depth=14.2 * scale)
        bpy.context.view_layer.update()
        for o in rings:
            md = o.modifiers.new('b', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = inner; md.solver = 'EXACT'
        cutter = prim('cube', (0, -12 * scale, 8 * scale), scale=(30 * scale, 24 * scale, 30 * scale), parent=root, size=1)
        for o in rings:
            md = o.modifiers.new('c', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
        inner.hide_render = True; cutter.hide_render = True
        vent = prim('cylinder', (0, 0, 15.5 * scale), m=mat('#2A1A0E', 0.9, key='hole'), parent=root, vertices=12, radius=0.45 * scale, depth=2.0 * scale)
    else:
        prim('cube', (0, -9.5 * scale, 1.2 * scale), scale=(1.4 * scale, 0.6 * scale, 2.4 * scale), m=mat('#2A1A0E', 0.9, key='hole'), parent=root, size=1)
    if not cut:
        for o in rings: outlined(o, 1.008)
    return root

def shade_wall(x0, x1, y, h=10, th=1.2):
    z = gz((x0 + x1) / 2, y)
    w = prim('cube', ((x0 + x1) / 2, y, z + h / 2), scale=(x1 - x0, th, h), m=mat('#B9773F', 0.95, key='swall'), size=1)
    return w

def pool(x0, x1, y0, y1):
    z = gz((x0 + x1) / 2, (y0 + y1) / 2)
    prim('cube', ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.1), scale=(x1 - x0 + 0.6, y1 - y0 + 0.6, 0.25), m=mat('#A9693A', 0.95, key='rim'), size=1)
    wm = bpy.data.materials.new('poolw'); wm.use_nodes = True; b = wm.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.08; b.inputs['Base Color'].default_value = (*lin('#3FA3D6'), 1)
    water = prim('cube', ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.24), scale=(x1 - x0, y1 - y0, 0.04), m=wm, size=1)
    return water, b

def set_freeze(bsdf, k):
    c0 = lin('#3FA3D6'); c1 = lin('#E8F6FF')
    bsdf.inputs['Base Color'].default_value = (*[a + (b - a) * k for a, b in zip(c0, c1)], 1)
    bsdf.inputs['Roughness'].default_value = 0.08 + 0.35 * k

def ice_block(loc, s=0.5):
    o = prim('cube', loc, scale=(s * 1.4, s, s * 0.6), m=mat('#DDF3FF', 0.15, emit=0.25, key='ice'), size=1)
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = 0.06; bv.segments = 2
    return o

def ground_section(L=44, depth=26, cx=0.0):
    layers = [(-3.0, 0.0, '#E3B26E'), (-9.0, -3.0, '#C9894F'), (-17.0, -9.0, '#A86A45'), (-depth, -17.0, '#8C5A3C')]
    objs = []
    for (z0, z1, col) in layers:
        o = prim('cube', (cx, 4, (z0 + z1) / 2), scale=(L, 16, z1 - z0), m=mat(col, 0.95), size=1); objs.append(o)
    return objs

def pit_cut(objs, r=6.5, d=9.0):
    cut = prim('cylinder', (0, 0, -d / 2 + 0.2), vertices=28, radius=r, depth=d)
    box = prim('cube', (0, -6, -d / 2), scale=(2 * r + 2, 12, d + 2), size=1)
    bpy.context.view_layer.update()
    for o in objs:
        m1 = o.modifiers.new('p', 'BOOLEAN'); m1.operation = 'DIFFERENCE'; m1.object = cut; m1.solver = 'EXACT'
    cut.hide_render = True; box.hide_render = True
    prim('cylinder', (0, 0.6, -d + 0.25), m=mat('#7A4A2C', 0.95, key='pitf'), vertices=28, radius=r * 0.98, depth=0.1)
    return cut

def ingredient(kind, loc):
    e = empty(loc)
    if kind == 'arena':
        prim('cone', (0, 0, 0.35), m=mat('#E6C07E', 0.95, key='ing_s'), parent=e, vertices=16, radius1=0.7, depth=0.7)
    elif kind == 'arcilla':
        prim('uv_sphere', (0, 0, 0.4), scale=(1, 1, 0.8), m=mat('#A35A32', 0.9, key='ing_c'), parent=e, segments=16, ring_count=10, radius=0.45)
    elif kind == 'cal':
        prim('cone', (0, 0, 0.3), m=mat('#F4F2EA', 0.9, key='ing_l'), parent=e, vertices=16, radius1=0.6, depth=0.6)
    elif kind == 'ceniza':
        prim('cone', (0, 0, 0.3), m=mat('#7D7C7A', 0.95, key='ing_a'), parent=e, vertices=16, radius1=0.6, depth=0.55)
    elif kind == 'pelo':
        for k in range(14):
            a = k / 14 * 2 * PI
            prim('cylinder', (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.3), rot=(0.5 * math.sin(a * 3), 0.5 * math.cos(a * 2), a), m=mat('#4A3A2E', 0.9, key='ing_h'), parent=e, vertices=4, radius=0.025, depth=0.7)
    elif kind == 'huevo':
        for k in range(3):
            prim('uv_sphere', (k * 0.35 - 0.35, 0, 0.25), scale=(0.8, 0.8, 1.0), m=mat('#F7F3E8', 0.4, key='ing_e'), parent=e, segments=16, ring_count=10, radius=0.22)
    for ch in e.children: outlined(ch, 1.05)
    return e

def pop(e, t, t0, base=1.0):
    k = 0.0 if t < t0 else min(1.0, (t - t0) / 0.25)
    s = base * (k * (1 + 0.25 * math.sin(k * PI)))
    e.scale = (max(s, 0.001),) * 3

def dim_arrow(p0, p1, col='#FFD240'):
    M = mat(col, 0.4, emit=1.0, key='dim')
    d = p1 - p0; mid = (p0 + p1) / 2
    e = empty(mid); e.rotation_euler = d.normalized().to_track_quat('Z', 'Y').to_euler()
    prim('cylinder', (0, 0, 0), m=M, parent=e, vertices=10, radius=0.06, depth=d.length - 0.5)
    for sgn in (1, -1):
        prim('cone', (0, 0, sgn * (d.length / 2 - 0.25)), rot=(0 if sgn > 0 else PI, 0, 0), m=M, parent=e, vertices=12, radius1=0.2, depth=0.5)
    return e

# ------------------------------------------------------------------ TOMAS
def H():
    rnd, camels = SA.world('dusk')
    y = yakhchal(0, 30); shade_wall(-24, -8, 32)
    w = Person(PERSIAN); blk = ice_block((0, 0, 0), 0.32)
    sparks = [prim('ico_sphere', (0, 0, 0), m=mat('#FFFFFF', 0.2, emit=5.0, key='spark'), subdivisions=1, radius=0.04) for _ in range(10)]
    cam, tgt = make_cam(28)
    def anim(t):
        SA.caravan(camels, t, y0=55)
        w.pose(pos=(0.8, 19.6, gz(0.8, 19.6)), yaw=0.2, armL=(-1.1, -0.15, 0, -1.4), armR=(-1.1, 0.15, 0, -1.4), smile=1, squint=0.3)
        hp = w.hand_pos('L').lerp(w.hand_pos('R'), 0.5); blk.location = hp + V(0, -0.15, 0.05)
        for k, s in enumerate(sparks):
            a = t * 3 + k; s.location = blk.location + V(math.cos(a) * 0.5, -0.4, math.sin(a * 1.3) * 0.35)
            sc = 0.5 + 0.5 * math.sin(t * 10 + k); s.scale = (sc, sc, sc)
        if t < 2.6:
            u = sm(t / 2.6); cam.location = V(30, -40, 30).lerp(V(4, 6, 6), u); tgt.location = V(0, 30, 8).lerp(V(0, 26, 8), u)
        else:
            u = sm((t - 2.6) / 2.5); cam.location = V(4, 6, 6).lerp(V(1.6, 16.2, 2.0), u); tgt.location = V(0, 26, 8).lerp(V(0.8, 19.6, 1.3), u)
    return anim

def A1():
    rnd, camels = SA.world('night')
    p = Person(PERSIAN); tray = prim('cylinder', (0, 0, 0), scale=(1, 1, 1), m=mat('#3FA3D6', 0.08, key='trayw'), vertices=24, radius=0.6, depth=0.06)
    rim = prim('torus', (0, 0, 0), m=mat('#8A5A3A', 0.8, key='tray'), major_radius=0.62, minor_radius=0.05, major_segments=24, minor_segments=6)
    SA.plight((2.0, -1.0, 3.0), power=30, hexc='#9FB8FF', radius=2.0)
    cam, tgt = make_cam(30)
    def anim(t):
        SA.caravan(camels, t + 8, y0=40)
        put = sm((t - 0.4) / 1.4)
        p.pose(pos=(1.2, 0.6, gz(1.2, 0.6)), yaw=-0.5, crouch=0.45 * put * (1 - sm((t - 2.4) / 0.6)), lean=0.4 * put * (1 - sm((t - 2.4) / 0.6)),
               armL=(-0.9, -0.2, 0, -0.4), armR=(-0.9, 0.2, 0, -0.4), smile=sm((t - 2.8) / 0.4), squint=0.3)
        hp = p.hand_pos('L').lerp(p.hand_pos('R'), 0.5)
        dest = V(0.2, -0.4, gz(0.2, -0.4) + 0.05)
        loc = hp + V(0, -0.2, 0) if put < 1 else dest
        if t > 1.8: loc = dest
        tray.location = loc; rim.location = loc + V(0, 0, 0.02)
        u = sm(t / 5.3); cam.location = V(4.5, -6.5, 2.4).lerp(V(3.2, -4.2, 1.9), u); tgt.location = V(0.6, 0.0, 0.8)
    return anim

def A2():
    rnd, camels = SA.world('day')
    p = Person(PERSIAN)
    tray = prim('cylinder', (0.2, -0.4, gz(0.2, -0.4) + 0.05), m=mat('#3FA3D6', 0.08, key='trayw'), vertices=24, radius=0.6, depth=0.06)
    prim('torus', (0.2, -0.4, gz(0.2, -0.4) + 0.07), m=mat('#8A5A3A', 0.8, key='tray'), major_radius=0.62, minor_radius=0.05, major_segments=24, minor_segments=6)
    ice = prim('cylinder', (0.2, -0.4, gz(0.2, -0.4) + 0.1), m=mat('#E8F6FF', 0.3, emit=0.2, key='icesheet'), vertices=24, radius=0.58, depth=0.05)
    steam = [prim('uv_sphere', (0.2 + random.uniform(-0.4, 0.4), -0.4 + random.uniform(-0.4, 0.4), 0.3), m=mat('#FFFFFF', 0.9, alpha=0.35, key='steam'), segments=8, ring_count=6, radius=0.12) for _ in range(8)]
    cam, tgt = make_cam(30)
    def anim(t):
        SA.caravan(camels, t + 8)
        melt = sm((t - 0.5) / 2.5); ice.scale = (max(0.01, 1 - melt), max(0.01, 1 - melt), 1)
        for k, s in enumerate(steam):
            u = (t * 0.6 + k * 0.12) % 1.0; s.location.z = gz(0.2, -0.4) + 0.2 + u * 1.2; sc = 0.5 + u; s.scale = (sc, sc, sc); s.hide_render = melt < 0.1
        sad = sm((t - 2.4) / 0.4)
        p.pose(pos=(1.4, 0.4, gz(1.4, 0.4)), yaw=-0.6, wide=1 - sad, worry=sad, mouth=0.4, nod=0.35, look=(-0.4, -0.6),
               armL=(-0.2, -0.3, 0, -0.3), armR=(-0.2, 0.3, 0, -0.3))
        if t < 1.0:
            u = sm(t / 1.0); cam.location = V(3.0, -5.0, 1.6); tgt.location = V(40, 420, 230).lerp(V(0.4, -0.2, 0.4), u)
        else:
            cam.location = V(3.0, -5.0, 1.6).lerp(V(2.0, -3.2, 1.5), sm((t - 1.0) / 3.0)); tgt.location = V(0.6, -0.2, 0.5)
    return anim

def pool_scene(mode):
    rnd, camels = SA.world(mode)
    wall = shade_wall(-10, 10, 4.0, h=10)
    water, bsdf = pool(-8, 8, 0.0, 3.2)
    return rnd, camels, wall, water, bsdf

def A3():
    rnd, camels, wall, water, bsdf = pool_scene('day')
    p = Person(PERSIAN); cam, tgt = make_cam(28)
    z0 = wall.location.z
    def anim(t):
        SA.caravan(camels, t + 17)
        r = eo(t / 2.2); wall.location.z = gz(0, 4) + 5 - 10.2 * (1 - r)
        p.pose(pos=(9.5, -2.5, gz(9.5, -2.5)), yaw=0.9, armR=(-1.5, 0.3, 0, -0.1), smile=sm((t - 2.4) / 0.4), squint=0.3, look=(-0.6, 0.3))
        u = sm(t / 4.7); cam.location = V(18, -16, 7).lerp(V(14, -11, 5), u); tgt.location = V(0, 2, 2.5)
    return anim

def A4():
    rnd, camels, wall, water, bsdf = pool_scene('night')
    cracks = []
    workers = [Person(PERSIAN), Person(HELPER)]
    slabs = [ice_block((0, 0, 0), 0.45) for _ in range(2)]
    SA.plight((0, -4, 6), power=60, hexc='#9FB8FF', radius=3.0)
    cam, tgt = make_cam(28)
    sun = [o for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'SUN'][0]
    wn = bpy.context.scene.world.node_tree.nodes; bg = wn['Background']
    ramp = [n for n in wn if n.type == 'VALTORGB'][0]
    starm = MATS.get('#FFFFFF_0.5_6.0_1.0') or bpy.data.materials.get('star')
    def anim(t):
        SA.caravan(camels, t + 22, y0=40)
        k = sm((t - 0.4) / 2.6); set_freeze(bsdf, k)
        dawn = sm((t - 3.0) / 1.0)
        sun.data.energy = 0.35 + 3.2 * dawn; sun.data.color = tuple(a + (b - a) * dawn for a, b in zip((0.55, 0.65, 1.0), (1.0, 0.96, 0.88)))
        sun.rotation_euler = (math.radians(60 - 18 * dawn), 0, math.radians(-40 + 70 * dawn))
        bg.inputs['Strength'].default_value = 0.25 + 0.65 * dawn
        c0 = lin('#0C1A3A'); c1 = lin('#4FA6E8'); ramp.color_ramp.elements[1].color = (*[a + (b - a) * dawn for a, b in zip(c0, c1)], 1)
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ('star', 'moon'): o.hide_render = dawn > 0.5
        morning = t > 3.6
        for i, (w, s) in enumerate(zip(workers, slabs)):
            x = -3 + i * 5
            if morning:
                lift = sm((t - 3.9 - i * 0.3) / 0.8)
                w.pose(pos=(x, -1.6, gz(x, -1.6)), yaw=0.0, crouch=0.4 * (1 - lift), lean=0.5 * (1 - lift), armL=(-1.0 - 0.8 * lift, -0.2, 0, -0.5), armR=(-1.0 - 0.8 * lift, 0.2, 0, -0.5), smile=lift)
                s.location = w.hand_pos('L').lerp(w.hand_pos('R'), 0.5) + V(0, -0.2, 0); s.hide_render = False
            else:
                w.root.location = V(0, -300, -50); s.hide_render = True
        u = sm(t / 5.9)
        cam.location = V(-7, -11, 9).lerp(V(-4, -8.5, 5.0), u); tgt.location = V(0, 1.6, 0.0)
    return anim

def A5():
    rnd, camels = SA.world('day')
    p = Person(PERSIAN); th, fluid = SA.thermometer(); th.location = (-2.6, 0.4, gz(-2.6, 0.4) + 0.6)
    blocks = [ice_block((rnd.uniform(-1.4, 1.4), rnd.uniform(-0.8, 0.6), 0), 0.42) for _ in range(5)]
    drips = [prim('uv_sphere', (0, 0, 0), scale=(0.5, 0.5, 0.8), m=mat('#4FB3E8', 0.1, key='drop'), segments=8, ring_count=6, radius=0.06) for _ in range(10)]
    cam, tgt = make_cam(30)
    def anim(t):
        SA.caravan(camels, t + 28)
        heat = sm((t - 0.3) / 2.5); fluid.scale.z = 0.4 + 2.4 * heat; fluid.location.z = fluid.scale.z / 2
        for i, b in enumerate(blocks):
            sh = 1 - 0.35 * sm((t - 1.0) / 4.0)
            b.location = V((i - 2) * 0.75, -0.2 + (i % 2) * 0.3, gz(0, 0) + 0.25 * sh + (0.5 if i == 4 else 0)); b.scale = (0.59 * sh, 0.42 * sh, 0.25 * sh)
        for k, d in enumerate(drips):
            u = (t * 1.3 + k * 0.17) % 1.0; d.location = V((k % 5 - 2) * 0.75, -0.45, gz(0, 0) + 0.3 - u * 0.3); d.hide_render = t < 1.0
        p.pose(pos=(1.9, -1.2, gz(1.9, -1.2)), yaw=-0.5, worry=1, wide=0.6, mouth=0.5, armL=(-0.5, -0.6, 0, -2.0), armR=(-0.5, 0.6, 0, -2.0), look=(-0.6, -0.3))
        u = sm(t / 5.0); cam.location = V(1.0, -6.0, 2.0).lerp(V(0.6, -4.6, 1.8), u); tgt.location = V(0, 0, 0.8)
    return anim

def section_world(with_dome=False, dome_rise=None):
    setup(world='#4FA6E8', strength=0.9, sun_rot=(42, 0, 15), sun_power=3.2, resx=RESX)
    objs = ground_section()
    pit_cut(objs)
    prim('cube', (0, 30, -0.5), scale=(300, 52, 1.0), m=SA.sand_mat(), size=1)
    for x in (-18, 16): SA.palm(x, 3.0, 6, random.Random(int(x) + 40))
    slabs = []
    for i in range(18):
        x = -4.5 + (i % 6) * 1.8; z = -8.4 + (i // 6) * 0.75
        slabs.append(ice_block((x, 0.8, z), 0.5))
    return objs, slabs

def A6():
    objs, slabs = section_world()
    p = Person(PERSIAN)
    arrows = [SA.arrow('#FF5A1F') for _ in range(4)]
    cam, tgt = make_cam(30)
    def anim(t):
        for i, s in enumerate(slabs):
            t0 = 1.2 + i * 0.12; k = sm((t - t0) / 0.4)
            s.hide_render = t < t0; s.location.z = -8.4 + (i // 6) * 0.75 + (1 - k) * 8
        dig = math.sin(t * 9)
        p.pose(pos=(8.5, -1.0, 0), yaw=1.2, crouch=0.2, lean=0.3 + 0.2 * dig * (1 - sm((t - 3) / 0.5)), armR=(-1.2 + 0.8 * dig, 0.2, 0, -0.4), armL=(-1.2 + 0.8 * dig, -0.2, 0, -0.4),
               worry=sm((t - 5.5) / 0.4), wide=sm((t - 5.5) / 0.4), look=(0, 0.6 * sm((t - 5.5) / 0.4)))
        for i, a in enumerate(arrows):
            k = sm((t - 5.4 - i * 0.1) / 1.4)
            SA.aim(a, V(-3 + i * 2, -4.5, 6 - 4.5 * k), V(0, 0, -1), 0.9 * min(1, (t - 5.4) * 3) if t > 5.4 else 0.001)
        u = sm(t / 7.6); cam.location = V(4, -30, 3).lerp(V(1, -34, -1.5), u); tgt.location = V(1, 0, -1.5).lerp(V(0.5, 0, -2.5), u)
    return anim

def A7():
    objs, slabs = section_world()
    dome = yakhchal(0, 0.6, cut=True, scale=0.75)
    dome.location = V(0, 0.6, 0)
    hot = [SA.arrow('#FF5A1F', length=1.2) for _ in range(5)]
    cold = [SA.arrow('#3FA9F5', length=1.2) for _ in range(5)]
    cam, tgt = make_cam(30)
    def anim(t):
        r = eo(t / 1.5); dome.scale = (1, 1, max(0.02, r))
        for i, a in enumerate(hot):
            u = ((t - 1.8) * 0.35 + i / 5) % 1.0
            SA.aim(a, V(-1.2 + i * 0.6, -4.2, 1.0 + u * 11.5), V(0, 0, 1), 0.7); a.hide_render = t < 1.8
        for i, a in enumerate(cold):
            u = ((t - 3.6) * 0.3 + i / 5) % 1.0
            SA.aim(a, V(-4.5 + i * 2.2, -4.4, 3.5 - u * 9.5), V(0, 0, -1), 0.7); a.hide_render = t < 3.6
        u = sm(t / 8.3); cam.location = V(0, -44, 5).lerp(V(0, -38, 3), u); tgt.location = V(0, 0, 1.5)
    return anim

def A8():
    rnd, camels = SA.world('day')
    y = yakhchal(0, 14)
    kinds = [('arena', 54.4), ('arcilla', 55.2), ('cal', 56.1), ('ceniza', 56.7), ('pelo', 57.4), ('huevo', 58.6)]
    ings = []
    for i, (k, tt) in enumerate(kinds):
        x = -3.75 + i * 1.5; ings.append((ingredient(k, (x, 0, gz(x, 0) + 0.2)), tt - 49.2))
    p = Person(PERSIAN); cam, tgt = make_cam(28)
    def anim(t):
        SA.caravan(camels, t + 49, y0=60)
        for e, t0 in ings: pop(e, t, t0, 1.0)
        bad = sm(t / 0.4) * (1 - sm((t - 3.0) / 0.5))
        p.pose(pos=(4.6, 1.0, gz(4.6, 1.0)), yaw=-0.7, worry=bad, smile=sm((t - 4.5) / 0.4), squint=0.3, look=(-0.7, -0.3),
               armR=(-1.3, 0.25, 0, -0.2) if t > 4.5 else None)
        if t < 3.2:
            u = sm(t / 3.2); cam.location = V(-6, -4, 10).lerp(V(-2, -7.5, 5), u); tgt.location = V(0, 14, 7).lerp(V(0, 4, 2), u)
        else:
            u = sm((t - 3.2) / 7.0); cam.location = V(-2, -7.5, 5).lerp(V(0, -7.0, 2.2), u); tgt.location = V(0, 4, 2).lerp(V(0, 0, 0.6), u)
    return anim

def A9():
    objs, slabs = section_world()
    dome = yakhchal(0, 0.6, cut=True, scale=0.75)
    p = Person(PERSIAN)
    dim = dim_arrow(V(-7.15, 0.3, 0.7), V(-5.65, 0.3, 0.7))
    cam, tgt = make_cam(32)
    def anim(t):
        dim.scale = (max(0.01, eo((t - 0.4) / 0.4)),) * 3
        p.pose(pos=(-9.3, -0.8, 0), yaw=0.2, smile=1, squint=0.4, armR=(-1.3, 0.4, 0, -0.1))
        u = sm(t / 3.5); cam.location = V(-5.5, -9.5, 2.6).lerp(V(-6.2, -7.5, 2.0), u); tgt.location = V(-6.8, 0.3, 1.0)
    return anim

def A10():
    rnd, camels = SA.world('day')
    y = yakhchal(0, 26)
    p = Person(PERSIAN); kid = Person(HELPER)
    bowl = empty()
    prim('uv_sphere', (0, 0, 0), scale=(1, 1, 0.5), m=mat('#2F6FB0', 0.3, key='bowl'), parent=bowl, segments=16, ring_count=8, radius=0.22)
    prim('uv_sphere', (0, 0, 0.08), scale=(1, 1, 0.45), m=mat('#FFF8EE', 0.3, key='falood'), parent=bowl, segments=16, ring_count=8, radius=0.2)
    for k in range(5): prim('uv_sphere', (math.cos(k) * 0.1, math.sin(k) * 0.1, 0.15), m=mat('#E63946', 0.3, key='cherry'), parent=bowl, segments=8, ring_count=6, radius=0.03)
    cam, tgt = make_cam(30)
    def anim(t):
        SA.caravan(camels, t + 63, y0=50)
        eat = math.sin(t * 5)
        p.pose(pos=(0.6, 12.2, gz(0.6, 12.2)), yaw=0.3, armL=(-1.2, -0.2, 0, -1.2), armR=(-1.0 - 0.4 * max(0, eat), 0.25, 0, -1.9), smile=1, squint=0.5, mouth=0.3 * max(0, eat))
        bowl.location = p.hand_pos('L') + V(0.05, -0.15, 0.05)
        kid.pose(pos=(-1.2, 12.6, gz(-1.2, 12.6)), yaw=-0.3, smile=1, wide=0.5, armL=(-0.5, -0.3, 0, -1.6), armR=(-0.5, 0.3, 0, -1.6), look=(0.6, -0.2))
        if t < 5.0:
            u = sm(t / 5.0); cam.location = V(2.0, 7.5, 1.7).lerp(V(1.0, 8.8, 1.7), u); tgt.location = V(0, 12.4, 1.4)
        else:
            u = sm((t - 5.0) / 4.6); cam.location = V(1.0, 8.8, 1.7).lerp(V(14, -22, 12), u); tgt.location = V(0, 12.4, 1.4).lerp(V(0, 26, 7), u)
    return anim

def A11():
    rnd, camels = SA.world('dusk')
    yakhchal(0, 0); shade_wall(-24, -10, 3)
    cam, tgt = make_cam(28)
    def anim(t):
        SA.caravan(camels, t + 72, y0=30)
        a = -1.7 + t * 0.09
        cam.location = V(math.cos(a) * 34, math.sin(a) * 34, 9 + t * 0.4); tgt.location = V(0, 0, 7)
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
