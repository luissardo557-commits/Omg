# Versión 2 de la voz: gancho nuevo (pregunta) + resto de la narración, pausas recortadas y un poco más rápida.
# Uso: python3 voz_v2.py <carpeta_scratch>   (lee hookA.wav, voz.wav, words.json; escribe voz_v2.wav, words_v2.json, map_v2.json)
import sys, os, json, subprocess
import numpy as np, soundfile as sf

D = sys.argv[1]; SR = 44100
SPEED = 1.1; MAXP = 0.20; MINP = 0.26      # pausas > MINP s se dejan en MAXP s
HOOK_A, HOOK_B = 0.10, 12.70               # parte útil del gancho
REST = 8.45                                # la narración vieja sigue desde "¿Quieres hielo..."
GAP = 0.30
HOOK_WORDS = [[0.0, 0.64, '¿Sabes'], [0.64, 1.0, 'cómo'], [1.0, 1.46, 'tenían'], [1.46, 1.94, 'hielo'], [1.94, 2.06, 'en'],
              [2.06, 2.6, 'pleno'], [2.6, 3.24, 'desierto'], [3.24, 3.86, 'hace'], [3.86, 4.2, 'más'], [4.2, 4.4, 'de'],
              [4.4, 4.94, '2.000'], [4.94, 5.36, 'años,'], [5.88, 6.14, 'sin'], [6.14, 6.98, 'electricidad,'], [6.98, 7.42, 'a'],
              [7.42, 8.14, '45'], [8.14, 9.32, 'grados...'], [9.32, 9.48, 'y'], [9.48, 9.66, 'con'], [9.66, 9.76, 'un'],
              [9.76, 10.3, 'ingrediente'], [10.3, 10.88, 'secreto'], [10.88, 11.06, 'que'], [11.06, 11.78, 'jamás'], [11.78, 12.54, 'adivinarías?']]
OLD_CUTS = [('A1', 8.5), ('A2', 13.8), ('A3', 17.7), ('A4', 22.4), ('A5', 28.3), ('A6', 33.3), ('A7', 40.9),
            ('A8', 49.2), ('A9', 59.8), ('A10', 63.3), ('A11', 72.9)]

def mono(p):
    a, sr = sf.read(p)
    if a.ndim > 1: a = a.mean(1)
    if sr != SR: raise SystemExit(f'{p}: sr {sr}')
    return a
h = mono(os.path.join(D, 'hookA.wav'))[int(HOOK_A * SR):int(HOOK_B * SR)]
v = mono(os.path.join(D, 'voz.wav'))
h = h / np.max(np.abs(h)) * np.max(np.abs(v))
rest = v[int(REST * SR):]
src = np.concatenate([h, np.zeros(int(GAP * SR)), rest])
off_rest = len(h) / SR + GAP
def old2src(x): return off_rest + (x - REST)
def hook2src(x): return x - HOOK_A

# recorte de pausas: tramos de silencio largos se acortan; mapa src->comp a trozos
hop = 441; e = np.array([np.sqrt(np.mean(src[i:i + hop] ** 2)) for i in range(0, len(src), hop)])
sil = e < 0.008
keep = []; i = 0; n = len(sil)
while i < n:
    if sil[i]:
        j = i
        while j < n and sil[j]: j += 1
        dur = (j - i) * hop / SR
        if dur > MINP and i > 0 and j < n:
            cut = dur - MAXP; a0 = i * hop / SR + MAXP / 2
            keep.append((a0, a0 + cut))
        i = j
    else: i += 1
pieces = []; knots = [(0.0, 0.0)]; last = 0.0; removed = 0.0
for a0, a1 in keep:
    pieces.append(src[int(last * SR):int(a0 * SR)]); removed += a1 - a0
    knots += [(a0, a0 - (removed - (a1 - a0))), (a1, a1 - removed)]; last = a1
pieces.append(src[int(last * SR):]); comp = np.concatenate(pieces)
knots.append((len(src) / SR, len(comp) / SR))
kx, ky = np.array(knots).T
def s2n(x): return float(np.interp(x, kx, ky)) / SPEED

tmp = os.path.join(D, '_comp.wav'); sf.write(tmp, comp.astype(np.float32), SR)
out = os.path.join(D, 'voz_v2_raw.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-af', f'atempo={SPEED}', '-ar', str(SR), out], check=True)
vv = mono(out)
END = round(len(vv) / SR + 1.3, 2)
sf.write(os.path.join(D, 'voz_v2.wav'), np.concatenate([vv, np.zeros(int((END - len(vv) / SR) * SR) + SR)]).astype(np.float32)[:int(END * SR)], SR)

old = json.load(open(os.path.join(D, 'words.json')))
words = [[round(s2n(hook2src(a + HOOK_A)), 3), round(s2n(hook2src(b + HOOK_A)), 3), w] for a, b, w in HOOK_WORDS]
words += [[round(s2n(old2src(a)), 3), round(s2n(old2src(b)), 3), w] for a, b, w in old if a >= REST]
json.dump(words, open(os.path.join(D, 'words_v2.json'), 'w'), ensure_ascii=False)

cuts = []
for k, c in OLD_CUTS:
    st = min((w for w in old if w[0] >= c - 0.3), key=lambda w: w[0])[0]   # primera palabra de la escena
    cuts.append([k, round(s2n(old2src(st)) - 0.08, 3), c])
oldx = np.arange(REST, 79.3, 0.05)
json.dump({'END': END, 'cuts': cuts, 'hook_end': cuts[0][1],
           'o2n': [[round(x, 3), round(s2n(old2src(x)), 3)] for x in oldx]}, open(os.path.join(D, 'map_v2.json'), 'w'))
print('END', END, 'hook', cuts[0][1]); print(cuts)
