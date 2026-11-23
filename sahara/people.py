# Personita estilo 2D POV (cabeza blanca, ojos con pupila, contorno) — compartida por todos los videos.
import math, bpy
from lib3d import *
PI = math.pi

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
        elif h == 'safari':
            outlined(prim('cylinder', (0, 0, 0.33), m=mat('#D8C49A', 0.8, key='saf'), parent=s.head, vertices=20, radius=0.31, depth=0.2), 1.05)
            prim('uv_sphere', (0, 0, 0.43), scale=(1, 1, 0.35), m=mat('#D8C49A', 0.8, key='saf'), parent=s.head, segments=16, ring_count=8, radius=0.31)
            prim('cylinder', (0, 0, 0.23), m=mat('#CDB88C', 0.8, key='safb'), parent=s.head, vertices=24, radius=0.52, depth=0.03)
            prim('cylinder', (0, 0, 0.27), m=mat('#6B4A2B', 0.7, key='safband'), parent=s.head, vertices=20, radius=0.315, depth=0.05)
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

