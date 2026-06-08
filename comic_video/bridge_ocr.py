#!/usr/bin/env python3
"""
Bridge OCR — logica di rilevazione pannelli e balloon.
Può essere usato come modulo (run_ocr) o come CLI standalone.
"""

import sys
import json
import traceback
import io
from pathlib import Path
from contextlib import redirect_stdout
from typing import Any

# Aggiungi il path del progetto per importare comic_video
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
from comic_video.panel_detector import detect_panels
from comic_video.balloon_detector import detect_balloons_in_panel


def run_ocr(img_path: str) -> dict[str, Any]:
    """
    Run panel and balloon detection on a single image.

    Returns a dict with:
        - page_width, page_height, panel_count, panels
        - or {error, traceback} on failure.
    """
    if not Path(img_path).exists():
        return {"error": f"File not found: {img_path}"}

    try:
        img = Image.open(img_path)

        # Redirect stdout during detection to prevent log pollution
        stdout_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer):
            panels = detect_panels(img, page_num=1)

            result_panels = []
            for i, panel in enumerate(panels):
                balloons, combined_text = detect_balloons_in_panel(panel.image)
                result_panels.append({
                    "panel_index": i,
                    "x": panel.x,
                    "y": panel.y,
                    "width": panel.width,
                    "height": panel.height,
                    "is_full_page": panel.is_full_page,
                    "balloons": [
                        {
                            "x": b.x,
                            "y": b.y,
                            "width": b.width,
                            "height": b.height,
                            "text": b.text,
                            "confidence": b.confidence,
                        }
                        for b in balloons
                    ],
                    "combined_text": combined_text,
                })

        return {
            "page_width": img.width,
            "page_height": img.height,
            "panel_count": len(panels),
            "panels": result_panels,
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python bridge_ocr.py <image_path>"}, ensure_ascii=False))
        sys.exit(1)

    result = run_ocr(sys.argv[1])
    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
