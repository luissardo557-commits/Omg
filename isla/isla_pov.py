# "La isla prohibida" — estilo 2D POV: personitas cartoon con contorno dentro de un mundo 3D detallado.
# Uso: blender -b -P isla_pov.py -- <toma> <carpeta_salida> <carpeta_banderas> [ancho] [frame_ini] [frame_fin]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh, math, random
from mathutils import Vector
import lib3d
from lib3d import *

argv = sys.argv[sys.argv.index('--') + 1:]
SHOT = argv[0]; OUT = argv[1]; lib3d.FLAGDIR = argv[2]
RESX = int(argv[3]) if len(argv) > 3 else 540
FSTART = int(argv[4]) if len(argv) > 4 else 0
FEND = int(argv[5]) if len(argv) > 5 else 10 ** 6
PI = math.pi; FPS = 24
SHOTS = {'A1': 5.92, 'A2': 5.46, 'A3': 3.63, 'B1': 3.67, 'B2': 2.22, 'B3': 4.22, 'B4': 6.89, 'C1': 4.67,
         'D1': 5.01, 'B5': 5.29, 'B6': 6.27, 'A4': 4.42, 'C2': 4.08, 'A5': 4.55}

def outlined(o, thick=1.06):
    add_outline(o, thick); return o

# ------------------------------------------------------------------ PERSONITA estilo 2D POV
class Person:
    """outfit: shirt ('usa' o hex), pants hex, shorts bool, hat ('cap_usa','straw','navy','bun' o None),
    mustache, glasses, camera, sleeves hex"""
    def __init__(s, outfit):
        o = dict(shirt='#2F7FE8', pants='#2B2B33', shorts=False, hat=None, mustache=False, glasses=False, camera=False, collar=None)
        o.update(outfit); s.o = o
        SKIN = mat('#FBFBF8', 0.55, key='skin'); K = mat('#18181C', 0.6, key='limb')
        s.root = empty(); s.pelvis = empty((0, 0, 0.80), s.root); s.chest = empty((0, 0, 0.05), s.pelvis)
        shirt = flag_mat('usa') if o['shirt'] == 'usa' else mat(o['shirt'], 0.7)
        torso = outlined(prim('uv_sphere', (0, 0, 0.24), scale=(0.24, 0.18, 0.31), m=shirt, smooth=True, parent=s.chest, segments=20, ring_count=12, radius=1), 1.07)
        if o['collar']:
            prim('cone', (0, -0.06, 0.5), rot=(0.2, 0, 0), m=mat(o['collar'], 0.6), parent=s.chest, vertices=12, radius1=0.16, radius2=0.08, depth=0.12)
        pz = 0.02 if not o['shorts'] else -0.02
        outlined(prim('uv_sphere', (0, 0, pz), scale=(0.225, 0.17, 0.16 if not o['shorts'] else 0.2), m=mat(o['pants'], 0.75), smooth=True, parent=s.pelvis, segments=18, ring_count=10, radius=1), 1.07)
        if o['camera']:
            prim('cube', (0.05, -0.2, 0.28), scale=(0.16, 0.07, 0.11), m=mat('#222226', 0.3, key='cam'), parent=s.chest, size=1)
            prim('cylinder', (0.05, -0.25, 0.28), rot=(PI / 2, 0, 0), m=mat('#4A4A55', 0.2, key='lens'), parent=s.chest, vertices=12, radius=0.045, depth=0.06)
            prim('torus', (0.0, -0.02, 0.38), rot=(0.4, 0, 0), m=K, parent=s.chest, major_radius=0.2, minor_radius=0.008, major_segments=16, minor_segments=4)
        s.neck = empty((0, 0, 0.52), s.chest)
        prim('cylinder', (0, 0, 0.04), m=K, smooth=True, parent=s.neck, vertices=8, radius=0.035, depth=0.14)
        s.head = empty((0, 0, 0.30), s.neck)
        hd = outlined(prim('uv_sphere', (0, 0, 0), m=SKIN, smooth=True, parent=s.head, segments=32, ring_count=20, radius=0.34), 1.045)
        # ojos: blanco + contorno + pupila
        EW = mat('#FFFFFF', 0.3, emit=0.2, key='eyew')
        s.eyes = []; s.pupils = []; s.brows = []
        for sd in (1, -1):
            piv = empty((0.115 * sd, -0.29, 0.05), s.head); piv.rotation_euler = (0, 0, 0.36 * sd)
            prim('uv_sphere', (0, -0.035, 0), scale=(0.085, 0.035, 0.105), m=EW, smooth=True, parent=piv, segments=20, ring_count=10, radius=1)
            prim('uv_sphere', (0, -0.022, 0), scale=(0.1, 0.03, 0.12), m=mat('#0A0A0A', 0.8, key='eyeol'), smooth=True, parent=piv, segments=20, ring_count=10, radius=1)
            pu = prim('uv_sphere', (0, -0.068, 0), scale=(0.034, 0.012, 0.04), m=mat('#0A0A0A', 0.2, key='pupil'), smooth=True, parent=piv, segments=12, ring_count=8, radius=1)
            s.eyes.append((piv, sd)); s.pupils.append(pu)
            bp = empty((0.115 * sd, -0.27, 0.19), s.head)
            prim('cylinder', (0, 0, 0), rot=(0, PI / 2, 0), m=K, smooth=True, parent=bp, vertices=8, radius=0.014, depth=0.1)
            s.brows.append((bp, sd))
        s.mouth = prim('uv_sphere', (0, -0.315, -0.13), scale=(0.06, 0.03, 0.014), m=mat('#0A0A0A', 0.6, key='mouth'), smooth=True, parent=s.head, segments=12, ring_count=8, radius=1)
        if o['mustache']:
            for sd in (1, -1):
                prim('uv_sphere', (0.055 * sd, -0.33, -0.065), rot=(0, 0.35 * sd, 0), scale=(0.07, 0.03, 0.028), m=mat('#2A1D14', 0.7, key='must'), smooth=True, parent=s.head, segments=12, ring_count=8, radius=1)
        s.glass = None
        if o['glasses']:
            g = empty((0, 0, 0), s.head); GL = mat('#050505', 0.12, key='sung')
            for sd in (1, -1):
                prim('cube', (0.115 * sd, -0.335, 0.06), rot=(0, 0, 0.36 * sd), scale=(0.15, 0.025, 0.1), m=GL, parent=g, size=1)
            prim('cube', (0, -0.345, 0.08), scale=(0.1, 0.02, 0.025), m=GL, parent=g, size=1)
            s.glass = g
        h = o['hat']
        if h == 'cap_usa':
            outlined(prim('uv_sphere', (0, 0.0, 0.12), scale=(0.35, 0.35, 0.25), m=flag_mat('usa'), smooth=True, parent=s.head, segments=24, ring_count=12, radius=1), 1.04)
            prim('cube', (0, -0.36, 0.19), rot=(-0.15, 0, 0), scale=(0.34, 0.26, 0.025), m=mat('#B22234', 0.6, key='brim'), parent=s.head, size=1)
        elif h == 'straw':
            prim('cylinder', (0, 0, 0.22), m=mat('#E3C27A', 0.8, key='straw'), parent=s.head, vertices=24, radius=0.6, depth=0.03)
            outlined(prim('cylinder', (0, 0, 0.33), m=mat('#E3C27A', 0.8, key='straw'), parent=s.head, vertices=20, radius=0.3, depth=0.22), 1.05)
            prim('cylinder', (0, 0, 0.27), m=mat('#1F8A3B', 0.6, key='band'), parent=s.head, vertices=20, radius=0.305, depth=0.06)
        elif h == 'navy':
            outlined(prim('cylinder', (0, 0, 0.3), scale=(1, 1, 1), m=mat('#F7F7F7', 0.5, key='navyc'), parent=s.head, vertices=24, radius=0.36, depth=0.12), 1.04)
            prim('cylinder', (0, 0, 0.24), m=mat('#1B2C4A', 0.5, key='navyb'), parent=s.head, vertices=24, radius=0.33, depth=0.07)
            prim('cube', (0, -0.33, 0.21), rot=(-0.25, 0, 0), scale=(0.32, 0.18, 0.02), m=mat('#111111', 0.2, key='visor'), parent=s.head, size=1)
        elif h == 'bun':
            hair = mat('#8A4B24', 0.7, key='hair')
            outlined(prim('uv_sphere', (0, 0.04, 0.07), scale=(0.36, 0.35, 0.31), m=hair, smooth=True, parent=s.head, segments=24, ring_count=12, radius=1), 1.04)
            outlined(prim('uv_sphere', (0, 0.12, 0.36), m=hair, smooth=True, parent=s.head, segments=16, ring_count=10, radius=0.13), 1.06)
        s.hd = hd
        s.sh = {}; s.el = {}; s.hand = {}; s.hip = {}; s.knee = {}
        SL = shirt if o['shirt'] != 'usa' else mat('#3C3B6E', 0.6, key='usasleeve')
        for side, sx in (('L', 1), ('R', -1)):
            sh = empty((0.25 * sx, 0, 0.44), s.chest)
            prim('uv_sphere', (0, 0, -0.02), m=SL, smooth=True, parent=sh, segments=12, ring_count=8, radius=0.085)
            prim('cylinder', (0, 0, -0.15), m=K, smooth=True, parent=sh, vertices=8, radius=0.03, depth=0.30)
            el = empty((0, 0, -0.30), sh)
            prim('cylinder', (0, 0, -0.14), m=K, smooth=True, parent=el, vertices=8, radius=0.028, depth=0.28)
            prim('uv_sphere', (0, 0, -0.30), m=K, smooth=True, parent=el, segments=10, ring_count=8, radius=0.05)
            s.hand[side] = empty((0, 0, -0.32), el); s.sh[side] = sh; s.el[side] = el
            hp = empty((0.10 * sx, 0, -0.02), s.pelvis)
            prim('cylinder', (0, 0, -0.18), m=K, smooth=True, parent=hp, vertices=8, radius=0.036, depth=0.36)
            kn = empty((0, 0, -0.36), hp)
            prim('cylinder', (0, 0, -0.17), m=K, smooth=True, parent=kn, vertices=8, radius=0.034, depth=0.34)
            outlined(prim('uv_sphere', (0, -0.05, -0.37), scale=(0.065, 0.12, 0.045), m=mat('#3A2A20', 0.6, key='shoe'), smooth=True, parent=kn, segments=12, ring_count=8, radius=1), 1.1)
            s.hip[side] = hp; s.knee[side] = kn

    def pose(s, pos=(0, 0, 0), yaw=0.0, walk=0.0, amp=0.0, lean=0.0, twist=0.0, nod=0.0, turn=0.0, tilt=0.0,
             armL=None, armR=None, mouth=0.0, worry=0.0, browup=0.0, crouch=0.0, wide=0.0, squint=0.0, look=(0.0, 0.0),
             glasses=1.0, smile=0.0, sweat=0.0):
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
        defL = (0.4 * a * math.sin(p), -0.1, 0, -0.25 - 0.2 * a)
        defR = (-0.4 * a * math.sin(p), 0.1, 0, -0.25 - 0.2 * a)
        for side, arm in (('L', armL or defL), ('R', armR or defR)):
            s.sh[side].rotation_euler = arm[:3]; s.el[side].rotation_euler = (arm[3], 0, 0)
        s.mouth.scale = (0.06 - 0.02 * mouth + 0.02 * smile, 0.03, 0.014 + 0.05 * mouth)
        s.mouth.location.z = -0.13 - 0.01 * mouth
        for bp, sd in s.brows:
            bp.rotation_euler = (0, sd * 0.45 * worry - sd * 0.35 * squint, 0); bp.location.z = 0.19 + 0.045 * browup - 0.03 * squint
        for (piv, sd), pu in zip(s.eyes, s.pupils):
            piv.scale = (1 + 0.1 * wide, 1, (1 + 0.22 * wide) * (1 - 0.5 * squint))
            pu.location = (look[0] * 0.04, -0.068, look[1] * 0.045)
            pu.scale = (0.034 * (1 - 0.25 * wide), 0.012, 0.04 * (1 - 0.25 * wide))
        if s.glass is not None:
            s.glass.location = (0, 0, (1 - glasses) * 0.0); s.glass.location.y = 0
            for ch in s.glass.children: ch.hide_render = glasses < 0.5

    def hand_pos(s, side):
        bpy.context.view_layer.update(); return s.hand[side].matrix_world.translation.copy()

TOURIST = dict(shirt='usa', pants='#C8B48A', shorts=True, hat='cap_usa', glasses=True, camera=True)
CAPTAIN = dict(shirt='#F2C230', pants='#2C4E8A', hat='straw', mustache=True, collar='#1F8A3B')
GIRL = dict(shirt='#E86A9A', pants='#3B4C78', hat='bun')
NAVY = dict(shirt='#F5F5F5', pants='#F5F5F5', hat='navy', collar='#1B2C4A')

# ------------------------------------------------------------------ mundo detallado
SEA = None
def building_mat(wall):
    key = 'bld_' + wall
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.8
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); add = nt.nodes.new('ShaderNodeMath')
    comb = nt.nodes.new('ShaderNodeCombineXYZ'); br = nt.nodes.new('ShaderNodeTexBrick')
    nt.links.new(geo.outputs['Position'], sep.inputs[0]); nt.links.new(sep.outputs['X'], add.inputs[0]); nt.links.new(sep.outputs['Y'], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs['X']); nt.links.new(sep.outputs['Z'], comb.inputs['Y'])
    nt.links.new(comb.outputs[0], br.inputs['Vector'])
    br.offset = 0.0; br.squash = 1.0
    br.inputs['Color1'].default_value = (*lin('#3E5F80'), 1); br.inputs['Color2'].default_value = (*lin('#577A9C'), 1)
    br.inputs['Mortar'].default_value = (*lin(wall), 1); br.inputs['Scale'].default_value = 0.42
    br.inputs['Mortar Size'].default_value = 0.42; br.inputs['Brick Width'].default_value = 1.0; br.inputs['Row Height'].default_value = 1.15
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    MATS[key] = m; return m

def mainland_town(rnd):
    # montañas verdes (Serra do Mar) y ciudad costera al fondo
    for i in range(9):
        x = -260 + i * 65 + rnd.uniform(-15, 15)
        prim('cone', (x, 430 + rnd.uniform(-20, 30), -2), rot=(0, 0, rnd.uniform(0, 3)), scale=(1, 0.7, 1), m=mat(rnd.choice(['#5D8F6E', '#6E9C7A', '#7FA88A']), 0.95),
             vertices=7, radius1=rnd.uniform(60, 90), depth=rnd.uniform(60, 110))
    prim('cube', (0, 335, 0.5), scale=(700, 40, 1.0), m=mat('#E4D3A6', 0.9), size=1)
    walls = ['#F3EBDD', '#EED9B6', '#F5F0E6', '#E9C7A5', '#D9E4EC', '#F2D2C2', '#E6E0C8']
    x = -230.0
    while x < 230:
        w = rnd.uniform(8, 16); d = rnd.uniform(8, 12); h = rnd.uniform(8, 30)
        y = rnd.uniform(345, 360)
        prim('cube', (x, y, h / 2), scale=(w, d, h), m=building_mat(rnd.choice(walls)), size=1)
        prim('cube', (x, y, h + 0.4), scale=(w + 0.6, d + 0.6, 0.8), m=mat('#B9A58A', 0.8), size=1)
        if rnd.random() < 0.5:
            prim('cone', (x, y, h + 2.0), rot=(0, 0, PI / 4), scale=(w * 0.74, d * 0.74, 1), m=mat('#C8653C', 0.8), vertices=4, radius1=1, depth=3.0)
        if rnd.random() < 0.25:
            h2 = h * rnd.uniform(1.3, 1.8)
            prim('cube', (x + rnd.uniform(-20, 20), y + 18, h2 / 2), scale=(w, d, h2), m=building_mat(rnd.choice(walls)), size=1)
        x += w + rnd.uniform(2, 8)
    for i in range(30):
        prim('ico_sphere', (rnd.uniform(-230, 230), rnd.uniform(338, 342), 3), m=mat('#3F7F3A', 0.8), subdivisions=1, radius=rnd.uniform(2.5, 4))

def puffy_clouds(rnd, n=9):
    C = mat('#FFFFFF', 0.9, emit=0.45, key='cloud2'); C.shadow_method = 'NONE'
    for _ in range(n):
        x = rnd.uniform(-200, 200); y = rnd.uniform(200, 420); z = rnd.uniform(45, 95); s = rnd.uniform(8, 16)
        for i in range(7):
            prim('uv_sphere', (x + (i - 3) * s * 0.6, y + rnd.uniform(-3, 3), z + (s * 0.35 if i in (2, 3, 4) else 0) + rnd.uniform(-1, 1)),
                 scale=(1, 0.8, 0.75), m=C, smooth=True, segments=16, ring_count=10, radius=s * rnd.uniform(0.5, 0.85))

def palm(x, y, z, h, rnd):
    T = mat('#8A6440', 0.9, key='palmt'); L = mat('#3F8F3A', 0.7, key='palml')
    n = 6; px, py = x, y
    lean = V(rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 0)
    for i in range(n):
        u = i / n
        c = V(x, y, z) + lean * h * u * u + V(0, 0, h * (u + 0.5 / n))
        prim('cylinder', c, rot=(lean.y * 0.6 * u * -1, lean.x * 0.6 * u, 0), m=T, vertices=7, radius=0.22 - 0.06 * u, depth=h / n * 1.05)
    top = V(x, y, z) + lean * h + V(0, 0, h)
    for k in range(7):
        a = k / 7 * 2 * PI + rnd.uniform(-0.2, 0.2)
        e = empty(top); e.rotation_euler = (0, 0, a)
        prim('cube', (1.3, 0, -0.35), rot=(0, 0.45, 0), scale=(2.6, 0.55, 0.04), m=L, parent=e, size=1)
    prim('ico_sphere', top + V(0, 0, -0.15), m=mat('#6B4A2B', 0.8, key='coco'), subdivisions=1, radius=0.25)

def warning_sign(x, y, z):
    P = mat('#7A5A3A', 0.8, key='post'); Y = mat('#F2C230', 0.5, key='signy'); K = mat('#111111', 0.6, key='signk')
    prim('cylinder', (x, y, z + 0.9), m=P, vertices=8, radius=0.06, depth=1.8)
    e = empty((x, y - 0.08, z + 1.85)); e.rotation_euler = (PI / 2, 0, 0)
    prim('cylinder', (0, 0, 0), m=K, parent=e, vertices=3, radius=0.62, depth=0.04).rotation_euler.z = PI / 2
    prim('cylinder', (0, 0, 0.012), m=Y, parent=e, vertices=3, radius=0.52, depth=0.04).rotation_euler.z = PI / 2
    cu = bpy.data.curves.new('ss', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.025
    sp = cu.splines.new('POLY'); sp.points.add(11)
    for i, p in enumerate(sp.points):
        u = i / 11; p.co = (x - 0.22 + u * 0.44, y - 0.12, z + 1.75 + 0.07 * math.sin(u * 3 * PI), 1)
    o = link(bpy.data.objects.new('ss', cu)); cu.materials.append(K)

def ruin_wall(x, y, z, rnd):
    S = [mat('#B8AE9C', 0.9), mat('#A39A88', 0.9)]
    for row in range(4):
        for col in range(6 - row):
            prim('cube', (x + col * 0.52 + row * 0.26 + rnd.uniform(-0.03, 0.03), y, z + 0.22 + row * 0.42), rot=(0, 0, rnd.uniform(-0.05, 0.05)),
                 scale=(0.48, 0.4, 0.38), m=rnd.choice(S), size=1)

def build_world():
    setup(world='#5DAEEA', resx=RESX)
    rnd = random.Random(5)
    global SEA
    SEA = prim('plane', (0, 0, 0), size=1400)
    md = SEA.modifiers.new('oc', 'OCEAN'); md.resolution = 9; md.spatial_size = 80; md.wave_scale = 0.8; md.choppiness = 1.1
    md.repeat_x = 9; md.repeat_y = 9
    sea_m = bpy.data.materials.new('sea'); sea_m.use_nodes = True; nt = sea_m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.1
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.45; ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*lin('#1C8CA6'), 1); ramp.color_ramp.elements[1].color = (*lin('#7CC8DA'), 1)
    nt.links.new(lw.outputs['Facing'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    SEA.data.materials.append(sea_m)
    for p in SEA.data.polygons: p.use_smooth = True
    hill = prim('ico_sphere', (0, 32, -4.5), scale=(34, 26, 15), subdivisions=5, radius=1)
    tex = bpy.data.textures.new('cl', 'CLOUDS'); tex.noise_scale = 0.35
    dm = hill.modifiers.new('d', 'DISPLACE'); dm.texture = tex; dm.strength = 0.18; dm.texture_coords = 'LOCAL'
    bpy.context.view_layer.objects.active = hill; bpy.ops.object.modifier_apply(modifier=dm.name)
    hm = bpy.data.materials.new('hill'); hm.use_nodes = True; nt = hm.node_tree; b = nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0.9
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.2; mr.inputs['From Max'].default_value = 2.2
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(geo.outputs['Position'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].color = (*lin('#A0957F'), 1); ramp.color_ramp.elements[1].color = (*lin('#58993F'), 1)
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.65
    nt.links.new(geo.outputs['Position'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], mix.inputs['Factor'])
    nt.links.new(ramp.outputs['Color'], mix.inputs[6]); mix.inputs[7].default_value = (*lin('#4A8436'), 1); mix.inputs['Factor'].default_value = 0.3
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 0.35
    nt.links.new(nz.outputs['Fac'], mm.inputs[0]); nt.links.new(mm.outputs[0], mix.inputs['Factor'])
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    hill.data.materials.append(hm)
    RK = [mat('#A39885', 0.9), mat('#8E8574', 0.9), mat('#B3A994', 0.9)]
    for (x, y, sx, sy, sz) in [(0, 2.5, 4.2, 3.0, 0.7), (-3.6, 3.5, 2.6, 2.4, 0.9), (3.8, 3.2, 2.8, 2.6, 0.8), (-1.5, 5.5, 3, 2.5, 1.2),
                               (2.2, 6.0, 3, 2.4, 1.4), (0.5, 0.2, 2.2, 1.6, 0.45), (-2.8, 0.8, 1.6, 1.4, 0.5), (3.2, 0.6, 1.5, 1.3, 0.5)]:
        prim('ico_sphere', (x, y, 0.0), rot=(0, 0, rnd.uniform(0, 3)), scale=(sx, sy, sz), m=rnd.choice(RK), subdivisions=2, radius=1)
    for _ in range(90):
        a = rnd.uniform(0, 2 * PI); rr = rnd.uniform(0.55, 1.0)
        x = math.cos(a) * 34 * rr * 1.02; y = 32 + math.sin(a) * 26 * rr * 1.02
        if y < 9 and abs(x) < 8: continue
        big = rnd.random() < 0.2
        prim('ico_sphere', (x, y, rnd.uniform(-0.3, 0.3) + (2 if big else 0)), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), 0),
             scale=(rnd.uniform(0.8, 2.5),) * 2 + ((rnd.uniform(3, 6) if big else rnd.uniform(0.5, 1.5)),), m=rnd.choice(RK), subdivisions=1, radius=1)
    bpy.context.view_layer.update()
    return rnd

def ground_z(x, y, start=80.0):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, V(x, y, start), V(0, 0, -1))
    return loc.z if hit else 0.0

def vegetation(rnd, n_trees=55, n_grass=240):
    G = [mat('#5FA33E', 0.8), mat('#4C8F33', 0.8), mat('#78B84A', 0.8)]
    T = mat('#6B4A2B', 0.9); F = [mat('#2F6E2B', 0.8), mat('#3B7F31', 0.8), mat('#468C38', 0.8)]
    FL = [mat('#F2D04B', 0.6), mat('#E8577A', 0.6), mat('#FFFFFF', 0.6)]
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
        if rnd.random() < 0.15:
            prim('uv_sphere', (0, 0, 0.5), m=rnd.choice(FL), parent=e, segments=8, ring_count=6, radius=0.06)
        tufts.append(e)
    for _ in range(26):
        x = rnd.uniform(-8, 8); y = rnd.uniform(6, 16); z = ground_z(x, y)
        if z < 0.3 or (abs(x) < 3 and y < 8): continue
        prim('ico_sphere', (x, y, z + 0.4), scale=(1, 1, 0.75), m=rnd.choice(F), subdivisions=2, radius=rnd.uniform(0.5, 0.9))
    for _ in range(n_trees):
        a = rnd.uniform(0, 2 * PI); rr = rnd.uniform(0.15, 0.8)
        x = math.cos(a) * 30 * rr; y = 32 + math.sin(a) * 22 * rr
        if y < 12 and abs(x) < 6: continue
        if abs(x) < 4 and abs(y - 32) < 4: continue
        z = ground_z(x, y); h = rnd.uniform(2.5, 4.5)
        prim('cylinder', (x, y, z + h / 2), m=T, vertices=6, radius=0.16, depth=h)
        for k in range(3):
            prim('ico_sphere', (x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6), z + h + rnd.uniform(-0.3, 0.6)), m=rnd.choice(F),
                 subdivisions=1, radius=rnd.uniform(1.0, 1.6))
    for (x, y) in [(-6.5, 8.0), (6.8, 9.5), (-9.5, 12), (9.5, 14), (-4.5, 13), (12, 7)]:
        z = ground_z(x, y)
        if z > 0.1: palm(x, y, z, rnd.uniform(4.5, 6.5), rnd)
    warning_sign(-2.6, 3.0, ground_z(-2.6, 3.0))
    ruin_wall(4.6, 9.2, ground_z(5.5, 9.2) - 0.1, rnd)
    return tufts

LIGHTHOUSE = V(0, 32, 0)
def lighthouse():
    z = ground_z(0, 32); LIGHTHOUSE.z = z
    W = mat('#F4F1EA', 0.6); R = mat('#C8352B', 0.6); K = mat('#2A2A2A', 0.5)
    prim('cylinder', (0, 32, z + 0.3), m=mat('#B8AE9C', 0.9), vertices=16, radius=1.8, depth=0.6)
    for i in range(5):
        prim('cylinder', (0, 32, z + 0.9 + i * 1.6), m=R if i % 2 else W, vertices=20, radius=1.25 - i * 0.12, depth=1.6)
    prim('cylinder', (0, 32, z + 8.3), m=K, vertices=20, radius=1.15, depth=0.12)
    prim('torus', (0, 32, z + 8.95), m=K, major_radius=1.1, minor_radius=0.035, major_segments=24, minor_segments=4)
    for k in range(16):
        a = k / 16 * 2 * PI; prim('cylinder', (math.cos(a) * 1.1, 32 + math.sin(a) * 1.1, z + 8.65), m=K, vertices=4, radius=0.025, depth=0.6)
    prim('cylinder', (0, 32, z + 8.9), m=mat('#FFE89A', 0.2, emit=4.0), vertices=12, radius=0.75, depth=1.0)
    prim('cone', (0, 32, z + 9.9), m=R, vertices=16, radius1=0.95, depth=1.0)
    prim('uv_sphere', (0, 32, z + 10.45), m=K, segments=8, ring_count=6, radius=0.15)
    for k in range(3):
        prim('cube', (0, 30.9 + 0.12 * k, z + 2.6 + k * 1.6), scale=(0.3, 0.1, 0.5), m=mat('#30485E', 0.2), size=1)
    beam = empty((0, 32, z + 8.9))
    prim('cone', (0, 3.5, 0), rot=(PI / 2, 0, 0), m=mat('#FFF3C4', 1.0, emit=1.5, alpha=0.1), parent=beam, vertices=16, radius1=0.9, radius2=0.2, depth=7)
    prim('cube', (0, 30.72, z + 0.95), scale=(0.75, 0.1, 1.4), m=mat('#5A3B22', 0.8), size=1)
    return beam

def loft(sections, m):
    bm = bmesh.new(); rings = []
    for y, pts in sections: rings.append([bm.verts.new((x, y, z)) for x, z in pts])
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('l'); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new('l', me)); me.materials.append(m)
    return o

def hull_sections(L, Wd, D, n=9, sheer=0.35):
    secs = []
    for i in range(n):
        u = i / (n - 1); y = (u - 0.5) * L
        w = Wd * (1 - max(0, (u - 0.6) / 0.4) ** 1.6 * 0.97)
        top = 0.0 + sheer * max(0, (u - 0.5) / 0.5) ** 2
        d = D * (1 - 0.4 * max(0, (u - 0.7) / 0.3))
        secs.append((y, [(-w, top), (-w * 0.95, top - d * 0.5), (-w * 0.55, top - d), (w * 0.55, top - d), (w * 0.95, top - d * 0.5), (w, top)]))
    return secs

def boat(x, y):
    root = empty((x, y, 0))
    H = mat('#F4F4F2', 0.5, key='hullw'); BL = mat('#1E5FA8', 0.5, key='hullb'); WD = mat('#B98A55', 0.8, key='deck')
    h = loft(hull_sections(7.0, 1.35, 1.2, sheer=0.5), H); h.parent = root; h.location = (0, 0, 1.0); outlined(h, 1.02)
    s = loft(hull_sections(7.02, 1.37, 0.25, sheer=0.5), BL); s.parent = root; s.location = (0, 0, 0.12)
    prim('cube', (0, -0.3, 0.98), scale=(2.5, 6.3, 0.06), m=WD, parent=root, size=1)
    cab = prim('cube', (0, -1.6, 1.85), scale=(1.8, 1.9, 1.7), m=H, parent=root, size=1); outlined(cab, 1.02)
    prim('cube', (0, -1.6, 2.75), scale=(2.1, 2.2, 0.1), m=BL, parent=root, size=1)
    for sx in (-0.91, 0.91):
        prim('cube', (sx, -1.6, 2.0), scale=(0.02, 1.3, 0.6), m=mat('#7FC7EA', 0.1, key='glassb'), parent=root, size=1)
    prim('cube', (0, -0.64, 2.0), scale=(1.4, 0.02, 0.6), m=mat('#7FC7EA', 0.1, key='glassb'), parent=root, size=1)
    RL = mat('#DADADA', 0.3, key='rail')
    for side in (-1, 1):
        for k in range(8):
            prim('cylinder', (side * 1.22, -3.0 + k * 0.8, 1.35), m=RL, parent=root, vertices=6, radius=0.03, depth=0.7)
        prim('cylinder', (side * 1.22, -0.2, 1.7), rot=(PI / 2, 0, 0), m=RL, parent=root, vertices=6, radius=0.03, depth=5.6)
        for k in range(3):
            prim('cylinder', (side * 1.38, -2.0 + k * 1.5, 0.6), rot=(0, PI / 2, 0), m=mat('#222222', 0.7, key='tire'), parent=root, vertices=12, radius=0.2, depth=0.15)
    lb = prim('torus', (0.92, -0.6, 2.1), rot=(0, PI / 2, 0), m=mat('#F36A2A', 0.5, key='buoy'), parent=root, major_radius=0.3, minor_radius=0.08, major_segments=16, minor_segments=8)
    prim('cylinder', (0, -2.2, 3.6), m=RL, parent=root, vertices=6, radius=0.03, depth=1.6)
    prim('plane', (0.35, -2.2, 4.1), rot=(PI / 2, 0, 0), scale=(0.35, 0.25, 1), m=flag_mat_plane('bra'), parent=root, size=1)
    return root

def navy_ship(x, y):
    root = empty((x, y, 0))
    G = mat('#7C8794', 0.6, key='navyg'); D = mat('#5C6672', 0.6, key='navyd'); K = mat('#2A3440', 0.2, key='navyk')
    h = loft(hull_sections(26, 3.2, 2.6, n=11, sheer=1.2), G); h.parent = root; h.location = (0, 0, 2.4); h.rotation_euler.z = -PI / 2; outlined(h, 1.01)
    s = loft(hull_sections(26.05, 3.22, 0.5, n=11, sheer=1.2), mat('#9B2D2A', 0.6, key='navyr')); s.parent = root; s.location = (0, 0, 0.3); s.rotation_euler.z = -PI / 2
    prim('cube', (0, 0, 2.45), scale=(22, 5.6, 0.1), m=D, parent=root, size=1)
    sup = prim('cube', (-2.5, 0, 4.0), scale=(7, 4.6, 3.0), m=G, parent=root, size=1); outlined(sup, 1.01)
    prim('cube', (-2.0, 0, 6.2), scale=(4, 3.8, 1.6), m=G, parent=root, size=1)
    prim('cube', (-0.05, 0, 6.3), scale=(0.05, 3.4, 0.5), m=K, parent=root, size=1)
    for k in range(5): prim('cube', (-6.0 + k * 1.4, -2.31, 4.4), scale=(0.6, 0.02, 0.4), m=K, parent=root, size=1)
    prim('cylinder', (-2.4, 0, 8.8), m=D, parent=root, vertices=8, radius=0.12, depth=4)
    rad = empty((-2.4, 0, 10.2), root)
    prim('cube', (0, 0, 0), scale=(1.6, 0.2, 0.3), m=D, parent=rad, size=1)
    prim('cube', (5.5, 0, 3.2), scale=(1.6, 1.6, 0.8), m=G, parent=root, size=1)
    prim('cylinder', (6.8, 0, 3.3), rot=(0, PI / 2, 0), m=D, parent=root, vertices=8, radius=0.1, depth=2.2)
    for k in range(2):
        prim('uv_sphere', (-4.0 + k * 3, 2.6, 3.6), scale=(1.4, 0.5, 0.45), m=mat('#F36A2A', 0.5, key='lifeb'), parent=root, segments=12, ring_count=8, radius=1)
    fl = prim('plane', (-12.2, 0.0, 5.0), rot=(PI / 2, 0, 0), scale=(1.2, 0.8, 1), m=flag_mat_plane('bra'), parent=root, size=1)
    prim('cylinder', (-12.9, 0, 4.0), m=D, parent=root, vertices=6, radius=0.05, depth=3.0)
    return root, fl, rad

def sea_time(t): SEA.modifiers['oc'].time = 2.0 + t * 0.9

def common(boat_xy=(2, -18)):
    rnd = build_world(); tufts = vegetation(rnd); beam = lighthouse(); puffy_clouds(rnd); mainland_town(rnd)
    bt = boat(*boat_xy)
    tourist = Person(TOURIST); captain = Person(CAPTAIN); girl = Person(GIRL)
    for p in (tourist, captain, girl): p.root.location = V(0, -400, -80)
    return rnd, tufts, beam, bt, tourist, captain, girl

def on_boat(bt, p, slot, **kw):
    off = [V(-0.55, 0.9, 1.0), V(0.55, 1.7, 1.0), V(-0.3, 2.5, 1.0)][slot]
    kw.setdefault('yaw', 0.5)
    yaw = kw.pop('yaw')
    p.pose(pos=bt.matrix_world @ off if False else bt.location + off, yaw=yaw, **kw)

def boat_motion(bt, t, y=None, x=None):
    if x is not None: bt.location.x = x
    if y is not None: bt.location.y = y
    bt.location.z = 0.12 * math.sin(t * 1.8); bt.rotation_euler = (0.025 * math.sin(t * 1.5), 0.035 * math.sin(t * 1.2), 0)

def snakes_field(rnd, n, region, coils=0.4):
    out = []
    for i in range(n):
        x = rnd.uniform(region[0], region[1]); y = rnd.uniform(region[2], region[3]); z = ground_z(x, y)
        s = Snake(L=rnd.uniform(1.1, 1.6)); kind = 'coil' if rnd.random() < coils else 'slither'
        out.append((s, V(x, y, z), kind, rnd.uniform(0, 2 * PI), rnd.uniform(0, 6)))
    return out

def update_snakes(field, t, raise_k=1.0):
    for i, (s, base, kind, ang, ph) in enumerate(field):
        if kind == 'coil': pts = path_coil(base, t, phase=ph, look=ang, raise_head=0.35 * raise_k)
        else: pts = path_slither(base, ang, s.L, t, speed=0.12, phase=ph, raise_head=0.25 * raise_k)
        s.set(pts, tongue=1.0 if math.sin(t * 5 + ph * 3) > 0.6 else 0.0)

def hidden_snake():
    return Snake(L=1.3), V(0.9, 3.9, ground_z(0.9, 3.9) - 0.05)

LAND = None
def land():
    return V(0.4, 1.3, ground_z(0.4, 1.3))

def tourist_idle(p, pos, t, yaw=0.0, **kw):
    kw.setdefault('look', (0.0, 0.0))
    p.pose(pos=pos, yaw=yaw, **kw)

# ------------------------------------------------------------------ TOMAS
def A1():
    rnd, tufts, beam, bt, tourist, captain, girl = common((1.5, -18))
    hs, hb = hidden_snake(); cam, tgt = make_cam(28)
    def anim(t):
        sea_time(t); beam.rotation_euler.z = t * 1.2
        boat_motion(bt, t, y=-18 + t * 0.5)
        # GANCHO: la serpiente escondida salta hacia la cámara (0.45-0.7 s) y vuelve
        camp = V(-1.2, -0.6, 2.0)
        lunge = sm((t - 0.45) / 0.22) * (1 - sm((t - 1.1) / 0.6))
        pts = path_coil(hb, t, raise_head=0.1 + 0.3 * sm((t - 0.3) / 0.15), phase=1.0, look=-1.9)
        dirc = (camp - hb); dirc.z *= 0.15; dirc = dirc.normalized()
        pts = [q + dirc * (0.75 * lunge * sm((i / (Snake.N - 1) - 0.5) / 0.5)) + V(0, 0, 0.12 * lunge * sm((i / (Snake.N - 1) - 0.6) / 0.4)) for i, q in enumerate(pts)]
        hs.set(pts, tongue=1.0 if 0.3 < t < 1.0 else 0.0)
        for k, tf in enumerate(tufts[:40]): tf.rotation_euler = (0.08 * math.sin(t * 3 + k), 0, 0)
        on_boat(bt, captain, 0, armR=(-0.5, 0.3, 0, -1.4), look=(0, 0.3), wide=sm((t - 4.0) / 0.3), browup=sm((t - 4.0) / 0.3))
        on_boat(bt, girl, 1, look=(0, 0.5))
        on_boat(bt, tourist, 2, squint=0.5, smile=1.0, armL=(-1.2, -0.2, 0, -1.4))
        if t < 0.9:
            rush = sm((t - 0.4) / 0.28)
            head = pts[-1]
            near = head + dirc * (0.55 - 0.25 * lunge) + V(0, 0, 0.06)
            p = V(-1.2, -0.6, 2.0).lerp(near, rush) + shake(t, 0.62, 0.3, 0.03); g = V(0.9, 4.1, 0.6).lerp(head, rush)
        elif t < 2.6:
            u = eo((t - 0.9) / 1.7); p = V(-1.15, -0.7, 2.0).lerp(V(-6, -46, 22), u); g = V(0.9, 4.1, 0.6).lerp(V(0, 22, 4), u)
        else:
            u = sm((t - 2.6) / 3.3); p = V(-6, -46, 22).lerp(V(6.5, -24, 3.2), u); g = V(0, 22, 4).lerp(V(1.5, -14, 2.2), u)
        cam.location = p; tgt.location = g
    return anim

def A5():
    rnd, tufts, beam, bt, tourist, captain, girl = common((1.5, -18))
    hs, hb = hidden_snake(); cam, tgt = make_cam(28)
    def anim(t):
        sea_time(t + 40)
        for k, tf in enumerate(tufts[:40]): tf.rotation_euler = (0.08 * math.sin(t * 3 + k), 0, 0)
        r = sm((t - 2.6) / 0.6)
        hs.set(path_coil(hb, t, raise_head=0.1 + 0.3 * r, phase=1.0, look=-1.9 + 0.3 * r), tongue=1.0 if (t > 3.2 and math.sin(t * 9) > 0) else 0.0)
        u = sm(t / 4.0)
        cam.location = V(-1.2, -0.6, 2.0).lerp(V(0.35, 3.0, 0.9), u); tgt.location = V(0.9, 4.1, 0.6).lerp(V(0.75, 3.75, 0.55), u)
    return anim

def A2():
    rnd, tufts, beam, bt, tourist, captain, girl = common((3, -24))
    ship, fl, rad = navy_ship(17, -12); officer = Person(NAVY)
    cam, tgt = make_cam(30)
    def anim(t):
        sea_time(t + 6); beam.rotation_euler.z = t * 1.2
        ship.location = V(17 - t * 4.0, -12, 0.1 * math.sin(t)); ship.rotation_euler = (0, 0.015 * math.sin(t * 0.8), 0)
        fl.scale.y = 0.8 + 0.05 * math.sin(t * 8); rad.rotation_euler.z = t * 3
        wave = math.sin(t * 9)
        officer.pose(pos=ship.location + V(3.0, -1.6, 2.5), yaw=0.2, armR=(-0.2, 2.6 + 0.3 * wave, 0, -0.2), armL=(-0.2, -2.6 - 0.3 * wave, 0, -0.2),
                     mouth=0.8, browup=0.6, wide=0.5)
        boat_motion(bt, t, y=-24)
        on_boat(bt, captain, 0, yaw=0.9, worry=sm((t - 1.5) / 0.4), look=(-0.6, 0.2), armR=(-0.3, 0.2, 0, -0.8))
        on_boat(bt, girl, 1, yaw=0.9, look=(-0.6, 0.2))
        on_boat(bt, tourist, 2, yaw=0.9, squint=0.6, smile=1.0, armL=(-0.3, -1.2, 0, -1.6), armR=(-0.3, 1.2, 0, -1.6))
        cam.location = V(9.0, -31.5, 3.0) + V(-t * 0.25, 0, 0); tgt.location = V(2.5, -15, 2.8)
    return anim

def A3():
    rnd, tufts, beam, bt, tourist, captain, girl = common((0.6, -5.0))
    cam, tgt = make_cam(28); L = land()
    def anim(t):
        sea_time(t + 12); boat_motion(bt, t, y=-5.0)
        on_boat(bt, captain, 0, yaw=0.6, worry=1, armR=(-1.4, 0.2, 0, -0.2), look=(0.4, 0.3), mouth=0.5)
        on_boat(bt, girl, 1, yaw=0.6, wide=1, look=(0.4, 0.4), mouth=0.4)
        start = bt.location + V(0.3, 3.1, 1.0)
        if t < 0.8:
            c = sm(t / 0.8)
            tourist.pose(pos=start, yaw=-0.6, crouch=0.5 * c, armL=(0.6 * c, -0.1, 0, -0.3), armR=(0.6 * c, 0.1, 0, -0.3), squint=0.6, smile=1)
        elif t < 1.7:
            u = (t - 0.8) / 0.9; p = start.lerp(L, u); p.z += 2.2 * math.sin(u * PI)
            tourist.pose(pos=p, yaw=-0.6, crouch=0.3 * math.sin(u * PI), armL=(-2.6, -0.3, 0, -0.2), armR=(-2.6, 0.3, 0, -0.2), squint=0.6, smile=1, mouth=0.3)
        else:
            u = t - 1.7; c = 0.5 * math.exp(-u * 5)
            tourist.pose(pos=L, yaw=-0.6 * (1 - sm((t - 2.1) / 0.5)), crouch=c, armL=(-0.3, -1.3, 0, -1.6), armR=(-0.3, 1.3, 0, -1.6), squint=0.6, smile=1)
        cam.location = V(7.0, -3.0, 2.6) + V(-0.3 * t, 0.1 * t, 0); tgt.location = V(0.5, -0.5, 1.4)
    return anim

def B1():
    rnd, tufts, beam, bt, tourist, captain, girl = common((0.6, -8))
    cam, tgt = make_cam(30); L = land()
    sn = Snake(L=1.6); base = V(-1.6, 3.6, ground_z(-1.6, 3.6))
    near = sorted(tufts, key=lambda e: (e.location - L).length)[:8]
    def anim(t):
        sea_time(t + 16)
        f = sm((t - 1.2) / 0.3)
        tourist.pose(pos=L, yaw=0.0, squint=0.6 * (1 - f), smile=1 - f, wide=f, look=(-0.9 * f, 0), turn=-0.5 * f, mouth=0.3 * f,
                     armL=(-0.3, -1.3 * (1 - f), 0, -1.6 * (1 - f)), armR=(-0.3, 1.3 * (1 - f), 0, -1.6 * (1 - f)))
        for k, tf in enumerate(near): tf.rotation_euler = (0.35 * math.sin(t * 14 + k) * sm((t - 0.4) / 0.3), 0.2 * math.sin(t * 11 + k), 0)
        sn.set(path_slither(base, 0.1, 1.6, t, speed=0.35, z=base.z - 0.06), tongue=0.0)
        u = sm(t / 3.6)
        cam.location = V(1.8, -3.6, 1.9).lerp(V(1.0, -1.7, 1.75), u); tgt.location = V(0.1, 2.0, 1.2).lerp(V(0.3, 1.6, 1.5), u)
    return anim

def B2():
    rnd, tufts, beam, bt, tourist, captain, girl = common((0.6, -8))
    cam, tgt = make_cam(28); L = land()
    pops = [(-1.0, 2.6, 0.2, -0.6), (1.7, 2.9, 0.8, -2.4), (-0.2, 3.6, 1.4, -1.6)]
    sns = [Snake(L=1.3) for _ in pops]
    def anim(t):
        sea_time(t + 20)
        lk = [p for p in pops if t >= p[2]]
        lx = (-0.8 if lk and lk[-1][0] < 0 else 0.8) if lk else 0
        tourist.pose(pos=L, yaw=0.0, wide=1, look=(lx, -0.3), mouth=0.6, worry=1, crouch=0.15, turn=-0.3 * lx,
                     armL=(-0.6, -0.4, 0, -1.4), armR=(-0.6, 0.4, 0, -1.4))
        for s, (x, y, t0, look) in zip(sns, pops):
            r = eo((t - t0) / 0.25) if t >= t0 else 0.0
            s.set(path_coil(V(x, y, ground_z(x, y) - 0.25 * (1 - r)), t, raise_head=0.45 * r, phase=x, look=look), tongue=1.0 if (t - t0) > 0.3 and math.sin(t * 10) > 0 else 0.0)
            s.curve.hide_render = r <= 0
            for ch in s.head.children_recursive: ch.hide_render = r <= 0
        punch = sum(max(0.0, 1 - abs(t - p[2] - 0.1) * 6) for p in pops)
        cam.location = V(0.4, -3.4, 2.2).lerp(V(0.4, 1.6, 1.5), 0.12 * punch); tgt.location = V(0.4, 1.8, 1.2)
    return anim

def B3():
    rnd, tufts, beam, bt, tourist, captain, girl = common((0.6, -8))
    cam, tgt = make_cam(28); L = land()
    field = [f for f in snakes_field(random.Random(9), 36, (-7, 7, 0.0, 9.0)) if (f[1] - L).length > 1.0]
    def anim(t):
        sea_time(t + 24)
        tourist.pose(pos=L, yaw=0.0, wide=1, worry=1, mouth=0.8, look=(0.9 * math.sin(t * 2.5), 0), crouch=0.2 + 0.03 * math.sin(t * 30),
                     armL=(-2.4, -0.4, 0, -0.3), armR=(-2.4, 0.4, 0, -0.3))
        update_snakes(field, t)
        u = sm(t / 4.1)
        cam.location = V(0.4, -2.2, 1.8).lerp(V(0.0, -10.5, 9.0), u); tgt.location = V(0.4, 1.5, 1.3).lerp(V(0.0, 4.5, 0.5), u)
    return anim

def B4():
    rnd, tufts, beam, bt, tourist, captain, girl = common((0.6, -8))
    cam, tgt = make_cam(35); L = land()
    sn = Snake(L=1.6); base = V(-0.6, 3.0, ground_z(-0.6, 3.0))
    def anim(t):
        sea_time(t + 30)
        sn.set(path_coil(base, t, raise_head=0.45, phase=0.5, look=-1.3 + 0.15 * math.sin(t * 0.8)), tongue=1.0 if math.sin(t * 6) > 0.2 else 0.0)
        tourist.pose(pos=L, yaw=0.5, wide=1, worry=1, mouth=0.5 + 0.2 * math.sin(t * 12), look=(-0.7, 0.3), crouch=0.15,
                     armL=(-0.9, -0.2, 0, -1.9), armR=(-0.9, 0.2, 0, -1.9))
        bpy.context.view_layer.update(); hp = sn.head.matrix_world.translation.copy()
        if t < 5.0:
            a = -0.4 - 0.5 * sm(t / 5.0)
            cam.location = hp + V(math.cos(a) * 0.75, math.sin(a) * 0.75, 0.12 + 0.05 * math.sin(t)); tgt.location = hp + V(0, 0, -0.05)
        else:
            u = sm((t - 5.0) / 1.2)
            face = L + V(0, 0, 1.65)
            cam.location = (hp + V(math.cos(-0.9) * 0.75, math.sin(-0.9) * 0.75, 0.12)).lerp(face + V(1.3, -2.6, 0.1), u)
            tgt.location = hp.lerp(face, u)
    return anim

def C1():
    rnd, tufts, beam, bt, tourist, captain, girl = common((3, -24))
    cam, tgt = make_cam(30)
    def anim(t):
        sea_time(t + 36); beam.rotation_euler.z = t * 1.2; boat_motion(bt, t, y=-24)
        th = sm((t - 0.8) / 0.4)
        on_boat(bt, captain, 0, yaw=1.0, worry=1, look=(0, 0.3))
        on_boat(bt, girl, 1, yaw=1.1, squint=0.4 * th, look=(0.6 * th, 0.8 * th), nod=-0.15 * th, tilt=0.12 * th,
                armR=(-1.3 * th, 0.25 * th, 0, -2.3 * th), mouth=0.0, worry=-0.3 * th)
        mp = bt.location + V(0.55, 1.7, 2.6)
        u = sm(t / 4.6)
        cam.location = (mp + V(3.6, -1.6, 0.4)).lerp(mp + V(1.8, -0.8, 0.0), u); tgt.location = mp + V(-0.2, 0, -0.2)
    return anim

def C2():
    rnd, tufts, beam, bt, tourist, captain, girl = common((3, -24))
    cam, tgt = make_cam(30)
    def anim(t):
        sea_time(t + 60); beam.rotation_euler.z = t * 1.2; boat_motion(bt, t, y=-24)
        lc = sm((t - 1.6) / 0.4)
        on_boat(bt, captain, 0, yaw=3.9 - 1.35 * lc, worry=1, look=(0, 0))
        on_boat(bt, girl, 1, yaw=3.8 - 1.32 * lc, wide=lc, browup=lc, look=(0, 0))
        on_boat(bt, tourist, 2, yaw=3.7 - 1.3 * lc, glasses=0.0, wide=1, worry=1, mouth=0.4, crouch=0.1 + 0.03 * math.sin(t * 30),
                armL=(-0.5, -0.3, 0, -1.6), armR=(-0.5, 0.3, 0, -1.6))
        mp = bt.location + V(0.0, 1.7, 2.0)
        u = sm(t / 4.0)
        cam.location = (mp + V(5.0, 6.5, 1.2)).lerp(mp + V(2.4, 3.2, 0.5), u); tgt.location = mp
    return anim

def branch_set(gz):
    T = mat('#6B4A2B', 0.9)
    prim('cylinder', (3.4, 6, gz + 1.4), m=T, vertices=8, radius=0.2, depth=2.8)
    prim('cylinder', (4.6, 6, gz + 2.3), rot=(0, PI / 2, 0), m=T, vertices=8, radius=0.09, depth=2.6)
    prim('cylinder', (7.6, 6, gz + 1.25), m=T, vertices=6, radius=0.1, depth=2.5)
    for k in range(3): prim('ico_sphere', (3.2 + k * 0.4, 6.3, gz + 3.2), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=1.0)

def B5():
    rnd, tufts, beam, bt, tourist, captain, girl = common((3, -24))
    gz = ground_z(4.5, 6); branch_set(gz)
    sn = Snake(L=1.6); bird = Bird(1.0); cam, tgt = make_cam(32)
    def anim(t):
        sea_time(t + 41)
        ext = sm((t - 2.4) / 1.0); pts = []
        for i in range(Snake.N):
            u = i / (Snake.N - 1)
            pts.append(V(3.7 + u * 1.55 + 0.06 * math.sin(u * 9 + t * 2) * (1 - u), 6 + 0.06 * math.sin(u * 12 + t * 1.5),
                         gz + 2.39 + 0.25 * ext * sm((u - 0.8) / 0.2)))
        sn.set(pts, tongue=1.0 if math.sin(t * 7) > 0.3 else 0.0)
        if t < 2.0:
            u = sm(t / 2.0); bird.set(V(14, 2, gz + 6).lerp(V(7.6, 6, gz + 2.62), u), yaw=PI / 2 + 0.3, flap=t * 22, pitch=-0.2 * (1 - u))
        else: bird.set(V(7.6, 6, gz + 2.62), yaw=PI / 2, fold=1.0, pitch=0.05 * math.sin(t * 3))
        u = sm(t / 5.2)
        cam.location = V(5.6, 1.5, gz + 2.6).lerp(V(5.4, 3.2, gz + 2.5), u); tgt.location = V(6.1, 6, gz + 2.4)
    return anim

def B6():
    rnd, tufts, beam, bt, tourist, captain, girl = common((3, -24))
    gz = ground_z(4.5, 6); branch_set(gz)
    sn = Snake(L=1.6); bird = Bird(1.0); cam, tgt = make_cam(32)
    def anim(t):
        sea_time(t + 47)
        l1 = sm((t - 0.6) / 0.18) * (1 - sm((t - 1.2) / 0.5)); l2 = sm((t - 5.3) / 0.15); pts = []
        for i in range(Snake.N):
            u = i / (Snake.N - 1)
            pts.append(V(3.7 + u * 1.55 + l1 * 1.6 * sm((u - 0.55) / 0.45) + 0.04 * math.sin(u * 9 + t * 2),
                         6 - l2 * 1.2 * sm((u - 0.6) / 0.4),
                         gz + 2.39 + 0.25 * sm((u - 0.8) / 0.2) + l1 * 0.25 * sm((u - 0.7) / 0.3) + l2 * 0.15 * sm((u - 0.7) / 0.3)))
        sn.set(pts, tongue=1.0 if (t > 3.6 and math.sin(t * 8) > 0) else 0.0)
        if t < 0.75: bird.set(V(7.6, 6, gz + 2.62), yaw=PI / 2, fold=1.0)
        else:
            u = t - 0.75
            bird.set(V(7.6 + u * 4.0, 6 + u * 9.0, gz + 2.62 + u * 2.2 - max(0.0, u - 2.2) ** 2 * 0.6), yaw=-0.45, flap=u * 24, pitch=-0.2)
        if t < 0.9:
            cam.location = V(5.6, 2.6, gz + 2.55) + shake(t, 0.62, 0.3, 0.08); tgt.location = V(6.4, 6, gz + 2.5)
        elif t < 3.6:
            u = sm((t - 0.9) / 2.7); bpy.context.view_layer.update()
            cam.location = V(5.6, 2.6, gz + 2.55).lerp(V(6.0, 2.0, gz + 3.2), u); tgt.location = bird.root.matrix_world.translation.copy()
        else:
            u = sm((t - 3.6) / 1.4)
            cam.location = V(5.0, 4.2, gz + 2.7).lerp(V(5.15, 4.9, gz + 2.68), u) + shake(t, 5.3, 0.4, 0.05); tgt.location = V(5.2, 6, gz + 2.65)
    return anim

def A4():
    rnd, tufts, beam, bt, tourist, captain, girl = common((3, -24))
    z = LIGHTHOUSE.z
    field = [(Snake(L=1.3), V(x, y, ground_z(x, y)), 'coil', -PI / 2, k * 2.0) for k, (x, y) in enumerate([(1.2, 29.6), (-1.5, 30.0), (2.0, 31.0)])]
    birds = [Bird(0.8) for _ in range(3)]
    cam, tgt = make_cam(28)
    def anim(t):
        sea_time(t + 53); beam.rotation_euler.z = t * 1.4
        update_snakes(field, t)
        for i, b in enumerate(birds):
            a = t * 0.5 + i * 2.1; b.set(V(math.cos(a) * 8, 32 + math.sin(a) * 8, z + 12 + i), yaw=a + PI, flap=t * 14 + i)
        a = -1.9 + t * 0.12
        cam.location = V(math.cos(a) * 13, 32 + math.sin(a) * 13, z + 10 + t * 0.4); tgt.location = V(0, 32, z + 6 + t * 0.3)
    return anim

def D1():
    setup(world='#A6DBFF', strength=0.9, sun_rot=(50, 0, 30), resx=RESX)
    rnd = random.Random(3)
    prim('cube', (0, 0, -1.6), scale=(20, 9, 2.0), m=mat('#6B4F35', 0.9), size=1)
    prim('cube', (-6.5, 0, -0.05), scale=(7, 8.6, 1.1), m=mat('#C9B58A', 0.9), size=1)
    prim('cube', (-6.5, 0, 0.55), scale=(7, 8.6, 0.12), m=mat('#5E9A48', 0.9), size=1)
    for i in range(14):
        prim('ico_sphere', (rnd.uniform(-9.5, -3.5), rnd.uniform(-3.8, 3.8), 0.9), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=rnd.uniform(0.35, 0.6))
    for i in range(6):
        x = rnd.uniform(-9, -5); y = rnd.uniform(-3, 3)
        prim('cube', (x, y, 0.95), scale=(0.5, 0.5, 0.7), m=building_mat('#F3EBDD'), size=1)
    prim('cube', (-1.0, 0, -0.45), scale=(6.5, 2.6, 0.6), m=mat('#D9C79C', 0.9), size=1)
    prim('ico_sphere', (4.2, 0, -0.2), scale=(2.6, 2.1, 1.9), m=mat('#4E8C3A', 0.9), subdivisions=2, radius=1)
    for i in range(6):
        prim('ico_sphere', (4.2 + rnd.uniform(-1.4, 1.4), rnd.uniform(-1.0, 1.0), 1.2 + rnd.uniform(0, 0.5)), m=mat('#2F6E2B', 0.8), subdivisions=1, radius=0.4)
    for i in range(14):
        a = rnd.uniform(0, 2 * PI); r = rnd.uniform(0.5, 1.8)
        prim('uv_sphere', (4.2 + math.cos(a) * r * 1.1, math.sin(a) * r * 0.85, 1.0), scale=(0.18, 0.05, 0.05), rot=(0, 0, a), m=snake_mat(), segments=8, ring_count=6, radius=1)
    water = prim('cube', (0, 0, -1.6), scale=(19.9, 8.9, 1.0), m=mat('#2A9BC4', 0.1, alpha=0.78), size=1)
    cam, tgt = make_cam(30)
    def anim(t):
        lvl = lerp(-0.95, 0.35, sm((t - 1.0) / 2.6))
        water.scale.z = lvl + 2.6; water.location.z = (-2.6 + lvl) / 2
        a = -1.25 + 0.12 * t
        cam.location = V(math.cos(a) * 15, math.sin(a) * 15, 9.5 - 0.3 * t); tgt.location = V(0.5, 0, -0.2)
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
