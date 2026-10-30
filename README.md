# lecture-transcriber

Trascrivi lezioni e video-corsi allineando ciò che viene detto a ciò che appare a schermo: ASR locale (mlx-whisper) + OCR dei frame (Apple Vision) uniti per timestamp in un markdown leggibile, con immagini referenziate.

## Requisiti
- `ffmpeg` (`brew install ffmpeg`)
- Python 3.12 + venv con `mlx-whisper`
- Apple Silicon (MLX Whisper usa Metal)

## Installazione

1. Crea il venv:
   ```bash
   uv venv --python 3.12 ~/.venvs/lecture-transcriber
   uv pip install --python ~/.venvs/lecture-transcriber/bin/python mlx-whisper
   ```

2. Compila l'OCR (Apple Vision):
   ```bash
   swiftc -O bin/ocr.swift -o bin/ocr
   ```

3. Verifica: `bin/ocr <immagine.png>` deve stampare JSON con `text` e `lines`.

## Uso

```bash
PY=~/.venvs/lecture-transcriber/bin/python
$PY lecture_transcribe.py lezione.mp4 --out ./trascrizioni --title "Titolo lezione"
```

## Output

```
trascrizioni/
└── Titolo lezione/
    ├── Titolo lezione.md      # leggibile: timestamp + callout schermo
    ├── transcript.json        # segmenti ASR + schermate OCR (dati riusabili)
    └── frames/
        ├── 00-12.jpg          # solo frame con testo nuovo
        └── 00-17.jpg
```

## Parametri principali

| Flag | Default | Quando usarlo |
|---|---|---|
| `--scene` | `0.25` | più basso = più frame (slide che cambiano poco) |
| `--interval` | `20` | rete di sicurezza per slide statiche |
| `--max-frames` | `150` | alza su lezioni molto lunghe (> 40 min) |
| `--lang` | `it` | lingua della lezione |
| `--model` | `large-v3-turbo` | `mlx-community/whisper-large-v3-mlx` per più precisione |
| `--no-screen` | off | video senza contenuto visivo utile (solo webcam) |
| `--glossary` | — | file di testo con termini/nomi da suggerire all'ASR |

## Note di sicurezza
- **Non contiene segreti, cookie, password o dati personali** — i file sono generici e pronti per la pubblicazione su GitHub.
- **Non salva video pesanti** nella knowledge base. Solo audio + trascrizione markdown.
- **Non duplica i video** (3,6 GB) nel KB.
- **Non riscrive** i `.md` originali; `editoriale.md` è separato.
- **Regole editoriale**: non inventare, non ridurre, non tradurre marchi, `[incomprensibile]` per audio oscuro.

## Licenza

MIT — libero di usare, modificare e distribuire.