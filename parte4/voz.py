# Narración de la Parte 4 con Kokoro TTS (voz em_alex), sincronizada con los subtítulos.
# Uso: python3 voz.py <kokoro.onnx> <voices.bin> <salida.wav> <subs.json>
import sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

VOICE = 'em_alex'
# (inicio, fin, texto hablado) — los nombres turcos van escritos como se pronuncian
SEGS = [(0.0, 1.6, 'Derinkuyu no es la única.'),
        (1.6, 4.0, 'Bajo Capadocia hay muchas más ciudades escondidas.'),
        (4.0, 6.6, 'Kaimaklí, Oskonák, Masí...'),
        (6.6, 10.4, 'Se estima que en la región hay más de doscientas ciudades y refugios subterráneos.'),
        (10.4, 12.6, 'La mayoría son pequeños.'),
        (12.6, 15.0, 'Pero algunos son gigantes.'),
        (15.0, 17.8, 'Y una de las más sorprendentes apareció hace muy poco.'),
        (17.8, 20.6, 'En dos mil catorce, en la ciudad de Nevsejír,'),
        (20.6, 24.0, 'unas obras derribaban casas viejas alrededor del castillo.'),
        (24.0, 27.0, 'Debajo de ellas apareció la entrada a otra ciudad subterránea:'),
        (27.0, 31.5, 'túneles, habitaciones y capillas talladas en la roca,'),
        (31.5, 36.0, 'todo escondido durante siglos...'),
        (36.0, 40.0, 'justo debajo de la gente.'),
        (40.0, 43.6, 'Los primeros estudios sugieren que podría ser incluso más grande que Derinkuyu.'),
        (43.6, 46.4, 'Pero gran parte sigue enterrada,'),
        (46.4, 49.6, 'y excavarla es lento y delicado,'),
        (49.6, 52.4, 'porque encima hay calles, casas y gente viviendo hoy.'),
        (52.4, 55.0, 'Nadie sabe todavía hasta dónde llega.'),
        (55.0, 57.4, 'Pero hay una pregunta más importante.'),
        (57.4, 60.6, 'Si construyeron tantas ciudades bajo tierra...'),
        (60.6, 63.0, '¿de quién se estaban escondiendo?'),
        (63.0, 65.0, 'Te lo cuento en la parte cinco.')]

import json
BLOCKS = [(0.0, 15.0, range(0, 6)), (15.0, 40.0, range(6, 13)), (40.0, 55.0, range(13, 18)), (55.0, 64.4, range(18, 22))]
k = Kokoro(sys.argv[1], sys.argv[2])
SR = 24000
out = np.zeros(int(65.0 * SR), dtype=np.float32)
subs = []

def say(txt, speed):
    audio, sr = k.create(txt, voice=VOICE, speed=speed, lang='es')
    idx = np.where(np.abs(audio) > 0.01)[0]
    return audio[max(0, idx[0] - 200): idx[-1] + 1200]

for b0, b1, ids in BLOCKS:
    speed = 0.92
    while True:
        clips = [say(SEGS[i][2], speed) for i in ids]
        talk = sum(len(c) for c in clips) / SR
        free = (b1 - b0 - 0.3) - talk
        if free >= 0.35 * (len(clips) - 1) or speed >= 1.15: break
        speed += 0.04
    gap = min(1.1, max(0.25, free / max(1, len(clips) - 1)))
    t = b0 + 0.15
    for i, c in zip(ids, clips):
        d = len(c) / SR
        j = int(t * SR); out[j:j + len(c)] += c[:len(out) - j]
        subs.append((round(t, 2), round(t + d + gap * 0.8, 2), i))
        print(f'{t:5.1f}-{t + d:5.1f} vel {speed:.2f} {SEGS[i][2]}')
        t += d + gap
out = out / max(1e-6, np.max(np.abs(out))) * 0.9
sf.write(sys.argv[3], out, SR)
json.dump(subs, open(sys.argv[4], 'w'))
