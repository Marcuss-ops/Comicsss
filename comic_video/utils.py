"""
Utility condivise per i moduli comic-video-maker e comic-video-creator.

Contiene:
    - log()                    — Stampa colorata (rich) o plain
    - parse_page_range()       — Parsing range pagine "1-5,7,9-12"
    - load_and_scale_image()   — Carica immagine con zoom ridotto per foreground
    - load_blurred_background()— Crea sfondo blur cinematografico
    - image_to_base64()        — Converte PIL Image in base64
    - TEMP_DIR                 — Directory temporanea condivisa
"""

import io
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image as PILImage
from PIL import ImageFilter, ImageEnhance

# Rich (optional, for colored output)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Temporary directory for audio files and other temp data
TEMP_DIR = Path(tempfile.gettempdir()) / "comic_video"

# Supported image formats
IMAGE_FORMAT = "PNG"

# Max image dimension for LLM analysis (to save tokens)
MAX_IMAGE_SIZE = (2048, 2048)

# Output video defaults
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 24

# Zoom: 0.65 = mostra ~60% dell'altezza pagina — leggero zoom, elegante
ZOOM_SCALE = 0.65

# Raggio blur per lo sfondo (più basso = più leggero)
BLUR_RADIUS = 25

# Quanto scurire lo sfondo (0.0 = nero, 1.0 = originale)
BG_DARKEN = 0.65


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str, style: str = "info"):
    """Print a colored log message if rich is available, otherwise plain text."""
    safe_msg = msg.encode(
        sys.stdout.encoding or "utf-8", errors="replace"
    ).decode(sys.stdout.encoding or "utf-8", errors="replace")

    if console:
        try:
            if style == "header":
                console.print(Panel(safe_msg, style="bold magenta"))
            else:
                color_map = {
                    "info": "[bold cyan]>>[/]",
                    "success": "[bold green]OK[/]",
                    "warning": "[bold yellow]!![/]",
                    "error": "[bold red]XX[/]",
                }
                prefix = color_map.get(style, "[bold cyan]>>[/]")
                console.print(f"{prefix} {safe_msg}")
        except (UnicodeEncodeError, UnicodeError):
            print(f"  [{style.upper()}] {safe_msg}")
    else:
        print(f"  [{style.upper()}] {safe_msg}")


# ---------------------------------------------------------------------------
# Page range parser
# ---------------------------------------------------------------------------

def parse_page_range(range_str: str, total_pages: int) -> list[int]:
    """
    Parse a page range string like '1-10' or '1,3,5-7'.

    Args:
        range_str: String like "1-5", "1,3,5-7", "1-10"
        total_pages: Maximum page number

    Returns:
        Sorted list of page numbers
    """
    pages = set()
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start = int(start.strip())
            end = int(end.strip())
            pages.update(range(max(1, start), min(total_pages, end) + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------

def image_to_base64(image: PILImage.Image) -> str:
    """Convert a PIL Image to base64-encoded PNG string."""
    buf = io.BytesIO()
    image.save(buf, format=IMAGE_FORMAT)
    import base64
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def resize_image_if_needed(image: PILImage.Image) -> PILImage.Image:
    """Resize image if it exceeds MAX_IMAGE_SIZE (to save tokens for LLM)."""
    w, h = image.size
    max_w, max_h = MAX_IMAGE_SIZE
    if w > max_w or h > max_h:
        ratio = min(max_w / w, max_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        image = image.resize((new_w, new_h), PILImage.LANCZOS)
        log(f"  Image resized to {new_w}x{new_h} (was {w}x{h})", "info")
    return image


def load_and_scale_image(
    image_path: str,
    target_w: int = VIDEO_WIDTH,
    target_h: int = VIDEO_HEIGHT,
) -> tuple[np.ndarray, int, int]:
    """
    Load a comic page image and scale it for the FOREGROUND layer.

    Uses a reduced zoom (ZOOM_SCALE) so more of the page is visible.
    The image is scaled to FILL (cover) the frame, then ZOOM_SCALE is
    applied to pull back and show the full comic panels.

    For a portrait comic page (1200x1800) at 1920x1080:
        - Cover scale: 1.6 → 1920x2880
        - Effective scale with ZOOM_SCALE=0.55: 0.88 → 1056x1584
        - Shows ~68% of the page height at a time
        - Remaining sides filled by blurred background

    Returns:
        Tuple of (numpy_array, actual_width, actual_height)
    """
    pil_img = PILImage.open(image_path).convert("RGB")
    orig_w, orig_h = pil_img.size

    # Scale to FILL the frame (cover), then reduce with ZOOM_SCALE
    cover_scale = max(target_w / orig_w, target_h / orig_h)
    scale = cover_scale * ZOOM_SCALE

    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)
    img_array = np.array(pil_img)
    pil_img.close()

    return img_array, new_w, new_h


def load_blurred_background(
    image_path: str,
    target_w: int = VIDEO_WIDTH,
    target_h: int = VIDEO_HEIGHT,
    blur_radius: int = BLUR_RADIUS,
    darken: float = BG_DARKEN,
) -> np.ndarray:
    """
    Load an image and create a cinematic blurred background.

    The image is scaled to FILL the frame (cover), center-cropped,
    heavily blurred, and slightly darkened. This creates a depth
    effect behind the scrolling page foreground.

    Returns:
        Numpy array of shape (target_h, target_w, 3)
    """
    pil_img = PILImage.open(image_path).convert("RGB")
    orig_w, orig_h = pil_img.size

    # Scale to fill the frame (cover) — super zoomata
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)

    # Center-crop to target dimensions
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    pil_img = pil_img.crop((left, top, left + target_w, top + target_h))

    # Heavy blur for cinematic look
    pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Darken slightly for better foreground contrast
    if darken < 1.0:
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(darken)

    img_array = np.array(pil_img)
    pil_img.close()

    return img_array


def extract_comic_title_from_filename(filename: str) -> str:
    """
    Extract a readable comic title from the PDF filename.

    Examples:
        '4fumetti-ita-batman-the-killing-joke-dc.pdf' -> 'Batman the Killing Joke'
        'spider-man-2099-ita.pdf' -> 'Spider Man 2099'
    """
    stem = Path(filename).stem
    name = stem

    # Remove common prefixes
    import re
    name = re.sub(r'^[\d]*fumetti[-_]*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^ita[-_]', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]dc$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]eng$', '', name, flags=re.IGNORECASE)

    # Replace separators with spaces
    name = name.replace('-', ' ').replace('_', ' ')

    # Capitalize words (keep articles lowercase)
    stop_words = {'the', 'a', 'an', 'of', 'in', 'and'}
    words = name.split()
    capitalized = []
    for i, w in enumerate(words):
        if w.lower() in stop_words and i > 0:
            capitalized.append(w.lower())
        else:
            capitalized.append(w.capitalize())

    return ' '.join(capitalized).strip() or Path(filename).stem


def find_pdf(base_dir: Path, default_name: str = "comic.pdf") -> Path:
    """
    Search for a PDF file in base_dir or its parent.

    Priority:
        1. A file named <default_name> in base_dir
        2. Any *.pdf found in base_dir (warn if multiple)
        3. Any *.pdf found in base_dir.parent (warn if multiple)
        4. Fallback to base_dir / <default_name>

    Returns:
        Path to the chosen PDF (may not exist if fallback is used).
    """
    default = base_dir / default_name
    if default.exists():
        return default

    for d in (base_dir, base_dir.parent):
        pdfs = sorted(d.glob("*.pdf"))
        if pdfs:
            if len(pdfs) > 1:
                names = ", ".join(p.name for p in pdfs)
                log(f"Multiple PDFs found in {d}: {names}. Using: {pdfs[0].name}", "warning")
            return pdfs[0]

    return default


def print_summary_table(title: str, rows: list[tuple[str, str]]):
    """Print a summary table using rich or plain text."""
    if RICH_AVAILABLE:
        table = Table(title=title, style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        for key, val in rows:
            table.add_row(key, val)
        console.print(table)
    else:
        print(f"\n=== {title.upper()} ===")
        for key, val in rows:
            print(f"{key}: {val}")
