# Cambia el gancho: reemplaza la frase 1 del audio de Marcos por un MP3 nuevo (o solo la retrasa)
# para dejar sitio al susto visual del primer segundo.
# Uso: python3 replace_hook.py <voz.wav> <tiempos.json> <salida_voz.wav> <salida_tiempos.json> [gancho.mp3 "texto del gancho"]
import sys, json, subprocess
import numpy as np, soundfile as sf

SR = 44100; START = 0.75; GAP = 0.45
voz, tj, ov, otj = sys.argv[1:5]
a, sr = sf.read(voz)
if a.ndim > 1: a = a.mean(1)
lines = json.load(open(tj))
if len(sys.argv) > 5:
    tmp = '/tmp/claude-0/_hook.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', sys.argv[5], '-ac', '1', '-ar', str(SR),
                    '-af', 'silenceremove=start_periods=1:start_threshold=-40dB,areverse,silenceremove=start_periods=1:start_threshold=-40dB,areverse', tmp], check=True)
    h, _ = sf.read(tmp)
    h = h / max(1e-6, np.max(np.abs(h))) * np.max(np.abs(a))
    rest_from = lines[1]['start']
    rest = a[int(rest_from * SR):]
    new_l1 = START + len(h) / SR + GAP
    out = np.zeros(int((new_l1 + len(rest) / SR + 0.5) * SR))
    out[int(START * SR):int(START * SR) + len(h)] = h
    i = int(new_l1 * SR); out[i:i + len(rest)] = rest
    shift = new_l1 - rest_from
    lines[0] = {'start': START, 'end': round(START + len(h) / SR, 3), 'text': sys.argv[6] if len(sys.argv) > 6 else lines[0]['text']}
    for l in lines[1:]: l['start'] = round(l['start'] + shift, 3); l['end'] = round(l['end'] + shift, 3)
else:
    shift = START - lines[0]['start']
    out = np.concatenate([np.zeros(int(shift * SR)), a])
    for l in lines: l['start'] = round(l['start'] + shift, 3); l['end'] = round(l['end'] + shift, 3)
sf.write(ov, out.astype(np.float32), SR)
json.dump(lines, open(otj, 'w'), ensure_ascii=False, indent=1)
for l in lines[:3]: print(l)
print('fin', lines[-1]['end'])
