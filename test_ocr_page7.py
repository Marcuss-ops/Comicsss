#!/usr/bin/env python3
"""
Test approfondito OCR su pagina 7: mostra TUTTI i balloon rilevati,
TUTTO il testo OCR estratto, e genera immagini debug per confronto visivo.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cv2
import numpy as np
from PIL import Image

from comic_video.panel_detector import detect_panels
from comic_video.balloon_detector import detect_balloons, Balloon, save_balloon_debug
from comic_video.utils import log

# Fix encoding per Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def draw_panel_with_balloons(panel_image, balloons, panel_num, page_num):
    """Disegna TUTTI i balloon su una copia dell'immagine con numeri e testo."""
    img_np = np.array(panel_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    for i, b in enumerate(balloons):
        # Colore diverso per ogni balloon
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

    debug_dir = Path(__file__).parent / "output" / "debug_ocr_test"
    debug_dir.mkdir(parents=True, exist_ok=True)
    out = debug_dir / f"page{page_num:04d}_panel{panel_num:02d}_debug.png"
    cv2.imwrite(str(out), img_bgr)
    return out

def main():
    page_num = 7
    page_path = Path(__file__).parent / "output" / "pages" / f"page_{page_num:04d}.png"

    if not page_path.exists():
        print(f"ERRORE: {page_path} non trovata. Estrai prima la pagina.")
        # Estrai dal PDF
        from comic_video.extractor import extract_pdf_pages
        pdf_path = r"C:\Users\pater\Pyt\comics\comic-pdf-video-maker\4fumetti-ita-batman-the-killing-joke-dc.pdf"
        extract_pdf_pages(pdf_path, str(Path(__file__).parent / "output"), dpi=200,
                        use_ocr=False, requested_pages={page_num})

    img = Image.open(str(page_path))
    print("=" * 80)
    print(f"  TEST OCR PAGINA {page_num}")
    print(f"  Dimensioni: {img.width} x {img.height}")
    print("=" * 80)

    # Step 1: Panel detection
    print("\n[STEP 1] Rilevamento vignette...")
    panels = detect_panels(img, page_num=page_num)
    print(f"  -> {len(panels)} vignette trovate\n")

    all_page_data = []

    for i, panel in enumerate(panels):
        print(f"\n{'='*80}")
        print(f"  VIGNETTA {i+1}/{len(panels)}")
        print(f"  Posizione: ({panel.x}, {panel.y}) -> ({panel.x + panel.width}, {panel.y + panel.height})")
        print(f"  Dimensioni: {panel.width}x{panel.height}")
        print(f"{'='*80}")

        # Balloon detection RAW
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

        # Salva debug image
        debug_path = draw_panel_with_balloons(panel.image, balloons, i+1, page_num)
        print(f"  Debug image salvata: {debug_path}")

        # Prova OCR su TUTTA l'immagine del panel (non solo balloon)
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

    # Salva report JSON
    report = {
        "pagina": page_num,
        "file": page_path.name,
        "dimensioni": f"{img.width}x{img.height}",
        "vignette": len(panels),
        "dettaglio": all_page_data,
    }

    report_path = Path(__file__).parent / "output" / f"page_{page_num:04d}_ocr_test.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport salvato: {report_path}")

    # Riepilogo finale
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

if __name__ == "__main__":
    main()
