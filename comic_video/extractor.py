"""
Modulo Estrazione PDF — estrae pagine, testo e OCR da PDF di fumetti.

Contiene:
    - extract_pdf_pages() — Estrae pagine come immagini + testo (PDF + OCR)
    - extract_text_ocr()   — OCR su immagine via EasyOCR
"""

import os
from pathlib import Path
from typing import Optional

import fitz
from PIL import Image

from comic_video.utils import log, resize_image_if_needed

# EasyOCR (optional — install separately)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    _ocr_reader = None  # lazy init
except ImportError:
    EASYOCR_AVAILABLE = False
    _ocr_reader = None


def get_ocr_reader() -> Optional[object]:
    """Get or initialize EasyOCR reader (lazy)."""
    global _ocr_reader
    if not EASYOCR_AVAILABLE:
        return None
    if _ocr_reader is None:
        log("    Initializing EasyOCR (first load may take time)...", "info")
        _ocr_reader = easyocr.Reader(["en", "it"], gpu=False)
    return _ocr_reader


def extract_text_ocr(image_path: str) -> str:
    """
    Extract text from a page image using EasyOCR.
    Used as fallback when PDF has no selectable text (scanned comics).

    Filters out low-confidence results (< 0.5) to avoid garbage text.
    Sorts by top-to-bottom, left-to-right reading order.
    """
    global _ocr_reader
    reader = get_ocr_reader()
    if reader is None:
        return ""

    try:
        # detail=1 returns [(bbox, text, conf), ...]; no paragraph to keep individual boxes sortable
        results = reader.readtext(image_path, paragraph=False, detail=1)
        if not results:
            return ""

        # Filter low-confidence results (comic fonts often fool OCR)
        filtered = [(bbox, text, conf) for bbox, text, conf in results if conf >= 0.5]
        # Sort by vertical position (top-to-bottom), then horizontal (left-to-right)
        filtered.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
        texts = [r[1] for r in filtered]
        joined = "\n".join(texts)

        # Log how much we filtered
        kept = len(filtered)
        total = len(results)
        if total > 0 and kept < total:
            log(f"    OCR confidence filter: kept {kept}/{total} text blocks", "info")

        return joined
    except Exception as e:
        log(f"    OCR warning: {e}", "warning")
        return ""


def extract_pdf_pages(
    pdf_path: str,
    output_dir: str,
    dpi: int = 200,
    use_ocr: bool = True,
    requested_pages: Optional[set[int]] = None,
) -> list[dict]:
    """
    Extract each page of a PDF as an image file + text content.

    CACHING: if the PNG file already exists, skip re-rendering and load from disk.
    Text extraction (PDF text + OCR) is always re-run since it's fast.

    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory (images go to {output_dir}/pages/)
        dpi: Image resolution
        use_ocr: Run EasyOCR on pages without selectable PDF text
        requested_pages: Optional set of page numbers to extract (1-indexed).
                         If None, extract ALL pages.

    Returns:
        List of dicts: [{page_num, path, image, page_text, ocr_text}, ...]
    """
    log(f"Opening PDF: {pdf_path}", "info")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    log(f"Total pages: {total_pages}", "info")

    pages_dir = Path(output_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Determine which pages to extract
    if requested_pages is not None:
        to_extract = sorted(p for p in requested_pages if 1 <= p <= total_pages)
        log(f"Extracting {len(to_extract)} requested pages", "info")
    else:
        to_extract = list(range(1, total_pages + 1))

    # Check which images are already cached
    cached_count = 0
    rendered_count = 0

    extracted = []
    for page_num in to_extract:
        try:
            img_path = pages_dir / f"page_{page_num:04d}.png"

            # CACHE HIT: image already exists, skip rendering
            if img_path.exists():
                cached_count += 1
            else:
                # CACHE MISS: render page to PNG
                page = doc.load_page(page_num - 1)  # fitz is 0-indexed
                zoom = dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                pix.save(str(img_path))
                rendered_count += 1

            # Always load image from disk (whether cached or freshly rendered)
            img = Image.open(str(img_path))
            img = resize_image_if_needed(img)

            # Text extraction: always re-run from PDF (fast, no rendering)
            # Need to open page to extract text
            page = doc.load_page(page_num - 1)
            pdf_text = page.get_text("text").strip()

            # OCR only if no PDF text
            ocr_text = ""
            if not pdf_text and use_ocr:
                log(f"  Page {page_num}: no PDF text, running OCR...", "info")
                ocr_text = extract_text_ocr(str(img_path))

            extracted.append({
                "page_num": page_num,
                "path": str(img_path),
                "image": img,
                "page_text": pdf_text,
                "ocr_text": ocr_text,
            })

            source = f"OCR ({len(ocr_text)} chars)" if ocr_text else (
                f"PDF ({len(pdf_text)} chars)" if pdf_text else "no text"
            )
            status = "cached" if img_path.exists() else "rendered"
            log(f"  Page {page_num}/{total_pages} — text: {source} [{status}]", "info")

        except Exception as e:
            log(f"  Warning: could not extract page {page_num}: {e}", "warning")
            try:
                img_path = pages_dir / f"page_{page_num:04d}.png"
                if not img_path.exists():
                    page = doc.load_page(page_num - 1)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
                    pix.save(str(img_path))
                img = Image.open(str(img_path))
                extracted.append({
                    "page_num": page_num,
                    "path": str(img_path),
                    "image": img,
                    "page_text": "",
                    "ocr_text": "",
                })
                log(f"  Page {page_num} extracted at low DPI (fallback)", "info")
            except Exception as e2:
                log(f"  Skipping page {page_num}: {e2}", "error")

    doc.close()

    # Summary
    cache_info = f" ({cached_count} cached, {rendered_count} fresh)" if cached_count else ""
    log(f"Extracted {len(extracted)} pages to {pages_dir}{cache_info}", "success")
    return extracted
