# Biblioteca 3D compartida (utilidades, cámara, contornos, banderas, serpiente y pájaro).
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Euler

FLAGDIR = '.'; RESX = 540
FPS = 24; PI = math.pi


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

def setup(world='#93D3FF', strength=0.8, sun_rot=(48, 0, 35), sun_power=3.0, resx=None):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.fps = FPS
    rx = resx or RESX; sc.render.resolution_x = rx; sc.render.resolution_y = rx * 16 // 9; sc.render.resolution_percentage = 100
    e = sc.eevee; e.taa_render_samples = 10; e.use_gtao = True; e.gtao_distance = 1.0
    e.use_soft_shadows = True; e.shadow_cascade_size = '2048'; e.shadow_cube_size = '512'
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 93
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    # cielo con degradado vertical
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (*lin('#CFEAFB'), 1)
    ramp.color_ramp.elements[1].position = 0.28; ramp.color_ramp.elements[1].color = (*lin(world), 1)
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

# ------------------------------------------------------------------ banderas

def flag_mat(code):
    key = 'flag_' + code
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.45
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); comb = nt.nodes.new('ShaderNodeCombineXYZ')
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = 0.5; mx.inputs[2].default_value = 0.5
    mz = nt.nodes.new('ShaderNodeMath'); mz.operation = 'MULTIPLY_ADD'; mz.inputs[1].default_value = 0.5; mz.inputs[2].default_value = 0.5
    img = nt.nodes.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(os.path.join(globals()['FLAGDIR'], code + '.png')); img.extension = 'EXTEND'
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    nt.links.new(sep.outputs['X'], mx.inputs[0]); nt.links.new(sep.outputs['Z'], mz.inputs[0])
    nt.links.new(mx.outputs[0], comb.inputs['X']); nt.links.new(mz.outputs[0], comb.inputs['Y'])
    nt.links.new(comb.outputs[0], img.inputs['Vector']); nt.links.new(img.outputs['Color'], b.inputs['Base Color'])
    MATS[key] = m; return m

def flag_mat_plane(code):
    key = 'flagp_' + code
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    img = nt.nodes.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(os.path.join(FLAGDIR, code + '.png'))
    nt.links.new(img.outputs['Color'], b.inputs['Base Color']); MATS[key] = m; return m

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

