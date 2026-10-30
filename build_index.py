#!/usr/bin/env python3
"""build_index.py — indice navigabile di un corso trascritto.

Legge il curriculum Udemy (capitoli/lezioni) e le trascrizioni prodotte da
lecture_transcribe.py, e genera INDICE.md con: ordine del corso, durata,
parole, schermate lette, link al markdown e stato di copertura.

Uso:
    build_index.py --course 5008250 --cookies "4 - STUDIO/udemy_cookies.txt" \
        --transcripts "4 - STUDIO/TRASCRIZIONE_5008250" \
        --extra "4 - STUDIO/PROOF_EXTRA" \
        --out "4 - STUDIO/TRASCRIZIONE_5008250/INDICE.md"
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "udemy-dl"))
from udemy_extra import Udemy  # noqa: E402


def enc(path):
    """URL-encoding per markdown: parentesi e spazi nei nomi delle lezioni."""
    return quote(str(path), safe="/")


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def find_transcript(root, title, chapter=""):
    """Trova la trascrizione della lezione, disambiguando i titoli duplicati col capitolo."""
    if not root.exists():
        return None
    t, c = norm(title), norm(chapter or "")
    cands = [d for d in root.iterdir() if d.is_dir() and norm(d.name).startswith(t)]
    if not cands:
        return None
    exact = [d for d in cands if norm(d.name) == t]
    if len(exact) == 1:
        pick = exact[0]
    else:
        byc = [d for d in cands if c and c in norm(d.name)]
        pick = byc[0] if byc else cands[0]
    f = pick / "transcript.json"
    return f if f.exists() else None


def find_article(root, title):
    if not root:
        return None
    d = root / "articoli"
    if not d.exists():
        return None
    t = norm(title)
    for f in d.glob("*.md"):
        if t in norm(f.stem):
            return f
    return None


def fmt(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--cookies", required=True)
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--resources", "--extra", dest="extra",
                    help="cartella risorse del pacchetto (articoli/, allegati/, RISORSE.md)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    api = Udemy(args.cookies)
    cid = api.resolve_course_id(args.course)
    items = api.curriculum(cid)
    tr = Path(args.transcripts)
    extra = Path(args.extra) if args.extra else None

    rows, chapter, stats = [], None, {"done": 0, "video": 0, "words": 0, "screens": 0,
                                      "dur": 0.0, "missing": []}
    order = 0
    for it in items:
        if it.get("_class") == "chapter":
            chapter = it.get("title")
            rows.append(("chapter", chapter))
            continue
        if it.get("_class") != "lecture":
            continue
        order += 1
        title = it.get("title", "")
        atype = (it.get("asset") or {}).get("asset_type")
        f = find_transcript(tr, title, chapter)
        art = find_article(extra, title) if (atype == "Article" and extra) else None
        if f:
            data = json.loads(f.read_text(encoding="utf-8"))
            words = sum(len(s["text"].split()) for s in data.get("segments", []))
            screens = len(data.get("screens", []))
            dur = data.get("duration", 0)
            stats["done"] += 1
            stats["words"] += words
            stats["screens"] += screens
            stats["dur"] += dur
            rel = f.parent.relative_to(tr)
            ed = f.parent / "editoriale.md"
            row = (order, title, atype, fmt(dur), words, screens, f"{rel}/{rel.name}.md",
                   f"{rel}/editoriale.md" if ed.exists() else None)
            if ed.exists():
                stats["edited"] = stats.get("edited", 0) + 1
            if atype in ("Video", "VideoMashup"):
                stats["video"] += 1
        elif atype == "Article":
            link = str(art.relative_to(tr)) if art else None
            row = (order, title, atype, "—", "—", "—", link, None)
        else:
            row = (order, title, atype, "—", "—", "—", None, None)
            if atype in ("Video", "VideoMashup"):
                stats["missing"].append(title)
        rows.append(("lecture", row))

    out = [f"# Indice del corso {cid}", "",
           f"**Trascritte** {stats['done']} lezioni · **durata coperta** {fmt(stats['dur'])} · "
           f"**parole** {stats['words']:,} · **schermate lette** {stats['screens']}", ""]
    if stats.get("edited"):
        out += [f"**Edizione riveduta**: {stats['edited']} lezioni (colonna *Ed.*, sintesi + "
                f"testo corretto con evidenza dallo schermo).", ""]
    if extra and (extra / "RISORSE.md").exists():
        rel = extra.relative_to(tr) if extra.is_relative_to(tr) else Path(extra.name)
        out.append(f"Link esterni del corso: [`RISORSE.md`]({enc(rel)}/RISORSE.md) · "
                   f"articoli in `{rel}/articoli/` · allegati in `{rel}/allegati/`")
        out.append("")

    in_table = False
    for kind, payload in rows:
        if kind == "chapter":
            out += ["", f"## {payload}", "",
                    "| # | Lezione | Tipo | Durata | Parole | Schermate | Ed. |",
                    "|---|---|---|---|---|---|---|"]
            in_table = True
            continue
        order, title, atype, dur, words, screens, link, ed = payload
        if link:
            name = f"[{title}]({enc(link)})"
        elif atype == "Article":
            name = f"{title} *(testo non pubblicato)*"
        else:
            name = title
        cell = f"[riveduta]({enc(ed)})" if ed else "—"
        out.append(f"| {order} | {name} | {atype or '—'} | {dur} | {words} | {screens} | {cell} |")

    if stats["missing"]:
        out += ["", "## Non trascritte", ""]
        out += [f"- {t}" for t in stats["missing"]]

    if extra:
        for sub, label in (("articoli", "Articoli"), ("allegati", "Allegati")):
            d = extra / sub
            if not d or not d.exists():
                continue
            files = sorted(d.iterdir())
            if not files:
                continue
            out += ["", f"## {label}", ""]
            for f in files:
                rel = f.relative_to(tr) if f.is_relative_to(tr) else Path(extra.name) / sub / f.name
                out.append(f"- [{f.name}]({enc(rel)})")

    Path(args.out).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"INDICE scritto: {args.out} · {stats['done']} lezioni, {len(stats['missing'])} mancanti")


if __name__ == "__main__":
    main()
