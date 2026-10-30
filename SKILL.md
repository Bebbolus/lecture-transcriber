SKILL.md — Skill: lecture-transcriber

Ultima modifica: 2026-10-30
Licenza: MIT

1. Scopo
Trascrivi lezioni e video-corsi allineando ciò che viene detto a ciò che appare a schermo: ASR locale (mlx-whisper) + OCR dei frame (Apple Vision) uniti per timestamp in un markdown leggibile, con immagini referenziate. Usa quando l'utente chiede di "trascrivere un corso", "trascrivere le lezioni", "estrarre il testo dai video", "cosa dicono e cosa mostrano", "sbobinare", o di rendere ricercabile/documentabile una serie di video.

2. Trigger parole-chiave
- `trascrivi video`
- `sbobinatura lezione`
- `download video Udemy`
- `estrai testo da video`
- `ASR + OCR`
- `legge-filma`

3. Input
- `**video**`: file video (MP4, MOV, WebM)
- `**lang**`: `it`, `en`, `auto` (default `it`)
- `**out**`: cartella di output
- `**model**`: modello whsiper (default `mlx-community/whisper-large-v3-turbo`)
- `**scene**`, `**interval**`, `**max-frames**`: parametri OCR
- **`--no-screen`**: salta OCR se mancano le slide

4. Output
```
<out>/<titolo>/
├── <titolo>.md         # leggibile: timestamp + callout schermo
├── transcript.json     # dati grezzi: segmenti ASR + schermate OCR
└── frames/             # solo frame con testo nuovo
```

5. Prerequisiti (una volta sola)
```bash
brew install ffmpeg

# Python 3.12: mlx-whisper su Apple Silicon
uv venv --python 3.12 ~/.venvs/lecture-transcriber
uv pip install --python ~/.venvs/lecture-transcriber/bin/python mlx-whisper

# OCR: compila il binario Swift
swiftc -O bin/ocr.swift -o bin/ocr
```

6. Uso base
```bash
PY=~/.venvs/lecture-transcriber/bin/python
$PY lecture_transcribe.py lezione.mp4 --out ./trascrizioni --title "Titolo lezione"
```

7. Workflow
1. Probe durata video (`ffprobe`)
2. Estrai audio WAV monourale 16kHz (`ffmpeg`)
3. ASR mlx-whisper → segmenti con timestamp
4. Frame ogni `--scene` soglia + intervallo, OCR Apple Vision → schermate
5. Unisci audio + schermate in markdown con timestamp [mm:ss]

8. Calibrazione modello
PREROSSA = glossario con termini ricorrenti (tool, nomi, acronimi). Se i termini sono < 120, aggiungili all'initial_prompt dell'ASR.

9. Limiti noti
- Screenshot testo piccolo → OCR parziale (include comunque l'immagine)
- Video solo webcam → skip OCR con `--no-screen`
- Audio con musica/più voci → ASR confuso (nessun fix automatico)
- Primo run → ~1.6 GB modello MLX (una tantum)

10. Relazioni
- **Dipende da**: `mlx-whisper` (ASR), Apple Vision (OCR), `ffmpeg` (audio/frame)
- **Complementare**: `video-downloader` (prepara il file video prima della trascrizione)
- **Non tocca**: file `.md` originali del Knowledge Base (regola Atomic Markdown)