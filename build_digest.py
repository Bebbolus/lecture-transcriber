#!/usr/bin/env python3
"""build_digest.py — estrae da ogni editoriale.md solo sintesi, punti chiave e strumenti.

Serve a passare il corso a un modello senza il testo integrale (80 lezioni ≈ 30k token
invece di 100k), per sintesi di corso o interrogazioni trasversali.

Uso:
    build_digest.py "4 - STUDIO/TRASCRIZIONE_5008250" [-o _risorse/digest.md]
"""
import re
import sys
from pathlib import Path

KEEP = ("## Sintesi", "## Punti chiave", "## Strumenti e termini")


def section(text, name):
    m = re.search(rf"^{re.escape(name)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else root / "_risorse" / "digest.md"
    parts = ["# Digest del corso", "",
             "Sintesi, punti chiave e strumenti di ogni lezione (dal pass editoriale).", ""]
    n = 0
    for ed in sorted(root.glob("*/editoriale.md")):
        text = ed.read_text(encoding="utf-8")
        title = ed.parent.name
        chunk = [f"## {title}", ""]
        for k in KEEP:
            body = section(text, k)
            if body:
                chunk += ([body, ""] if k == "## Sintesi" else [f"**{k[3:]}**", "", body, ""])
        parts += chunk
        n += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"digest scritto: {out} · {n} lezioni · {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
