#!/usr/bin/env python3
"""
Analizza una singola pagina PNG dal PDF usando il pipeline esistente (panel detection + Ollama vision).
Accetta il numero di pagina come argomento. Estrae la pagina dal PDF se non esiste gia'.
"""

import sys
import json
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from comic_video.panel_detector import detect_panels
from comic_video.analyzer import analyze_page_panels
from comic_video.extractor import extract_pdf_pages
from comic_video.utils import log

# Fix per Windows cp1252
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    if len(sys.argv) < 2:
        print("Usa: python analyze_single_page.py <numero_pagina>")
        print("Es:  python analyze_single_page.py 7")
        sys.exit(1)

    page_num = int(sys.argv[1])
    pdf_path = r"C:\Users\pater\Pyt\comics\comic-pdf-video-maker\4fumetti-ita-batman-the-killing-joke-dc.pdf"
    output_dir = r"C:\Users\pater\Pyt\comics\comic-pdf-video-maker\output"
    page_path = Path(output_dir) / "pages" / f"page_{page_num:04d}.png"

    # Estrai pagina se non esiste
    if not page_path.exists():
        print(f"  Pagina {page_path.name} non trovata. Estraggo dal PDF...")
        extracted = extract_pdf_pages(
            pdf_path, output_dir, dpi=200,
            use_ocr=True, requested_pages={page_num},
        )
        if not extracted:
            print(f"  ERRORE: impossibile estrarre la pagina {page_num}")
            sys.exit(1)
        print(f"  Estratta: {page_path}")
    else:
        print(f"  Pagina gia' esistente: {page_path}")

    print("=" * 70)
    print(f"  ANALISI PAGINA: {page_path.name}")
    print(f"  Modello: llava:13b")
    print("=" * 70)

    # Carica immagine
    img = Image.open(str(page_path))
    print(f"\n  Dimensioni: {img.width} x {img.height}")
    print(f"  Formato: {img.format}")
    print(f"  Modello: {img.mode}")
    print()

    # Step 1: Panel detection
    print("  [Step 1] Rilevamento vignette...")
    panels = detect_panels(img, page_num=page_num)
    print(f"  -> Trovate {len(panels)} vignette\n")

    for i, p in enumerate(panels):
        print(f"    Vignetta {i+1}: ({p.x}, {p.y}) -> ({p.x + p.width}, {p.y + p.height}) "
              f"[{p.width}x{p.height}] full_page={p.is_full_page}")

    print()

    # Step 2: Analisi con llava:13b
    print("  [Step 2] Analisi con llava:13b (una vignetta alla volta)...")
    print()

    results = analyze_page_panels(
        model="llava:13b",
        panels=panels,
        ollama_url="http://localhost:11434",
        timeout=300,
        comic_title="Batman: The Killing Joke",
        use_balloon_ocr=True,
        skip_no_balloon=False,
    )

    print()
    print("=" * 70)
    print("  RISULTATI ANALISI")
    print("=" * 70)

    for r in results:
        print(f"\n  [+] Vignetta {r['panel_num']}/{r['total_panels']} (pagina {r['page_num']})")
        print(f"      Tipo: {r.get('tipo', '?')}")
        print(f"      Titolo: {r.get('titolo', '?')}")
        print(f"      Personaggi: {r.get('personaggi', '?')}")
        print(f"      Ambientazione: {r.get('ambientazione', '?')}")
        print(f"      Descrizione: {r.get('descrizione', '?')}")
        if r.get('dialoghi'):
            print(f"      Dialoghi: \"{r['dialoghi']}\"")
        if r.get('dialoghi_ocr'):
            print(f"      OCR Balloon: {r['dialoghi_ocr']}")
        if r.get('effetto_sonoro'):
            print(f"      Effetto sonoro: {r['effetto_sonoro']}")
        print(f"      Durata stimata: {r.get('durata_stimata', '?')}s")

    # Salva su file
    output = {
        "pagina": page_path.name,
        "dimensioni": f"{img.width}x{img.height}",
        "vignette_trovate": len(panels),
        "analisi": results
    }

    out_path = Path(output_dir) / f"page_{page_num:04d}_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  Analisi salvata in: {out_path}")
    print()

if __name__ == "__main__":
    main()
