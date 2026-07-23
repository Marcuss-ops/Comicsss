"""`ocr-test` command group — per-page OCR deep-debug body.

LAYER SPLIT (split-commands-by-group, July 2026): extracted from
`comic_video.commands.run_ocr_test` along with the OCR debug-image
helper (`_draw_panel_with_balloons`). This file owns the
end-to-end run for the OCR deep-debug diagnostic:

  1. Resolve the source page PNG (extract from PDF if absent).
  2. Detect panels via `detect_panels`.
  3. Per-panel: detect balloons + extract text via
     `detect_balloons` (with relaxed area / circularity params
     tuned for spotting text).
  4. Per-panel: draw every balloon on a debug-image copy via
     `_draw_panel_with_balloons` (numbered + coloured rectangles
     with the OCR-extracted text).
  5. Per-panel: as a cross-check, run easyocr.readtext on the
     WHOLE panel image (not only the balloon crops) so an
     operator can compare detected-vs-extracted texts.
  6. Emit a typed OCR report (`page_<PAGE>_ocr_test.json`) with
     per-balloon positions, texts, and confidence.

godlike/06 SSOT: this file is the SINGLE canonical owner of:

  - `run_ocr_test(page_num)` orchestrator.
  - `_draw_panel_with_balloons(panel_image, balloons, panel_num,
    page_num, debug_dir)` debug-image renderer.

Wire contract: `comic_video.commands.COMMANDS["ocr-test"]` binds
to `run_ocr_test`; the helper stays private to this module
(`_` prefix) — external callers reach the orchestrator only.
"""

from __future__ import annotations

import json
from pathlib import Path

from .balloon_detector import detect_balloons
from .config import OUTPUT_DIR, PROJECT_ROOT
from .extractor import extract_pdf_pages
from .panel_detector import detect_panels
from .utils import find_pdf, log


def _draw_panel_with_balloons(panel_image, balloons, panel_num, page_num, debug_dir: Path):
    """Disegna TUTTI i balloon su una copia dell'immagine con numeri e testo."""
    import cv2
    import numpy as np
    img_np = np.array(panel_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    for i, b in enumerate(balloons):
        color = (
            (255, 0, 0) if i % 3 == 0 else
            (0, 255, 0) if i % 3 == 1 else
            (0, 0, 255)
        )
        cv2.rectangle(img_bgr,
            (b.x, b.y),
            (b.x + b.width, b.y + b.height),
            color, 2)

        label = f"B{i+1}: \"{b.text[:80]}\" [{b.confidence:.2f}]"
        label_y = max(20, b.y - 8)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(img_bgr,
            (b.x - 2, label_y - th - 2),
            (b.x + tw + 2, label_y + 2),
            (0, 0, 0), -1)
        cv2.putText(img_bgr, label, (b.x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    out = debug_dir / f"page{page_num:04d}_panel{panel_num:02d}_debug.png"
    cv2.imwrite(str(out), img_bgr)
    return out


def run_ocr_test(page_num: int = 7) -> None:
    """Test approfondito OCR: mostra balloon rilevati, testo estratto e debug visivo."""
    from PIL import Image
    import cv2
    import numpy as np

    page_path = OUTPUT_DIR / "pages" / f"page_{page_num:04d}.png"

    if not page_path.exists():
        print(f"ERRORE: {page_path} non trovata. Estrai prima la pagina.")
        pdf_path = find_pdf(PROJECT_ROOT)
        if not pdf_path.exists():
            log(f"Nessun PDF trovato in {PROJECT_ROOT}. Fornisci un PDF o estrai prima la pagina.", "error")
            raise FileNotFoundError(str(pdf_path))
        extract_pdf_pages(str(pdf_path), str(OUTPUT_DIR), dpi=200,
                        use_ocr=False, requested_pages={page_num})

    img = Image.open(str(page_path))
    print("=" * 80)
    print(f"  TEST OCR PAGINA {page_num}")
    print(f"  Dimensioni: {img.width} x {img.height}")
    print("=" * 80)

    print("\n[STEP 1] Rilevamento vignette...")
    panels = detect_panels(img, page_num=page_num)
    print(f"  -> {len(panels)} vignette trovate\n")

    all_page_data = []
    debug_dir = OUTPUT_DIR / "debug_ocr_test"
    debug_dir.mkdir(parents=True, exist_ok=True)

    for i, panel in enumerate(panels):
        print(f"\n{'='*80}")
        print(f"  VIGNETTA {i+1}/{len(panels)}")
        print(f"  Posizione: ({panel.x}, {panel.y}) -> ({panel.x + panel.width}, {panel.y + panel.height})")
        print(f"  Dimensioni: {panel.width}x{panel.height}")
        print(f"{'='*80}")

        balloons = detect_balloons(panel.image,
                                    min_area_pct=0.003,
                                    max_area_pct=0.65,
                                    circularity_min=0.2)

        print(f"  Balloon rilevati: {len(balloons)}")
        print()

        panel_texts = []
        for j, b in enumerate(balloons):
            print(f"  Balloon #{j+1}:")
            print(f"    Pos: ({b.x}, {b.y}) -> ({b.x + b.width}, {b.y + b.height}) [{b.width}x{b.height}]")
            print(f"    Testo: \"{b.text}\"")
            print(f"    Confidenza: {b.confidence:.3f}")
            if b.text.strip():
                panel_texts.append(b.text.strip())
            print()

        combined = " | ".join(panel_texts) if panel_texts else "(NESSUN TESTO ESTRATTO)"
        print(f"  TESTO COMBINATO: \"{combined}\"")
        print()

        debug_path = _draw_panel_with_balloons(panel.image, balloons, i+1, page_num, debug_dir)
        print(f"  Debug image salvata: {debug_path}")

        print(f"\n  >>> OCR su TUTTA l'immagine del panel (non solo balloon)...")
        try:
            import easyocr
            reader = easyocr.Reader(["en", "it"], gpu=False)
            panel_np = np.array(panel.image.convert("RGB"))
            full_results = reader.readtext(panel_np, paragraph=False, detail=1)
            if full_results:
                print(f"  RISULTATI OCR COMPLETO:")
                for idx, (bbox, text, conf) in enumerate(full_results):
                    pts = [f"({int(p[0])},{int(p[1])})" for p in bbox]
                    print(f"    [{idx+1}] \"{text}\" (conf: {conf:.3f}) @ {', '.join(pts[:2])}")
            else:
                print(f"    (nessun testo rilevato su tutta l'immagine)")
        except Exception as e:
            print(f"    ERRORE OCR su tutta l'immagine: {e}")

        print()

        all_page_data.append({
            "panel": i+1,
            "bbox": f"({panel.x},{panel.y}) -> ({panel.x+panel.width},{panel.y+panel.height})",
            "balloons": [
                {
                    "pos": f"({b.x},{b.y}) -> ({b.x+b.width},{b.y+b.height})",
                    "text": b.text,
                    "conf": round(b.confidence, 3),
                }
                for b in balloons
            ],
            "combined_text": combined,
        })

    report = {
        "pagina": page_num,
        "file": page_path.name,
        "dimensioni": f"{img.width}x{img.height}",
        "vignette": len(panels),
        "dettaglio": all_page_data,
    }

    report_path = OUTPUT_DIR / f"page_{page_num:04d}_ocr_test.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport salvato: {report_path}")

    print("\n" + "=" * 80)
    print("  RIEPILOGO TESTO ESTRATTO PER VIGNETTA")
    print("=" * 80)
    for d in all_page_data:
        print(f"\n  Vignetta {d['panel']}:")
        for b in d['balloons']:
            if b['text']:
                print(f"    -> \"{b['text']}\" [{b['conf']:.2f}]")
        if not any(b['text'] for b in d['balloons']):
            print(f"    (nessun testo)")
