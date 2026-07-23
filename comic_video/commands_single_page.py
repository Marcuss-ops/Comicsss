"""`single-page` command group — single-page analysis body.

LAYER SPLIT (split-commands-by-group, July 2026): extracted from
`comic_video.commands.run_single_page`. This file owns the
end-to-end run for analysing ONE page of a comic:

  1. Resolve the PDF path (CLI-provided, or auto-discover via
     `find_pdf(PROJECT_ROOT)` if absent).
  2. Ensure the page PNG exists (extract from PDF if not).
  3. Detect panels via `detect_panels`.
  4. Analyse each panel with Ollama vision via
     `analyze_page_panels`.
  5. Print results to stdout AND dump into a per-page JSON file
     (`page_<PAGE>_analysis.json`).

godlike/06 SSOT: this file is the SINGLE canonical owner of the
single-page orchestrator. `run_single_page(...)` in
`comic_video.commands` re-exports the function below for
back-compat.

Pre-split semantics preserved byte-byte: the function signature
lists the same kwargs in the same order, prints the same headers
(`"=" * 70` blocks), and writes the same JSON shape.
Output file name: `OUTPUT_DIR / f"page_{page:04d}_analysis.json"`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .analyzer import analyze_page_panels
from .config import OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS, OUTPUT_DIR, PROJECT_ROOT
from .extractor import extract_pdf_pages
from .ollama import DEFAULT_OLLAMA_URL
from .panel_detector import detect_panels
from .utils import find_pdf, log


def run_single_page(
    page: int,
    pdf: Optional[str] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = OLLAMA_MODEL,
    comic_title: str = "Batman: The Killing Joke",
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
) -> None:
    """Analizza una singola pagina PNG dal PDF usando panel detection + Ollama vision."""
    from PIL import Image

    if pdf:
        pdf_path = Path(pdf).resolve()
    else:
        pdf_path = find_pdf(PROJECT_ROOT)

    if not pdf_path.exists():
        log(f"Nessun PDF trovato in {PROJECT_ROOT} (ne in parent). Fornisci un percorso esplicito.", "error")
        raise FileNotFoundError(str(pdf_path))

    output_dir = OUTPUT_DIR
    page_path = output_dir / "pages" / f"page_{page:04d}.png"

    if not page_path.exists():
        print(f"  Pagina {page_path.name} non trovata. Estraggo dal PDF...")
        extracted = extract_pdf_pages(
            str(pdf_path), str(output_dir), dpi=200,
            use_ocr=True, requested_pages={page},
        )
        if not extracted:
            print(f"  ERRORE: impossibile estrarre la pagina {page}")
            raise RuntimeError(f"Could not extract page {page}")
        print(f"  Estratta: {page_path}")
    else:
        print(f"  Pagina gia' esistente: {page_path}")

    print("=" * 70)
    print(f"  ANALISI PAGINA: {page_path.name}")
    print(f"  Modello: {model}")
    print("=" * 70)

    img = Image.open(str(page_path))
    print(f"\n  Dimensioni: {img.width} x {img.height}")
    print(f"  Formato: {img.format}")
    print(f"  Modello: {img.mode}")
    print()

    print("  [Step 1] Rilevamento vignette...")
    panels = detect_panels(img, page_num=page)
    print(f"  -> Trovate {len(panels)} vignette\n")

    for i, p in enumerate(panels):
        print(f"    Vignetta {i+1}: ({p.x}, {p.y}) -> ({p.x + p.width}, {p.y + p.height}) "
              f"[{p.width}x{p.height}] full_page={p.is_full_page}")

    print()

    print(f"  [Step 2] Analisi con {model} (una vignetta alla volta)...")
    print()

    results = analyze_page_panels(
        model=model,
        panels=panels,
        ollama_url=ollama_url,
        timeout=timeout,
        comic_title=comic_title,
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

    output = {
        "pagina": page_path.name,
        "dimensioni": f"{img.width}x{img.height}",
        "vignette_trovate": len(panels),
        "analisi": results
    }

    out_path = output_dir / f"page_{page:04d}_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  Analisi salvata in: {out_path}")
    print()
