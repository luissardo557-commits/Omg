# Construye la pista de voz y los tiempos de cada frase.
#  a) desde frases sueltas (Kokoro):   python3 voz_timeline.py lines <carpeta_wavs> <salida.wav> <salida.json>
#  b) desde un único audio (Marcos):   python3 voz_timeline.py single <audio.mp3> <salida.wav> <salida.json> [durs_referencia.json]
#     — busca los silencios y elige los 13 cortes que mejor encajan con la proporción esperada de cada frase.
import sys, os, json, subprocess, re
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guion import LINES

SR = 44100
mode = sys.argv[1]

def load(path):
    tmp = '/tmp/claude-0/_voz_tmp.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-ac', '1', '-ar', str(SR), tmp], check=True)
    a, _ = sf.read(tmp); return a

if mode == 'lines':
    d = sys.argv[2]; files = sorted(f for f in os.listdir(d) if f.startswith('l') and f.endswith('.wav'))
    t = 0.2; gap = 0.35; segs = []; parts = []
    for f in files:
        a = load(os.path.join(d, f)); dur = len(a) / SR
        segs.append([round(t, 3), round(t + dur, 3)]); parts.append((t, a)); t += dur + gap
    out = np.zeros(int((t + 1.0) * SR))
    for s, a in parts: i = int(s * SR); out[i:i + len(a)] += a
else:
    a = load(sys.argv[2])
    # silencios (> 0.18 s por debajo de -35 dB)
    r = subprocess.run(['ffmpeg', '-i', sys.argv[2], '-af', 'silencedetect=noise=-35dB:d=0.18', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
    sil = list(zip(st, en))
    total = len(a) / SR
    speech_start = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    speech_end = sil[-1][0] if sil and sil[-1][1] > total - 0.05 else total
    ref = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else [len(l) for l in LINES]
    cum = np.cumsum(ref)[:-1] / sum(ref)
    expected = speech_start + cum * (speech_end - speech_start)
    cands = [(s, e) for s, e in sil if speech_start < s and e < speech_end]
    # programación dinámica: elegir len(LINES)-1 silencios en orden, minimizando la distancia a lo esperado (premia silencios largos)
    K = len(LINES) - 1; M = len(cands); INF = 1e9
    cost = [[INF] * (M + 1) for _ in range(K + 1)]; back = [[-1] * (M + 1) for _ in range(K + 1)]
    for j in range(M + 1): cost[0][j] = 0.0
    for k in range(1, K + 1):
        for j in range(1, M + 1):
            s, e = cands[j - 1]; mid = (s + e) / 2
            c = abs(mid - expected[k - 1]) - 0.8 * (e - s)
            best = min(range(j), key=lambda q: cost[k - 1][q]) if k > 1 else 0
            if cost[k - 1][best] < INF:
                cost[k][j] = cost[k - 1][best] + c; back[k][j] = best
    j = min(range(1, M + 1), key=lambda q: cost[K][q]); cuts = []
    for k in range(K, 0, -1): cuts.append(cands[j - 1]); j = back[k][j]
    cuts.reverse()
    bounds = [speech_start] + [x for c in cuts for x in c] + [speech_end]
    segs = [[round(bounds[2 * i], 3), round(bounds[2 * i + 1], 3)] for i in range(len(LINES))]
    shift = 0.2 - speech_start
    segs = [[s + shift, e + shift] for s, e in segs]
    out = np.zeros(int((segs[-1][1] + 1.0) * SR)); i0 = int(0.2 * SR)
    seg = a[int(speech_start * SR):]; out[i0:i0 + len(seg)] = seg[:len(out) - i0]
out = out / max(1e-6, np.max(np.abs(out))) * 0.9
sf.write(sys.argv[3], out, SR)
json.dump([{'start': s, 'end': e, 'text': t} for (s, e), t in zip(segs, LINES)], open(sys.argv[4], 'w'), ensure_ascii=False, indent=1)
for (s, e), t in zip(segs, LINES): print(f'{s:6.2f}-{e:6.2f}  {t}')
