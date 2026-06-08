"""
Comic Video — Moduli condivisi per analisi e creazione video di fumetti.

Moduli:
    - utils.py          : Utility generiche (log, immagini, range)
    - ollama.py         : Chiamate API Ollama + prompt narrativi
    - extractor.py      : Estrazione pagine PDF + OCR (EasyOCR)
    - panel_detector.py : Rilevamento vignette con OpenCV
    - analyzer.py       : Analisi vignette via LLM vision + sintesi script
"""

from .utils import (
    RICH_AVAILABLE,
    console,
    TEMP_DIR,
    IMAGE_FORMAT,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    ZOOM_SCALE,
    BLUR_RADIUS,
    BG_DARKEN,
    log,
    parse_page_range,
    image_to_base64,
    resize_image_if_needed,
    load_and_scale_image,
    load_blurred_background,
    extract_comic_title_from_filename,
    print_summary_table,
)

from .ollama import (
    call_ollama,
    PANEL_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
    parse_json_response,
    parse_synthesis_json,
    DEFAULT_OLLAMA_URL,
)

from .extractor import (
    extract_pdf_pages,
    EASYOCR_AVAILABLE,
)

from .panel_detector import (
    detect_panels,
    Panel,
    save_panels_debug,
)

from .balloon_detector import (
    detect_balloons,
    detect_balloons_in_panel,
    Balloon,
    save_balloon_debug,
)

from .analyzer import (
    analyze_panel,
    analyze_page_panels,
    analyze_full_page,
    synthesize_script,
    synthesize_scene_json,
)

from .ollama import (
    SCENE_SYNTHESIS_PROMPT,
)

__all__ = [
    "RICH_AVAILABLE", "console", "TEMP_DIR", "IMAGE_FORMAT",
    "VIDEO_WIDTH", "VIDEO_HEIGHT", "VIDEO_FPS",
    "ZOOM_SCALE", "BLUR_RADIUS", "BG_DARKEN",
    "log", "parse_page_range", "image_to_base64",
    "resize_image_if_needed", "load_and_scale_image",
    "load_blurred_background", "extract_comic_title_from_filename",
    "print_summary_table",
    "call_ollama", "PANEL_PROMPT",
    "FINAL_SYNTHESIS_PROMPT", "SCENE_SYNTHESIS_PROMPT",
    "parse_json_response", "parse_synthesis_json",
    "DEFAULT_OLLAMA_URL",
    "extract_pdf_pages", "EASYOCR_AVAILABLE",
    "detect_panels", "Panel", "save_panels_debug",
    "detect_balloons", "detect_balloons_in_panel", "Balloon", "save_balloon_debug",
    "analyze_panel", "analyze_page_panels", "analyze_full_page",
    "synthesize_script", "synthesize_scene_json",
]
