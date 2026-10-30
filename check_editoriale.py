#!/usr/bin/env python3
"""check_editoriale.py — controllo qualità del pass editoriale.

Verifica, per ogni lezione:
  - editoriale.md presente e con le sezioni del contratto;
  - fedeltà: parole del "Testo riveduto" vs parole della trascrizione (85–120%);
  - copertura dei timestamp (≥ 85% dei segmenti ASR);
  - tabella Correzioni presente (anche vuota, ma dichiarata).

Uso:
    check_editoriale.py "4 - STUDIO/TRASCRIZIONE_5008250"
"""
import json
import re
import sys
from pathlib import Path

REQ = ["## Sintesi", "## Punti chiave", "## Testo riveduto"]
TS = re.compile(r"\*\*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\*\*")


def section(text, name):
    m = re.search(rf"^{re.escape(name)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    ok, problems = 0, []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "_risorse"):
        ed, tr = d / "editoriale.md", d / "transcript.json"
        if not ed.exists():
            problems.append((d.name, "manca editoriale.md"))
            continue
        text = ed.read_text(encoding="utf-8")
        miss = [h for h in REQ if h not in text]
        if miss:
            problems.append((d.name, "sezioni mancanti: " + ", ".join(miss)))
            continue
        if "## Correzioni" not in text:
            problems.append((d.name, "manca la tabella Correzioni"))
            continue
        body = section(text, "## Testo riveduto")
        words_body = len(re.sub(r"\*\*\[[^\]]+\]\*\*", "", body).split())
        try:
            data = json.loads(tr.read_text(encoding="utf-8"))
        except Exception:
            problems.append((d.name, "transcript.json illeggibile"))
            continue
        words_tr = sum(len(s["text"].split()) for s in data.get("segments", []))
        ratio = words_body / words_tr if words_tr else 0
        stamps = len(TS.findall(body))
        segs = len(data.get("segments", []))
        cov = stamps / segs if segs else 0
        if ratio < 0.85:
            problems.append((d.name, f"testo ridotto al {ratio:.0%} dell'originale"))
        elif ratio > 1.20:
            problems.append((d.name, f"testo gonfiato al {ratio:.0%} dell'originale"))
        elif cov < 0.85:
            problems.append((d.name, f"timestamp coperti {cov:.0%} ({stamps}/{segs})"))
        else:
            ok += 1
    total = ok + len(problems)
    print(f"controllate: {total} | ok: {ok} | problemi: {len(problems)}")
    for name, why in problems:
        print(f"  · {name}: {why}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
