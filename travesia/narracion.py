# Narración del Episodio 1 (Kokoro TTS, voz masculina em_alex, español latino es-419).
# Genera un WAV por frase y un JSON con duraciones. Uso: python3 narracion.py <kokoro.onnx> <voices.bin> <carpeta>
import sys, os, json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

LINES = {
    'n1': ['¡Todos los países de América tienen que cruzar el Atlántico!',
           'Pero hay un pequeño problema...',
           '¡no todos llegarán vivos!'],
    'n2': ['Estados Unidos, México, Brasil, Argentina, Colombia y todos los demás tienen una misión:',
           'llegar a una isla que esconde un secreto.'],
    'n3': ['Ruta uno: el barco.',
           'Parece la más segura... hasta que llega la tormenta.',
           'Ruta dos: el avión.',
           'Es la más rápida... pero el combustible podría no alcanzar.',
           'Ruta tres: nadando.',
           'Nadie sabe qué se esconde en lo más profundo...'],
    'n4': ['Los países empiezan a discutir.',
           'Estados Unidos quiere tomar el control,',
           'Brasil parece estar preparando algo...',
           'y México acaba de descubrir algo extraño en el agua...'],
    'n5': ['¡Pero hay una regla!',
           'Cada país debe elegir solamente una ruta.',
           'Ahora tú decides:',
           '¿qué países van en barco, cuáles vuelan y cuáles se atreven a nadar?',
           '¡Escribe tu distribución en los comentarios...',
           'porque el próximo episodio dependerá de ustedes!'],
}
SPEED = {'n3': 1.1, 'n1': 1.12, 'n2': 1.12, 'n4': 1.08, 'n5': 1.12}

k = Kokoro(sys.argv[1], sys.argv[2]); out = sys.argv[3]; os.makedirs(out, exist_ok=True)
info = {}
for blk, lines in LINES.items():
    info[blk] = []
    for i, txt in enumerate(lines):
        a, sr = k.create(txt, voice='em_alex', speed=SPEED[blk], lang='es-419')
        idx = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, idx[0] - 200): idx[-1] + 1500]
        fn = f'{blk}_{i}.wav'; sf.write(os.path.join(out, fn), a, sr)
        info[blk].append({'file': fn, 'text': txt, 'dur': round(len(a) / sr, 3)})
        print(blk, i, round(len(a) / sr, 2), txt)
json.dump(info, open(os.path.join(out, 'lines.json'), 'w'), ensure_ascii=False, indent=1)
