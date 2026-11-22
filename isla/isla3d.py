# "La isla prohibida" — escenas 3D (Blender Eevee) con countryballs 3D, serpientes y la isla.
# Uso: blender -b -P isla3d.py -- <toma> <carpeta_salida> <carpeta_banderas> [ancho] [frame_ini] [frame_fin]
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index('--') + 1:]
SHOT = argv[0]; OUT = argv[1]; FLAGDIR = argv[2]
RESX = int(argv[3]) if len(argv) > 3 else 540
FSTART = int(argv[4]) if len(argv) > 4 else 0
FEND = int(argv[5]) if len(argv) > 5 else 10 ** 6
FPS = 24; PI = math.pi
# duración nominal de cada toma (s) — luego se reajusta a la voz real
SHOTS = {'A1': 5.92, 'A2': 5.46, 'A3': 3.63, 'B1': 3.67, 'B2': 2.22, 'B3': 4.22, 'B4': 6.89, 'C1': 4.67,
         'D1': 5.01, 'B5': 5.29, 'B6': 6.27, 'A4': 4.42, 'C2': 4.08, 'A5': 4.55}

# ------------------------------------------------------------------ utilidades
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

MATS = {}
def mat(h, rough=0.7, emit=0.0, alpha=1.0, key=None):
    key = key or f'{h}_{rough}_{emit}_{alpha}'
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    c = (*lin(h), 1)
    b.inputs['Base Color'].default_value = c; b.inputs['Roughness'].default_value = rough
    if emit > 0:
        b.inputs['Emission Color'].default_value = c; b.inputs['Emission Strength'].default_value = emit
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'; m.shadow_method = 'NONE'
    MATS[key] = m; return m

def link(o): bpy.context.scene.collection.objects.link(o); return o

def prim(kind, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), m=None, smooth=False, parent=None, **kw):
    getattr(bpy.ops.mesh, 'primitive_%s_add' % kind)(**kw)
    o = bpy.context.object
    if parent: o.parent = parent
    o.location = loc; o.rotation_euler = rot; o.scale = scale
    if m: o.data.materials.clear(); o.data.materials.append(m)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    return o

def empty(loc=(0, 0, 0), parent=None):
    o = link(bpy.data.objects.new('e', None))
    if parent: o.parent = parent
    o.location = loc; return o

def sm(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def eo(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def lerp(a, b, u): return a + (b - a) * u
def V(*a): return Vector(a)
def keys(t, ks):
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            u = sm((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list, Vector)): return Vector(v0).lerp(Vector(v1), u)
            return v0 + (v1 - v0) * u
    v = ks[-1][1]
    return Vector(v) if isinstance(v, (tuple, list, Vector)) else v
def spline(t, ks):
    if t <= ks[0][0]: return Vector(ks[0][1])
    if t >= ks[-1][0]: return Vector(ks[-1][1])
    for i in range(len(ks) - 1):
        if ks[i][0] <= t <= ks[i + 1][0]: break
    p0 = Vector(ks[max(i - 1, 0)][1]); p1 = Vector(ks[i][1]); p2 = Vector(ks[i + 1][1]); p3 = Vector(ks[min(i + 2, len(ks) - 1)][1])
    u = (t - ks[i][0]) / (ks[i + 1][0] - ks[i][0])
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
def shake(t, t0, dur, amp):
    if t < t0 or t > t0 + dur: return Vector((0, 0, 0))
    k = amp * (1 - (t - t0) / dur)
    return Vector((math.sin(t * 71) * k, math.sin(t * 53 + 1) * k * 0.6, math.sin(t * 89 + 2) * k))

def setup(world='#93D3FF', strength=0.8, sun_rot=(48, 0, 35), sun_power=3.0):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.fps = FPS
    sc.render.resolution_x = RESX; sc.render.resolution_y = RESX * 16 // 9; sc.render.resolution_percentage = 100
    e = sc.eevee; e.taa_render_samples = 10; e.use_gtao = True; e.gtao_distance = 1.0
    e.use_soft_shadows = True; e.shadow_cascade_size = '2048'; e.shadow_cube_size = '512'
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 93
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    # cielo con degradado vertical
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[0].color = (*lin('#DDF1FF'), 1)
    ramp.color_ramp.elements[1].position = 0.85; ramp.color_ramp.elements[1].color = (*lin(world), 1)
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    d = bpy.data.lights.new('sun', 'SUN'); d.energy = sun_power; d.angle = math.radians(3); d.color = (1.0, 0.96, 0.88)
    d.shadow_cascade_max_distance = 120
    o = link(bpy.data.objects.new('sun', d)); o.rotation_euler = tuple(math.radians(a) for a in sun_rot)

def make_cam(lens=30):
    cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.clip_start = 0.02; cd.clip_end = 1500
    cam = link(bpy.data.objects.new('cam', cd)); tgt = empty()
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam, tgt

def flip_normals(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()

OUTLINE = None
def outline_mat():
    global OUTLINE
    if OUTLINE is None:
        OUTLINE = mat('#0A0A0A', 1.0, key='outline'); OUTLINE.use_backface_culling = True
    return OUTLINE

def add_outline(o, thick=1.04):
    d = o.copy(); d.data = o.data.copy(); link(d)
    d.parent = o.parent; d.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    d.scale = tuple(s * thick for s in o.scale)
    d.data.materials.clear(); d.data.materials.append(outline_mat()); flip_normals(d)
    return d

# ------------------------------------------------------------------ countryball 3D
def flag_mat(code):
    key = 'flag_' + code
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.45
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); comb = nt.nodes.new('ShaderNodeCombineXYZ')
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = 0.5; mx.inputs[2].default_value = 0.5
    mz = nt.nodes.new('ShaderNodeMath'); mz.operation = 'MULTIPLY_ADD'; mz.inputs[1].default_value = 0.5; mz.inputs[2].default_value = 0.5
    img = nt.nodes.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(os.path.join(FLAGDIR, code + '.png')); img.extension = 'EXTEND'
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    nt.links.new(sep.outputs['X'], mx.inputs[0]); nt.links.new(sep.outputs['Z'], mz.inputs[0])
    nt.links.new(mx.outputs[0], comb.inputs['X']); nt.links.new(mz.outputs[0], comb.inputs['Y'])
    nt.links.new(comb.outputs[0], img.inputs['Vector']); nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
    MATS[key] = m; return m

class Ball:
    def __init__(s, code, r=0.45):
        s.r = r; s.root = empty(); s.body = empty(parent=s.root)
        sp = prim('uv_sphere', m=flag_mat(code), smooth=True, parent=s.body, segments=48, ring_count=24, radius=1)
        sp.location = (0, 0, 1)  # el centro del cuerpo a 1 radio del suelo
        s.body.scale = (r, r, r)
        add_outline(sp, 1.045)
        W = mat('#FFFFFF', 0.3, emit=0.25, key='eyewhite')
        s.eyes = []
        for side in (1, -1):
            piv = empty((0.33 * side, -0.9, 1.1), s.body)
            piv.rotation_euler = (0, 0, 0.34 * side)
            prim('uv_sphere', (0, -0.06, 0), scale=(0.25, 0.08, 0.31), m=W, smooth=True, parent=piv, segments=24, ring_count=12, radius=1)
            prim('uv_sphere', (0, -0.035, 0), scale=(0.295, 0.07, 0.355), m=mat('#0A0A0A', 0.8, key='eyeblk'), smooth=True, parent=piv, segments=24, ring_count=12, radius=1)
            s.eyes.append((piv, side))
        s.glasses = None; s.sweat = None
        s.mouth = prim('uv_sphere', (0, -0.95, 0.62), scale=(0.1, 0.04, 0.13), m=mat('#0A0A0A', 0.6, key='mouth'), smooth=True, parent=s.body, segments=16, ring_count=8, radius=1)
        s.mouth.hide_render = True

    def add_glasses(s):
        g = empty((0, 0, 0), s.body); K = mat('#050505', 0.15, key='glass')
        for side in (1, -1):
            prim('cube', (0.34 * side, -1.02, 1.14), rot=(0, 0, 0.32 * side), scale=(0.36, 0.05, 0.24), m=K, parent=g, size=1)
        prim('cube', (0, -1.06, 1.22), scale=(0.3, 0.05, 0.06), m=K, parent=g, size=1)
        s.glasses = g

    def add_sweat(s):
        s.sweat = prim('uv_sphere', (0.78, -0.45, 1.6), scale=(0.08, 0.06, 0.13), m=mat('#BDE8FF', 0.1, emit=0.3, key='sweat'), smooth=True, parent=s.body, segments=12, ring_count=8, radius=1)

    def set(s, pos, yaw=0.0, eyes='normal', look=(0.0, 0.0), squash=1.0, tilt=0.0, glasses=None, sweat=0.0, mouth=False, blink=0.0):
        s.root.location = pos; s.root.rotation_euler = (0, tilt, yaw)
        s.body.scale = (s.r / math.sqrt(squash), s.r / math.sqrt(squash), s.r * squash)
        for piv, side in s.eyes:
            sx, sz, roll = {'normal': (1, 1, 0), 'wide': (1.15, 1.25, 0), 'scared': (1.3, 1.35, 0), 'smug': (1.05, 0.45, 0),
                            'angry': (1.0, 0.6, 0.4), 'worried': (1.0, 0.75, -0.4), 'think': (1.0, 0.55, -0.15)}[eyes]
            sz *= max(0.08, 1 - blink)
            piv.scale = (sx, 1, sz); piv.rotation_euler = (0, roll * side, 0.34 * side)
            piv.location = (0.33 * side + look[0] * 0.12, -0.9 + abs(look[0]) * 0.03, 1.1 + look[1] * 0.12)
        if s.glasses is not None:
            if glasses is None: glasses = 1.0
            s.glasses.location = (0, 0, (1 - glasses) * 1.8)
            for ch in s.glasses.children: ch.hide_render = glasses <= 0
        if s.sweat is not None:
            s.sweat.hide_render = sweat <= 0; s.sweat.location.z = 1.6 - 0.25 * ((sweat * 3) % 1)
        s.mouth.hide_render = not mouth

# ------------------------------------------------------------------ serpiente (cabeza de lanza dorada)
def snake_mat():
    if 'snake' in MATS: return MATS['snake']
    m = bpy.data.materials.new('snake'); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.38
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 2
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.48; ramp.color_ramp.elements[0].color = (*lin('#7A5418'), 1)
    ramp.color_ramp.elements[1].position = 0.55; ramp.color_ramp.elements[1].color = (*lin('#D9AE48'), 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    MATS['snake'] = m; return m

class Snake:
    N = 26
    def __init__(s, L=1.5, r=0.05):
        s.L = L
        cu = bpy.data.curves.new('sn', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3
        cu.resolution_u = 3; cu.use_fill_caps = True
        sp = cu.splines.new('POLY'); sp.points.add(s.N - 1)
        for i, p in enumerate(sp.points):
            u = i / (s.N - 1); p.radius = 0.25 + 0.85 * math.sin(min(1.0, u * 1.25) * PI / 2) if u < 0.92 else 0.8
        s.curve = link(bpy.data.objects.new('snake', cu)); cu.materials.append(snake_mat())
        s.sp = sp
        s.head = empty()
        prim('uv_sphere', (0, 0.03, 0.0), scale=(0.085, 0.08, 0.042), m=snake_mat(), smooth=True, parent=s.head, segments=16, ring_count=10, radius=1)
        prim('cone', (0, 0.1, -0.003), rot=(-PI / 2, 0, 0), scale=(1.0, 0.55, 1.0), m=snake_mat(), smooth=True, parent=s.head, vertices=12, radius1=0.075, radius2=0.012, depth=0.13)
        for sd in (1, -1):
            prim('uv_sphere', (0.058 * sd, 0.07, 0.022), m=mat('#E8B33A', 0.15, key='snakeiris'), smooth=True, parent=s.head, segments=10, ring_count=6, radius=0.016)
            prim('cube', (0.0735 * sd, 0.07, 0.022), scale=(0.004, 0.006, 0.022), m=mat('#120C05', 0.1, key='snakeeye'), parent=s.head, size=1)
            s.tongue = empty((0, 0.16, -0.012), s.head)
        T = mat('#C2185B', 0.4, key='tongue')
        prim('cylinder', (0, 0.03, 0), rot=(PI / 2, 0, 0), m=T, parent=s.tongue, vertices=6, radius=0.004, depth=0.06)
        for sd in (1, -1):
            prim('cylinder', (0.008 * sd, 0.07, 0), rot=(PI / 2, 0, 0.35 * sd), m=T, parent=s.tongue, vertices=6, radius=0.0035, depth=0.03)

    def set(s, pts, tongue=0.0):
        for p, c in zip(s.sp.points, pts): p.co = (c.x, c.y, c.z, 1)
        d = (pts[-1] - pts[-3]); d.z *= 0.25; d = d.normalized()
        s.head.location = pts[-1]
        s.head.rotation_euler = d.to_track_quat('Y', 'Z').to_euler()
        s.tongue.scale = (1, max(0.01, tongue), 1)
        s.tongue.hide_render = tongue < 0.05

def path_slither(base, ang, L, t, speed=0.15, amp=0.12, raise_head=0.0, phase=0.0, z=None, n=Snake.N):
    fwd = V(math.cos(ang), math.sin(ang), 0); side = V(-fwd.y, fwd.x, 0)
    pts = []
    for i in range(n):
        u = i / (n - 1)
        along = (u - 0.5) * L + speed * t
        lat = amp * math.sin(2 * PI * u * 1.6 - t * 4 + phase) * (0.35 + 0.65 * (1 - u))
        p = base + fwd * along + side * lat
        p.z = (base.z if z is None else z) + 0.045 + raise_head * sm((u - 0.72) / 0.28) * 0.4
        pts.append(p)
    return pts

def path_coil(base, t, L=1.5, raise_head=0.35, phase=0.0, n=Snake.N, look=0.0):
    pts = []
    for i in range(n):
        u = i / (n - 1)
        if u < 0.78:
            a = u / 0.78 * 2.3 * 2 * PI + phase; rr = 0.32 * (1 - u * 0.55)
            p = base + V(math.cos(a) * rr, math.sin(a) * rr, 0.05 + 0.06 * u)
        else:
            k = (u - 0.78) / 0.22
            a = 2.3 * 2 * PI + phase
            start = base + V(math.cos(a) * 0.32 * (1 - 0.78 * 0.55), math.sin(a) * 0.32 * (1 - 0.78 * 0.55), 0.1)
            dirv = V(math.cos(look), math.sin(look), 0)
            p = start + dirv * 0.22 * k + V(0, 0, raise_head * math.sin(k * PI / 2)) + V(0.02 * math.sin(t * 3 + phase), 0, 0)
        pts.append(p)
    return pts

# ------------------------------------------------------------------ pájaro
class Bird:
    def __init__(s, scale=1.0):
        s.root = empty(); s.root.scale = (scale,) * 3
        Wt = mat('#F4F4F0', 0.6, key='bird'); G = mat('#8A8F98', 0.6, key='birdg')
        prim('uv_sphere', (0, 0, 0), scale=(0.11, 0.24, 0.11), m=Wt, smooth=True, parent=s.root, segments=16, ring_count=10, radius=1)
        prim('uv_sphere', (0, 0.22, 0.07), m=Wt, smooth=True, parent=s.root, segments=12, ring_count=8, radius=0.075)
        prim('cone', (0, 0.32, 0.06), rot=(-PI / 2, 0, 0), m=mat('#F0A030', 0.5, key='beak'), parent=s.root, vertices=8, radius1=0.025, depth=0.09)
        for sd in (1, -1):
            prim('uv_sphere', (0.045 * sd, 0.26, 0.09), m=mat('#111111', 0.2, key='beye'), parent=s.root, segments=8, ring_count=6, radius=0.013)
        s.wings = []
        for sd in (1, -1):
            h = empty((0.08 * sd, 0.02, 0.04), s.root)
            prim('cube', (0.25 * sd, 0, 0), scale=(0.5, 0.17, 0.015), m=G, parent=h, size=1)
            s.wings.append((h, sd))
        prim('cube', (0, -0.27, 0.02), rot=(0.2, 0, 0), scale=(0.12, 0.12, 0.015), m=G, parent=s.root, size=1)

    def set(s, pos, yaw=0.0, flap=0.0, fold=0.0, pitch=0.0):
        s.root.location = pos; s.root.rotation_euler = (pitch, 0, yaw)
        for h, sd in s.wings:
            a = (0.6 * math.sin(flap)) * (1 - fold) - fold * 1.2
            h.rotation_euler = (0, -a * sd, 0)
            h.scale = (1 - 0.55 * fold, 1, 1)

# ------------------------------------------------------------------ mundo de la isla
SEA = None
def build_world(detail=True):
    setup()
    rnd = random.Random(5)
    global SEA
    SEA = prim('plane', (0, 0, 0), m=None, size=900)
    md = SEA.modifiers.new('oc', 'OCEAN'); md.resolution = 9; md.spatial_size = 80; md.wave_scale = 0.9; md.choppiness = 1.2
    md.repeat_x = 6; md.repeat_y = 6; md.size = 1.0
    sm_ = bpy.data.materials.new('sea'); sm_.use_nodes = True; b = sm_.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin('#1F8FA8'), 1); b.inputs['Roughness'].default_value = 0.12
    SEA.data.materials.append(sm_)
    for p in SEA.data.polygons: p.use_smooth = True
    # colina principal
    hill = prim('ico_sphere', (0, 32, -4.5), scale=(34, 26, 15), subdivisions=5, radius=1)
    tex = bpy.data.textures.new('cl', 'CLOUDS'); tex.noise_scale = 0.35
    dm = hill.modifiers.new('d', 'DISPLACE'); dm.texture = tex; dm.strength = 0.18; dm.texture_coords = 'LOCAL'
    bpy.context.view_layer.objects.active = hill; bpy.ops.object.modifier_apply(modifier=dm.name)
    hm = bpy.data.materials.new('hill'); hm.use_nodes = True; nt = hm.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.9
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.2; mr.inputs['From Max'].default_value = 2.2
    nt.links.new(geo.outputs['Position'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].color = (*lin('#9A8F7E'), 1); ramp.color_ramp.elements[1].color = (*lin('#4E8C3A'), 1)
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.7
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    hill.data.materials.append(hm)
    # plataforma de rocas donde se desembarca
    RK = [mat('#A39885', 0.9), mat('#8E8574', 0.9), mat('#B3A994', 0.9)]
    for (x, y, sx, sy, sz) in [(0, 2.5, 4.2, 3.0, 0.7), (-3.6, 3.5, 2.6, 2.4, 0.9), (3.8, 3.2, 2.8, 2.6, 0.8), (-1.5, 5.5, 3, 2.5, 1.2),
                               (2.2, 6.0, 3, 2.4, 1.4), (0.5, 0.2, 2.2, 1.6, 0.45), (-2.8, 0.8, 1.6, 1.4, 0.5), (3.2, 0.6, 1.5, 1.3, 0.5)]:
        r = prim('ico_sphere', (x, y, 0.0), rot=(0, 0, rnd.uniform(0, 3)), scale=(sx, sy, sz), m=rnd.choice(RK), subdivisions=2, radius=1)
    for _ in range(70):
        a = rnd.uniform(0, 2 * PI); rr = rnd.uniform(0.5, 1.0)
        x = math.cos(a) * 34 * rr * 1.02; y = 32 + math.sin(a) * 26 * rr * 1.02
        if y < 9 and abs(x) < 8: continue
        prim('ico_sphere', (x, y, rnd.uniform(-0.3, 0.3)), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), 0), scale=(rnd.uniform(0.8, 2.5),) * 2 + (rnd.uniform(0.5, 1.5),),
             m=rnd.choice(RK), subdivisions=1, radius=1)
    bpy.context.view_layer.update()
    return rnd

def ground_z(x, y, start=60.0):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, V(x, y, start), V(0, 0, -1))
    return loc.z if hit else 0.0

def vegetation(rnd, n_trees=60, n_grass=220):
    G = [mat('#5FA33E', 0.8), mat('#4C8F33', 0.8), mat('#78B84A', 0.8)]
    T = mat('#6B4A2B', 0.9); F = [mat('#2F6E2B', 0.8), mat('#3B7F31', 0.8)]
    tufts = []
    for _ in range(n_grass):
        x = rnd.uniform(-9, 9); y = rnd.uniform(3.5, 14)
        if abs(x) < 1.8 and y < 3.4: continue
        z = ground_z(x, y)
        if z < 0.15: continue
        e = empty((x, y, z))
        for k in range(3):
            prim('cone', (0.05 * k - 0.05, 0.03 * k, 0.25), rot=(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0), m=rnd.choice(G),
                 parent=e, vertices=4, radius1=0.05, radius2=0.0, depth=rnd.uniform(0.4, 0.7))
        tufts.append(e)
    for _ in range(n_trees):
        a = rnd.uniform(0, 2 * PI); rr = rnd.uniform(0.15, 0.8)
        x = math.cos(a) * 30 * rr; y = 32 + math.sin(a) * 22 * rr
        if y < 12 and abs(x) < 6: continue
        z = ground_z(x, y); h = rnd.uniform(2.5, 4.5)
        prim('cylinder', (x, y, z + h / 2), m=T, vertices=6, radius=0.16, depth=h)
        for k in range(3):
            prim('ico_sphere', (x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6), z + h + rnd.uniform(-0.3, 0.6)), m=rnd.choice(F),
                 subdivisions=1, radius=rnd.uniform(1.0, 1.6))
    return tufts

LIGHTHOUSE = V(0, 32, 0)
def lighthouse():
    z = ground_z(0, 32); LIGHTHOUSE.z = z
    W = mat('#F4F1EA', 0.6); R = mat('#C8352B', 0.6)
    for i in range(5):
        prim('cylinder', (0, 32, z + 0.9 + i * 1.6), m=R if i % 2 else W, vertices=16, radius=1.25 - i * 0.12, depth=1.6)
    prim('cylinder', (0, 32, z + 8.9), m=mat('#FFE89A', 0.2, emit=4.0), vertices=12, radius=0.75, depth=1.0)
    prim('cone', (0, 32, z + 9.9), m=R, vertices=16, radius1=0.95, depth=1.0)
    beam = empty((0, 32, z + 8.9))
    prim('cone', (0, 6, 0), rot=(PI / 2, 0, 0), m=mat('#FFF3C4', 1.0, emit=2.0, alpha=0.18), parent=beam, vertices=16, radius1=1.8, radius2=0.2, depth=12)
    prim('cube', (0, 30.7, z + 0.9), scale=(0.7, 0.1, 1.3), m=mat('#5A3B22', 0.8), size=1)
    return beam

def boat(x, y):
    root = empty((x, y, 0))
    H = mat('#F2F2F2', 0.5); BL = mat('#1E5FA8', 0.5)
    hull = prim('cube', (0, 0, 0.25), scale=(1.7, 4.4, 0.9), m=H, parent=root, size=1)
    bv = hull.modifiers.new('bv', 'BEVEL'); bv.width = 0.25; bv.segments = 3
    prim('cube', (0, 0, -0.05), scale=(1.72, 4.42, 0.3), m=BL, parent=root, size=1)
    prim('cube', (0, -1.2, 1.05), scale=(1.2, 1.3, 0.9), m=H, parent=root, size=1)
    prim('cube', (0, -1.2, 1.25), scale=(1.22, 1.32, 0.3), m=mat('#7FC7EA', 0.1), parent=root, size=1)
    prim('cube', (0, 2.0, 0.72), scale=(1.4, 0.06, 0.12), m=BL, parent=root, size=1)
    return root

def navy_ship(x, y):
    root = empty((x, y, 0))
    G = mat('#7C8794', 0.6); D = mat('#5C6672', 0.6)
    h = prim('cube', (0, 0, 0.6), scale=(16, 3.4, 2.2), m=G, parent=root, size=1)
    bv = h.modifiers.new('bv', 'BEVEL'); bv.width = 0.5; bv.segments = 2
    prim('cone', (8.6, 0, 0.6), rot=(0, PI / 2, 0), scale=(1.1, 1.7, 1), m=G, parent=root, vertices=4, radius1=1.6, depth=2.5)
    prim('cube', (-1.5, 0, 2.4), scale=(5, 2.6, 1.6), m=D, parent=root, size=1)
    prim('cube', (-1.0, 0, 3.7), scale=(2.8, 2.0, 1.1), m=G, parent=root, size=1)
    prim('cube', (-0.6, 0, 4.0), scale=(1.6, 2.05, 0.35), m=mat('#2A3440', 0.1), parent=root, size=1)
    prim('cylinder', (-1.2, 0, 5.8), m=D, parent=root, vertices=8, radius=0.1, depth=3.4)
    fl = prim('plane', (-1.2, 0.0, 7.1), rot=(PI / 2, 0, 0), scale=(0.9, 0.6, 1), m=flag_mat_plane('bra'), parent=root, size=1)
    prim('cube', (0, 0, -0.45), scale=(16.05, 3.45, 0.2), m=mat('#B23A32', 0.6), parent=root, size=1)
    return root, fl

def flag_mat_plane(code):
    key = 'flagp_' + code
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    img = nt.nodes.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(os.path.join(FLAGDIR, code + '.png'))
    nt.links.new(img.outputs['Color'], b.inputs['Base Color']); MATS[key] = m; return m

def clouds(rnd, n=10):
    C = mat('#FFFFFF', 0.95, emit=0.6, key='cloud'); C.shadow_method = 'NONE'
    for _ in range(n):
        x = rnd.uniform(-150, 150); y = rnd.uniform(120, 260); z = rnd.uniform(35, 70); s = rnd.uniform(6, 12)
        for i in range(5):
            prim('ico_sphere', (x + (i - 2) * s * 0.8, y + rnd.uniform(-2, 2), z + rnd.uniform(-1, 2)), m=C, subdivisions=1, radius=s * rnd.uniform(0.6, 1.1))

def mainland(rnd):
    M = mat('#5E9A48', 0.9)
    for i in range(6):
        prim('ico_sphere', (-160 + i * 30, 330, -5), scale=(30, 14, rnd.uniform(12, 22)), m=M, subdivisions=2, radius=1)

def sea_time(t): SEA.modifiers['oc'].time = 2.0 + t * 0.9

# ------------------------------------------------------------------ escenas compartidas por varias tomas
def snakes_field(rnd, n, region, coils=0.4):
    """Crea n serpientes repartidas sobre las rocas/hierba en region=(x0,x1,y0,y1)."""
    out = []
    for i in range(n):
        x = rnd.uniform(region[0], region[1]); y = rnd.uniform(region[2], region[3]); z = ground_z(x, y)
        s = Snake(L=rnd.uniform(1.1, 1.6)); kind = 'coil' if rnd.random() < coils else 'slither'
        out.append((s, V(x, y, z), kind, rnd.uniform(0, 2 * PI), rnd.uniform(0, 6)))
    return out

def update_snakes(field, t, raise_k=1.0, appear=None):
    for i, (s, base, kind, ang, ph) in enumerate(field):
        vis = True if appear is None else t >= appear[i]
        s.curve.hide_render = not vis
        for ch in s.head.children_recursive: ch.hide_render = not vis
        if not vis: continue
        if kind == 'coil':
            pts = path_coil(base, t, phase=ph, look=ang, raise_head=0.35 * raise_k)
        else:
            pts = path_slither(base, ang, s.L, t, speed=0.12, phase=ph, raise_head=0.25 * raise_k)
        s.set(pts, tongue=1.0 if math.sin(t * 5 + ph * 3) > 0.6 else 0.0)

# ------------------------------------------------------------------ TOMAS
def shot_island_common(boat_xy=(2, -14), navy=False, detail=True):
    rnd = build_world()
    tufts = vegetation(rnd)
    beam = lighthouse(); clouds(rnd); mainland(rnd)
    bt = boat(*boat_xy)
    bra = Ball('bra', 0.42); mex = Ball('mex', 0.42); usa = Ball('usa', 0.42); usa.add_glasses()
    for b in (bra, mex, usa): b.root.location = V(0, -300, -80)
    return rnd, tufts, beam, bt, bra, mex, usa

def place_on_boat(bt, ball, slot, t, **kw):
    pos = bt.location + V([-0.35, 0.45, 0.0][slot], [0.4, 0.9, 1.4][slot], 0.72)
    kw.setdefault('yaw', 0.55)
    ball.set(pos, **kw)

def hidden_snake(rnd):
    s = Snake(L=1.3)
    return s, V(0.9, 3.9, ground_z(0.9, 3.9) - 0.05)

def A1():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((1.5, -16))
    hs, hb = hidden_snake(rnd)
    cam, tgt = make_cam(28)
    def anim(t):
        sea_time(t); beam.rotation_euler.z = t * 1.2
        bt.location = V(1.5, -16 + t * 0.5, 0.15 * math.sin(t * 1.8)); bt.rotation_euler = (0.03 * math.sin(t * 1.5), 0.04 * math.sin(t * 1.2), 0)
        hs.set(path_coil(hb, t, raise_head=0.1, phase=1.0, look=-1.9), tongue=1.0 if 0.4 < t < 0.7 else 0.0)
        for k, tf in enumerate(tufts[:40]): tf.rotation_euler = (0.08 * math.sin(t * 3 + k), 0, 0)
        place_on_boat(bt, bra, 0, t, eyes='wide' if t > 4.0 else 'normal', look=(0, 0.3))
        place_on_boat(bt, mex, 1, t, eyes='normal', look=(0, 0.3))
        place_on_boat(bt, usa, 2, t, eyes='smug')
        if t < 0.9:
            p = V(-1.2, -0.6, 2.0) + V(0.05 * t, -0.1 * t, 0); g = V(0.9, 4.1, 0.6)
        elif t < 2.6:
            u = eo((t - 0.9) / 1.7)
            p = V(-1.15, -0.7, 2.0).lerp(V(-6, -42, 20), u); g = V(0.9, 4.1, 0.6).lerp(V(0, 22, 4), u)
        else:
            u = sm((t - 2.6) / 3.3)
            p = V(-6, -42, 20).lerp(V(4.5, -21, 2.6), u); g = V(0, 22, 4).lerp(V(1.5, -12, 1.2), u)
        cam.location = p; tgt.location = g
    return anim

def A5():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((1.5, -16))
    hs, hb = hidden_snake(rnd)
    cam, tgt = make_cam(28)
    def anim(t):
        sea_time(t + 40)
        for k, tf in enumerate(tufts[:40]): tf.rotation_euler = (0.08 * math.sin(t * 3 + k), 0, 0)
        raise_ = sm((t - 2.6) / 0.6)
        hs.set(path_coil(hb, t, raise_head=0.1 + 0.3 * raise_, phase=1.0, look=-1.9 + 0.3 * raise_), tongue=1.0 if (t > 3.2 and math.sin(t * 9) > 0) else 0.0)
        for b in (bra, mex, usa): b.root.location = V(0, -100, -50)
        u = sm(t / 4.0)
        cam.location = V(-1.2, -0.6, 2.0).lerp(V(0.35, 3.0, 0.9), u); tgt.location = V(0.9, 4.1, 0.6).lerp(V(0.75, 3.75, 0.55), u)
    return anim

def A2():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((3, -20))
    ship, fl = navy_ship(26, -8)
    cam, tgt = make_cam(30)
    def anim(t):
        sea_time(t + 6); beam.rotation_euler.z = t * 1.2
        ship.location = V(26 - t * 4.2, -8, 0.1 * math.sin(t)); ship.rotation_euler = (0, 0.02 * math.sin(t * 0.8), PI)
        fl.scale.y = 0.6 + 0.05 * math.sin(t * 8)
        bt.location = V(3, -20, 0.15 * math.sin(t * 1.8)); bt.rotation_euler = (0.03 * math.sin(t * 1.5), 0.04 * math.sin(t * 1.2), 0)
        place_on_boat(bt, bra, 0, t, eyes='worried' if t > 1.5 else 'normal', look=(-0.6, 0.2))
        place_on_boat(bt, mex, 1, t, eyes='normal', look=(-0.6, 0.2))
        place_on_boat(bt, usa, 2, t, eyes='smug')
        cam.location = V(6.5, -25.5, 2.3) + V(-t * 0.25, 0, 0); tgt.location = V(1.0, -12, 2.2)
    return anim

def A3():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((0.6, -3.2))
    cam, tgt = make_cam(28)
    land = V(0.4, 1.3, ground_z(0.4, 1.3))
    def anim(t):
        sea_time(t + 12)
        bt.location = V(0.6, -3.2, 0.12 * math.sin(t * 1.8)); bt.rotation_euler = (0.02 * math.sin(t * 1.5), 0.03 * math.sin(t * 1.2), 0)
        place_on_boat(bt, bra, 0, t, eyes='worried', look=(0.3, 0.3))
        place_on_boat(bt, mex, 1, t, eyes='wide', look=(0.3, 0.4))
        start = bt.location + V(0.0, 1.4, 0.72)
        if t < 0.8:
            usa.set(start, yaw=-0.8, eyes='smug', squash=1 - 0.2 * sm(t / 0.8))
        elif t < 1.7:
            u = (t - 0.8) / 0.9
            p = start.lerp(land, u); p.z += 2.0 * math.sin(u * PI)
            usa.set(p, yaw=-0.8, eyes='smug', squash=1.15 - 0.15 * abs(math.sin(u * PI)), tilt=-0.4 * math.sin(u * PI))
        else:
            u = (t - 1.7)
            sq = 1 - 0.3 * math.exp(-u * 6) * math.cos(u * 18)
            usa.set(land, yaw=-0.9 * sm((t - 2.1) / 0.5), eyes='smug', squash=sq)
        cam.location = V(5.5, -1.8, 2.0) + V(-0.3 * t, 0.1 * t, 0); tgt.location = V(0.5, 0.0, 1.0)
    return anim

def B1():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((0.6, -6))
    cam, tgt = make_cam(30)
    land = V(0.4, 1.3, ground_z(0.4, 1.3))
    sn = Snake(L=1.6); base = V(-1.6, 3.6, ground_z(-1.6, 3.6))
    near = sorted(tufts, key=lambda e: (e.location - land).length)[:8]
    def anim(t):
        sea_time(t + 16)
        freeze = sm((t - 1.2) / 0.3)
        usa.set(land, yaw=0.0, eyes='smug' if freeze < 0.5 else 'wide', look=(-0.9 * freeze, 0), squash=1 + 0.03 * math.sin(t * 30) * freeze)
        for k, tf in enumerate(near): tf.rotation_euler = (0.35 * math.sin(t * 14 + k) * sm((t - 0.4) / 0.3), 0.2 * math.sin(t * 11 + k), 0)
        sn.set(path_slither(base, 0.1, 1.6, t, speed=0.35, raise_head=0.0, z=base.z - 0.06), tongue=0.0)
        u = sm(t / 3.6)
        cam.location = V(1.6, -2.4, 1.2).lerp(V(0.9, -0.9, 1.05), u); tgt.location = V(0.0, 2.0, 0.8).lerp(V(0.2, 1.6, 0.85), u)
    return anim

def B2():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((0.6, -6))
    cam, tgt = make_cam(28)
    land = V(0.4, 1.3, ground_z(0.4, 1.3))
    pops = [(-1.0, 2.6, 0.2, -0.6), (1.7, 2.9, 0.8, -2.4), (-0.2, 3.6, 1.4, -1.6)]
    sns = [Snake(L=1.3) for _ in pops]
    def anim(t):
        sea_time(t + 20)
        usa.set(land, yaw=0.0, eyes='scared', look=(0.8 * math.sin(t * 3), 0.1), squash=1 + 0.03 * math.sin(t * 40))
        for s, (x, y, t0, look) in zip(sns, pops):
            r = eo((t - t0) / 0.25) if t >= t0 else 0.0
            s.set(path_coil(V(x, y, ground_z(x, y) - 0.25 * (1 - r)), t, raise_head=0.45 * r, phase=x, look=look), tongue=1.0 if (t - t0) > 0.3 and math.sin(t * 10) > 0 else 0.0)
            s.curve.hide_render = r <= 0
            for ch in s.head.children_recursive: ch.hide_render = r <= 0
        z = 1.0 + 0.08 * sum(max(0.0, 1 - abs(t - p[2] - 0.1) * 6) for p in pops)
        cam.location = V(0.4, -2.6, 1.6) + (V(0.4, 1.6, 0.9) - V(0.4, -2.6, 1.6)) * (0.12 * (z - 1) * 10)
        tgt.location = V(0.4, 1.8, 0.8)
    return anim

def B3():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((0.6, -6))
    usa.add_sweat()
    cam, tgt = make_cam(28)
    land = V(0.4, 1.3, ground_z(0.4, 1.3))
    field = snakes_field(random.Random(9), 34, (-7, 7, 0.0, 9.0))
    field = [f for f in field if (f[1] - land).length > 1.0]
    def anim(t):
        sea_time(t + 24)
        usa.set(land, yaw=0.0, eyes='scared', look=(0.9 * math.sin(t * 2.5), 0.2), squash=1 + 0.03 * math.sin(t * 40), sweat=t)
        update_snakes(field, t)
        u = sm(t / 4.1)
        cam.location = V(0.4, -1.6, 1.2).lerp(V(0.0, -9.5, 8.0), u); tgt.location = V(0.4, 1.5, 0.8).lerp(V(0.0, 4.5, 0.5), u)
    return anim

def B4():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((0.6, -6))
    usa.add_sweat()
    cam, tgt = make_cam(35)
    sn = Snake(L=1.6); base = V(-0.6, 3.0, ground_z(-0.6, 3.0))
    land = V(0.4, 1.3, ground_z(0.4, 1.3))
    def anim(t):
        sea_time(t + 30)
        sn.set(path_coil(base, t, raise_head=0.45, phase=0.5, look=-1.3 + 0.15 * math.sin(t * 0.8)),
               tongue=1.0 if math.sin(t * 6) > 0.2 else 0.0)
        usa.set(land, yaw=0.5, eyes='scared', look=(-0.7, 0.2), squash=1 + 0.03 * math.sin(t * 40), sweat=t)
        hp = sn.head.matrix_world.translation if t > 0 else base
        bpy.context.view_layer.update()
        hp = sn.head.matrix_world.translation.copy()
        if t < 5.0:
            a = -0.4 - 0.5 * sm(t / 5.0)
            cam.location = hp + V(math.cos(a) * 0.75, math.sin(a) * 0.75, 0.12 + 0.05 * math.sin(t)); tgt.location = hp + V(0, 0, -0.05)
        else:
            u = sm((t - 5.0) / 1.2)
            cam.location = (hp + V(math.cos(-0.9) * 0.75, math.sin(-0.9) * 0.75, 0.12)).lerp(land + V(0.3, -1.7, 0.8), u)
            tgt.location = hp.lerp(land + V(0, 0, 0.5), u)
    return anim

def C1():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((3, -20))
    cam, tgt = make_cam(30)
    def anim(t):
        sea_time(t + 36); beam.rotation_euler.z = t * 1.2
        bt.location = V(3, -20, 0.15 * math.sin(t * 1.8)); bt.rotation_euler = (0.03 * math.sin(t * 1.5), 0.04 * math.sin(t * 1.2), 0)
        place_on_boat(bt, bra, 0, t, yaw=1.0, eyes='worried', look=(0.0, 0.3))
        place_on_boat(bt, mex, 1, t, yaw=1.15, eyes='think' if t > 0.8 else 'normal', look=(0.5, 0.7) if t > 0.8 else (0, 0.2))
        usa.root.location = V(0, -200, -50)
        mp = bt.location + V(0.45, 0.9, 1.2)
        u = sm(t / 4.6)
        cam.location = (mp + V(2.9, -1.2, 0.7)).lerp(mp + V(1.4, -0.6, 0.3), u); tgt.location = mp + V(-0.2, 0, -0.1)
    return anim

def C2():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((3, -20))
    usa.add_sweat()
    cam, tgt = make_cam(30)
    def anim(t):
        sea_time(t + 60); beam.rotation_euler.z = t * 1.2
        bt.location = V(3, -20, 0.15 * math.sin(t * 1.8)); bt.rotation_euler = (0.03 * math.sin(t * 1.5), 0.04 * math.sin(t * 1.2), 0)
        look_cam = sm((t - 1.6) / 0.4)
        place_on_boat(bt, bra, 0, t, eyes='worried', look=(0, 0.2))
        place_on_boat(bt, mex, 1, t, eyes='wide' if look_cam > 0.5 else 'normal', look=(0, 0.1))
        place_on_boat(bt, usa, 2, t, eyes='scared', glasses=0.0, sweat=t, squash=1 + 0.03 * math.sin(t * 35))
        for b in (bra, mex, usa): b.root.rotation_euler.z = PI - (PI - 0.0) * look_cam
        mp = bt.location + V(0.0, 0.9, 1.0)
        u = sm(t / 4.0)
        cam.location = (mp + V(0.3, 6.0, 1.2)).lerp(mp + V(0.1, 3.0, 0.5), u); tgt.location = mp
    return anim

def B5():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((3, -20))
    for b in (bra, mex, usa): b.root.location = V(0, -200, -50)
    T = mat('#6B4A2B', 0.9)
    gz = ground_z(4.5, 6)
    prim('cylinder', (3.4, 6, gz + 1.4), m=T, vertices=8, radius=0.2, depth=2.8)
    prim('cylinder', (4.6, 6, gz + 2.3), rot=(0, PI / 2, 0), m=T, vertices=8, radius=0.09, depth=2.6)
    prim('cylinder', (7.6, 6, gz + 1.25), m=T, vertices=6, radius=0.1, depth=2.5)
    for k in range(3): prim('ico_sphere', (3.2 + k * 0.4, 6.3, gz + 3.2), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=1.0)
    sn = Snake(L=1.6); bird = Bird(1.0)
    cam, tgt = make_cam(32)
    def anim(t):
        sea_time(t + 41)
        ext = sm((t - 2.4) / 1.0)
        pts = []
        for i in range(Snake.N):
            u = i / (Snake.N - 1)
            x = 3.7 + u * 1.55 + 0.06 * math.sin(u * 9 + t * 2) * (1 - u)
            y = 6 + 0.06 * math.sin(u * 12 + t * 1.5)
            z = gz + 2.39 + 0.25 * ext * sm((u - 0.8) / 0.2)
            pts.append(V(x, y, z))
        sn.set(pts, tongue=1.0 if math.sin(t * 7) > 0.3 else 0.0)
        if t < 2.0:
            u = sm(t / 2.0)
            p = V(14, 2, gz + 6).lerp(V(7.6, 6, gz + 2.62), u); bird.set(p, yaw=PI / 2 + 0.3, flap=t * 22, pitch=-0.2 * (1 - u))
        else:
            bird.set(V(7.6, 6, gz + 2.62), yaw=PI / 2, flap=0, fold=1.0, pitch=0.05 * math.sin(t * 3))
        u = sm(t / 5.2)
        cam.location = V(5.6, 1.5, gz + 2.6).lerp(V(5.4, 3.2, gz + 2.5), u); tgt.location = V(6.1, 6, gz + 2.4)
    return anim

def B6():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((3, -20))
    for b in (bra, mex, usa): b.root.location = V(0, -200, -50)
    T = mat('#6B4A2B', 0.9)
    gz = ground_z(4.5, 6)
    prim('cylinder', (3.4, 6, gz + 1.4), m=T, vertices=8, radius=0.2, depth=2.8)
    prim('cylinder', (4.6, 6, gz + 2.3), rot=(0, PI / 2, 0), m=T, vertices=8, radius=0.09, depth=2.6)
    prim('cylinder', (7.6, 6, gz + 1.25), m=T, vertices=6, radius=0.1, depth=2.5)
    for k in range(3): prim('ico_sphere', (3.2 + k * 0.4, 6.3, gz + 3.2), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=1.0)
    sn = Snake(L=1.6); bird = Bird(1.0)
    cam, tgt = make_cam(32)
    def anim(t):
        sea_time(t + 47)
        # ataque: 0.6-0.85 s ; luego el pájaro huye volando lejos; al final la serpiente vuelve a atacar hacia la cámara
        lunge = sm((t - 0.6) / 0.18) * (1 - sm((t - 1.2) / 0.5))
        lunge2 = sm((t - 5.3) / 0.15)
        pts = []
        for i in range(Snake.N):
            u = i / (Snake.N - 1)
            x = 3.7 + u * 1.55 + lunge * 1.6 * sm((u - 0.55) / 0.45) + 0.04 * math.sin(u * 9 + t * 2)
            y = 6 - lunge2 * 1.2 * sm((u - 0.6) / 0.4)
            z = gz + 2.39 + 0.25 * sm((u - 0.8) / 0.2) + lunge * 0.25 * sm((u - 0.7) / 0.3) + lunge2 * 0.15 * sm((u - 0.7) / 0.3)
            pts.append(V(x, y, z))
        sn.set(pts, tongue=1.0 if (t > 3.6 and math.sin(t * 8) > 0) else 0.0)
        if t < 0.75:
            bird.set(V(7.6, 6, gz + 2.62), yaw=PI / 2, fold=1.0)
        else:
            u = t - 0.75
            p = V(7.6 + u * 4.0, 6 + u * 9.0, gz + 2.62 + u * 2.2 - max(0.0, u - 2.2) ** 2 * 0.6)
            bird.set(p, yaw=-0.45, flap=u * 24, pitch=-0.2, fold=0.0)
        if t < 0.9:
            cam.location = V(5.6, 2.6, gz + 2.55); tgt.location = V(6.4, 6, gz + 2.5)
            cam.location += shake(t, 0.62, 0.3, 0.08)
        elif t < 3.6:
            u = sm((t - 0.9) / 2.7)
            bpy.context.view_layer.update()
            bp = bird.root.matrix_world.translation.copy()
            cam.location = V(5.6, 2.6, gz + 2.55).lerp(V(6.0, 2.0, gz + 3.2), u); tgt.location = bp
        else:
            u = sm((t - 3.6) / 1.4)
            hp = V(5.2, 6, gz + 2.65)
            cam.location = V(5.0, 4.2, gz + 2.7).lerp(V(5.15, 4.9, gz + 2.68), u); tgt.location = hp
            cam.location += shake(t, 5.3, 0.4, 0.05)
    return anim

def A4():
    rnd, tufts, beam, bt, bra, mex, usa = shot_island_common((3, -20))
    for b in (bra, mex, usa): b.root.location = V(0, -200, -50)
    z = LIGHTHOUSE.z
    field = []
    for k, (x, y) in enumerate([(1.2, 29.8), (-1.5, 30.2), (2.0, 31.2)]):
        s = Snake(L=1.3); field.append((s, V(x, y, ground_z(x, y)), 'coil', -PI / 2, k * 2.0))
    birds = [Bird(0.8) for _ in range(3)]
    cam, tgt = make_cam(28)
    def anim(t):
        sea_time(t + 53); beam.rotation_euler.z = t * 1.4
        update_snakes(field, t)
        for i, b in enumerate(birds):
            a = t * 0.5 + i * 2.1
            b.set(V(math.cos(a) * 8, 32 + math.sin(a) * 8, z + 12 + i), yaw=a + PI, flap=t * 14 + i)
        a = -1.9 + t * 0.12
        cam.location = V(math.cos(a) * 13, 32 + math.sin(a) * 13, z + 10 + t * 0.4); tgt.location = V(0, 32, z + 6 + t * 0.3)
    return anim

def D1():
    setup(world='#A6DBFF', strength=0.9, sun_rot=(50, 0, 30))
    rnd = random.Random(3)
    base = prim('cube', (0, 0, -1.6), scale=(20, 9, 2.0), m=mat('#6B4F35', 0.9), size=1)
    land = prim('cube', (-6.5, 0, -0.05), scale=(7, 8.6, 1.1), m=mat('#C9B58A', 0.9), size=1)
    prim('cube', (-6.5, 0, 0.55), scale=(7, 8.6, 0.12), m=mat('#5E9A48', 0.9), size=1)
    for i in range(10):
        prim('ico_sphere', (rnd.uniform(-9.5, -3.5), rnd.uniform(-3.8, 3.8), 0.9), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=rnd.uniform(0.35, 0.6))
    prim('cube', (-1.0, 0, -0.45), scale=(6.5, 2.6, 0.6), m=mat('#D9C79C', 0.9), size=1)
    isl = prim('ico_sphere', (4.2, 0, -0.2), scale=(2.6, 2.1, 1.9), m=mat('#4E8C3A', 0.9), subdivisions=2, radius=1)
    for i in range(6):
        prim('ico_sphere', (4.2 + rnd.uniform(-1.4, 1.4), rnd.uniform(-1.0, 1.0), 1.2 + rnd.uniform(0, 0.5)), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=0.4)
    dots = []
    for i in range(14):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(0.5, 1.8)
        dots.append(prim('uv_sphere', (4.2 + math.cos(a) * r * 1.1, math.sin(a) * r * 0.85, 1.0), scale=(0.18, 0.05, 0.05), rot=(0, 0, a), m=snake_mat(), segments=8, ring_count=6, radius=1))
    water = prim('cube', (0, 0, -1.6), scale=(19.9, 8.9, 1.0), m=mat('#2A9BC4', 0.1, alpha=0.78), size=1)
    cam, tgt = make_cam(30)
    def anim(t):
        lvl = lerp(-0.95, 0.35, sm((t - 1.0) / 2.6))
        water.scale.z = (lvl - (-2.6)); water.location.z = (-2.6 + lvl) / 2
        for k, d in enumerate(dots): d.location.z = 1.0 + 0.6 * 0 + 0.02 * math.sin(t * 4 + k)
        a = -1.25 + 0.12 * t
        cam.location = V(math.cos(a) * 15, math.sin(a) * 15, 9.5 - 0.3 * t); tgt.location = V(0.5, 0, -0.2)
    return anim

# ------------------------------------------------------------------ render
bpy.ops.wm.read_factory_settings(use_empty=True)
anim = globals()[SHOT]()
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
n = int(round(SHOTS[SHOT] * FPS))
for f in range(FSTART, min(FEND, n)):
    anim(f / FPS)
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUT, 'f%04d.jpg' % f)
    bpy.ops.render.render(write_still=True)
