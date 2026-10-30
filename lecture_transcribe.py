#!/usr/bin/env python3
"""lecture_transcribe.py — trascrizione allineata di una lezione video.

Audio  : mlx-whisper (large-v3-turbo, Metal) con glossario di dominio.
Schermo: frame ai cambi scena + OCR Apple Vision (bin/ocr), allineati al timestamp.
Output : <out>/<titolo>.md (leggibile), transcript.json (dati grezzi), frames/*.

Esempio:
    lecture_transcribe.py lezione.mp4 --out ./trascrizioni \
        --title "Cosa è un'estensione" --glossary glossario.txt
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OCR = HERE / "bin" / "ocr"
DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"

# Prompt ASR: nomi propri e tool che Whisper sbaglia più spesso in italiano.
BASE_PROMPT = (
    "Lezione di OSINT in italiano. Termini ricorrenti: OSINT, Ghunt, Holehe, Epieos, "
    "LeakCheck, Have I Been Pwned, Seon, Sherlock, Maltego, Shodan, Whois, DNS, VPN, Tor, "
    "dark web, Google Dork, reverse image search, Yandex, Bing, Kali Linux, VirtualBox, "
    "VMware, Telegram, Instagram, Facebook, TikTok, LinkedIn, X, Twitter, OnlyFans."
)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe_duration(video):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(video)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"ERRORE: durata non leggibile da {video}")


def extract_audio(video, wav):
    r = run(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
             "-c:a", "pcm_s16le", str(wav)])
    if r.returncode != 0:
        sys.exit("ERRORE ffmpeg (audio):\n" + r.stderr[-800:])


def scene_times(video, threshold):
    """Timestamp dei cambi scena, letti da showinfo."""
    r = run(["ffmpeg", "-i", str(video), "-filter:v",
             f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    times = [float(m) for m in re.findall(r"pts_time:\s*([0-9.]+)", r.stderr)]
    return [t for t in times if t > 0.4]


def plan_frames(duration, scenes, interval, min_gap, max_frames):
    """Unisce cambi scena + campionamento uniforme, poi dirada."""
    times = sorted(set(scenes) | set(x * interval for x in range(int(duration / interval) + 1)))
    out = []
    for t in times:
        if not out or t - out[-1] >= min_gap:
            out.append(round(t, 2))
    if len(out) > max_frames:
        step = len(out) / max_frames
        out = [out[int(i * step)] for i in range(max_frames)]
    return out


def grab_frame(video, t, dest):
    r = run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
             "-vf", "scale='min(1600,iw)':-2", "-q:v", "3", str(dest)])
    return r.returncode == 0 and dest.exists()


def ocr(path, ocr_bin, lang):
    r = run([str(ocr_bin), str(path), lang])
    if r.returncode != 0:
        return ""
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return ""
    keep = [l["text"] for l in data.get("lines", []) if l.get("conf", 0) >= 0.3]
    return "\n".join(keep).strip()


# Chrome del player e rumore ricorrente: non sono contenuto della lezione.
NOISE = re.compile(
    r"^(?:[^\w]{0,3}[ûúùüodbsbm]?demy|udemy|panoramica|note|risorse|impostazioni|"
    r"riproduci|schermo intero|^[\d:]{3,8}\s*/\s*[\d:]{3,8})$",
    re.IGNORECASE)


def clean_screen(text, max_lines=28):
    """Toglie il rumore del player, redige le email, limita la lunghezza."""
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if len(s) < 3 or NOISE.match(s):
            continue
        s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", s)
        lines.append(s)
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"… (+{len(lines) - max_lines} righe — vedi immagine)"]
    return "\n".join(lines)


def similar(a, b, threshold=0.75):
    """Schermate quasi identiche (stessa pagina, piccolo scroll)."""
    if not a or not b:
        return False
    sa, sb = set(norm(a).split()), set(norm(b).split())
    if not sa or not sb:
        return False
    return len(sa & sb) / len(sa | sb) >= threshold


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def fmt_ts(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def merge_segments(segments, max_chars=280):
    """Unisce i frammenti ASR che spezzano la stessa frase (Whisper taglia ogni ~5 s)."""
    out = []
    for seg in segments:
        if not seg["text"]:
            continue
        prev = out[-1] if out else None
        if (prev and seg["start"] - prev["end"] < 0.45
                and not re.search(r"[.!?]$", prev["text"])
                and len(prev["text"]) + len(seg["text"]) <= max_chars):
            prev["text"] += " " + seg["text"]
            prev["end"] = seg["end"]
        else:
            out.append(dict(seg))
    return out


def main():
    ap = argparse.ArgumentParser(description="Trascrizione audio+schermo di una lezione.")
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    ap.add_argument("--lang", default="it")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--glossary", help="file di testo con termini/nomi da suggerire all'ASR")
    ap.add_argument("--ocr-bin", default=str(DEFAULT_OCR))
    ap.add_argument("--scene", type=float, default=0.25, help="soglia cambio scena 0..1")
    ap.add_argument("--interval", type=float, default=20.0, help="frame di sicurezza ogni N s")
    ap.add_argument("--min-gap", type=float, default=4.0, help="distanza minima tra frame")
    ap.add_argument("--max-frames", type=int, default=150)
    ap.add_argument("--no-screen", action="store_true", help="salta frame/OCR")
    ap.add_argument("--keep-wav", action="store_true")
    ap.add_argument("--force", action="store_true", help="riesegue anche se il .md esiste già")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.exists():
        sys.exit(f"ERRORE: video non trovato: {video}")
    title = args.title or video.stem
    out = Path(args.out)
    dest = out / re.sub(r'[/\\:*?"<>|]+', "-", title).strip().strip(".") or "lezione"
    if (dest / f"{title}.md").exists() and not args.force:
        print(f"SALTO (già trascritto): {title}")
        return
    frames_dir = dest / "frames"
    dest.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(video)
    print(f"[1/4] audio · {fmt_ts(duration)} · {video.name}", flush=True)
    tmp = Path(tempfile.mkdtemp(prefix="lecture_"))
    wav = tmp / "audio.wav"
    extract_audio(video, wav)

    prompt = BASE_PROMPT
    if args.glossary and Path(args.glossary).exists():
        terms = [t.strip() for t in Path(args.glossary).read_text(encoding="utf-8").splitlines()
                 if t.strip() and not t.startswith("#")]
        if terms:
            prompt += " " + ", ".join(terms[:120]) + "."

    print("[2/4] ASR · mlx-whisper", flush=True)
    import mlx_whisper  # import ritardato: pesa
    result = mlx_whisper.transcribe(
        str(wav),
        path_or_hf_repo=args.model,
        language=args.lang,
        word_timestamps=True,
        initial_prompt=prompt[:900],
        condition_on_previous_text=False,
        verbose=False,
    )
    segments = [{"start": float(s["start"]), "end": float(s["end"]),
                 "text": s["text"].strip()} for s in result.get("segments", [])]
    segments = merge_segments(segments)
    if args.keep_wav:
        shutil.copy(wav, dest / "audio.wav")

    screens = []
    if not args.no_screen:
        print("[3/4] frame + OCR", flush=True)
        frames_dir.mkdir(exist_ok=True)
        scenes = scene_times(video, args.scene)
        plan = plan_frames(duration, scenes, args.interval, args.min_gap, args.max_frames)
        print(f"      {len(scenes)} cambi scena -> {len(plan)} frame", flush=True)
        last = None
        for t in plan:
            name = f"{fmt_ts(t).replace(':', '-')}.jpg"
            frame_path = frames_dir / name
            if not grab_frame(video, t, frame_path):
                continue
            text = ocr(frame_path, args.ocr_bin, args.lang)
            text = clean_screen(text)
            if not text or similar(text, last):
                frame_path.unlink(missing_ok=True)  # schermata identica o solo chrome: non serve
                continue
            last = text
            screens.append({"t": t, "file": f"frames/{name}", "text": text})
    shutil.rmtree(tmp, ignore_errors=True)

    print("[4/4] markdown", flush=True)
    md = [f"---",
          f"title: {json.dumps(title, ensure_ascii=False)}",
          f"source: {json.dumps(video.name, ensure_ascii=False)}",
          f"duration: {fmt_ts(duration)}",
          f"asr: {args.model} ({args.lang})",
          f"ocr: apple-vision" if screens else "ocr: none",
          f"---", "", f"# {title}", "",
          f"**Durata** {fmt_ts(duration)} · **Trascrizione** `{args.model.split('/')[-1]}` · "
          f"**Schermate lette** {len(screens)}", ""]

    def screen_for(start, end):
        chunk = [s for s in screens if start <= s["t"] < end]
        if not chunk:
            return []
        block = []
        for s in chunk:
            block += [f"> **🖥 Schermo — {fmt_ts(s['t'])}**", f"> ![]({s['file']})", ">"]
            block += ["> " + line for line in s["text"].splitlines()]
            block.append("")
        return block

    for seg in segments:
        if not seg["text"]:
            continue
        md.append(f"**[{fmt_ts(seg['start'])}]** {seg['text']}")
        md.extend(screen_for(seg["start"], seg["end"]))
        md.append("")

    (dest / f"{title}.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    (dest / "transcript.json").write_text(json.dumps({
        "title": title, "source": video.name, "duration": duration,
        "model": args.model, "language": args.lang,
        "segments": segments, "screens": screens,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    words = sum(len(s["text"].split()) for s in segments)
    print(f"FATTO · {len(segments)} segmenti, {words} parole, {len(screens)} schermate")


if __name__ == "__main__":
    main()
