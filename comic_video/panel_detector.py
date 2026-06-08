"""
Modulo Rilevamento Pannelli — segmenta pagine fumetto in vignette individuali.

Algoritmo:
    1. Immagine → scala di grigi → soglia binaria adattiva
    2. Trova contorni → filtra per area minima → approssima a rettangoli
    3. Ordina per ordine di lettura (dall'alto verso il basso, da sinistra a destra)
    4. Ritaglia ogni pannello come immagine separata

Supporta:
    - Layout a griglia regolare
    - Layout irregolari (splash page, vignette sovrapposte)
    - Copertine e pagine intere (nessuna suddivisione)
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from comic_video.utils import log


@dataclass
class Panel:
    """Rappresenta un singolo pannello/vignetta di una pagina fumetto."""
    page_num: int
    panel_index: int       # Ordine di lettura (0-based)
    x: int                 # Coordinata X nell'immagine originale
    y: int                 # Coordinata Y nell'immagine originale
    width: int             # Larghezza in pixel
    height: int            # Altezza in pixel
    image: Image.Image     # Immagine ritagliata del pannello
    is_full_page: bool = False  # True se è una splash page / pagina intera
    page_width: int = 0        # Larghezza totale della pagina (per normalizzazione)
    page_height: int = 0       # Altezza totale della pagina (per normalizzazione)


def detect_panels(
    page_image: Image.Image,
    page_num: int,
    min_panel_area_pct: float = 0.015,
    max_panel_area_pct: float = 0.95,
    border_tolerance: int = 5,
    use_gutter_detection: bool = True,
) -> list[Panel]:
    """
    Rileva i pannelli in una pagina fumetto usando contour + gutter detection.

    Strategia doppia:
        1. Gutter detection: trova le linee bianche (gutter) che separano
           i pannelli — funziona bene su layout a griglia regolare.
        2. Contour detection: trova regioni scure delimitate da linee nere
           — funziona su layout irregolari.
        Combina i due approcci per robustezza.

    Args:
        page_image: Immagine PIL della pagina
        page_num: Numero della pagina (per metadata)
        min_panel_area_pct: Area minima di un pannello
        max_panel_area_pct: Area massima (sopra questa, è full-page)
        border_tolerance: Pixel per espandere i bordi
        use_gutter_detection: Se usare gutter detection (default: True)

    Returns:
        Lista di oggetti Panel ordinati per ordine di lettura
    """
    img_w, img_h = page_image.size
    total_area = img_w * img_h

    img_rgb = np.array(page_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # --- Gutter Detection (linee bianche tra i pannelli) ---
    gutter_rects = []
    if use_gutter_detection:
        gutter_rects = _detect_gutters(gray, img_w, img_h, page_num)

    # --- Contour Detection (regioni delimitate da linee nere) ---
    contour_rects = _detect_contour_panels(
        gray, img_w, img_h, total_area,
        min_panel_area_pct, max_panel_area_pct, border_tolerance,
    )

    # --- Combina i due approcci ---
    if gutter_rects and contour_rects:
        # Prendi quello con più pannelli (più accurato)
        if len(gutter_rects) >= len(contour_rects):
            rectangles = gutter_rects
        else:
            rectangles = contour_rects
    elif gutter_rects:
        rectangles = gutter_rects
    elif contour_rects:
        rectangles = contour_rects
    else:
        log(f"  Page {page_num}: no panels detected, treating as full page", "info")
        return [Panel(
            page_num=page_num, panel_index=0,
            x=0, y=0, width=img_w, height=img_h,
            image=page_image, is_full_page=True,
            page_width=img_w, page_height=img_h,
        )]

    # --- Unisci rettangoli sovrapposti ---
    merged = _merge_overlapping_rectangles(rectangles, total_area)

    # --- Se c'è un solo rettangolo che copre quasi tutta la pagina → full page ---
    if len(merged) == 1:
        _, _, _, _, area = merged[0]
        if area / total_area > max_panel_area_pct:
            return [Panel(
                page_num=page_num, panel_index=0,
                x=0, y=0, width=img_w, height=img_h,
                image=page_image, is_full_page=True,
                page_width=img_w, page_height=img_h,
            )]

    # --- Ordina per ordine di lettura (Y principale, X secondario) ---
    merged.sort(key=lambda r: (r[1], r[0]))

    # --- Ritaglia ogni pannello ---
    panels = []
    img_np = np.array(page_image.convert("RGB"))
    for i, (x, y, w, h, _) in enumerate(merged):
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))

        panel_np = img_np[y:y + h, x:x + w, :]
        panel_img = Image.fromarray(panel_np)
        is_full = (w * h) / total_area > max_panel_area_pct

        panels.append(Panel(
            page_num=page_num,
            panel_index=i,
            x=x, y=y, width=w, height=h,
            image=panel_img,
            is_full_page=is_full,
            page_width=img_w, page_height=img_h,
        ))

    method = "gutter+contour" if gutter_rects else "contour-only"
    log(f"  Page {page_num}: detected {len(panels)} panel(s) [{method}]", "success")
    return panels


def _detect_gutters(
    gray: np.ndarray,
    img_w: int,
    img_h: int,
    page_num: int,
) -> list[tuple[int, int, int, int, int]]:
    """
    Rileva i pannelli analizzando le linee bianche (gutter) tra di essi.

    Le gutter sono le strisce bianche orizzontali e verticali che
    separano le vignette nei fumetti.
    """
    # Soglia per trovare le regioni bianche (gutter)
    # Usa Otsu per adattarsi a diverse tonalità di carta
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Rileva linee orizzontali bianche (gutter orizzontali)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (img_w // 2, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

    # Rileva linee verticali bianche (gutter verticali)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, img_h // 2))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)

    # Combina le linee
    gutter_lines = cv2.bitwise_or(h_lines, v_lines)

    # Inverti: regioni NON gutter (cioè i pannelli)
    panel_regions = cv2.bitwise_not(gutter_lines)

    # Trova contorni delle regioni dei pannelli
    contours, _ = cv2.findContours(
        panel_regions, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )

    total_area = img_w * img_h
    min_area = total_area * 0.01
    max_area = total_area * 0.95

    rectangles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0
        if aspect < 0.1 or aspect > 10:
            continue

        # Espandi di 2px per coprire i bordi
        x = max(0, x - 2)
        y = max(0, y - 2)
        w = min(img_w - x, w + 4)
        h = min(img_h - y, h + 4)

        rectangles.append((x, y, w, h, w * h))

    return rectangles


def _detect_contour_panels(
    gray: np.ndarray,
    img_w: int,
    img_h: int,
    total_area: int,
    min_panel_area_pct: float,
    max_panel_area_pct: float,
    border_tolerance: int,
) -> list[tuple[int, int, int, int, int]]:
    """Rileva pannelli via contour detection standard."""
    # Adaptive threshold con parametri regolati
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 25, 3,
    )

    kernel_clean = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_clean)

    # Dilation per unire contorni vicini
    kernel_dilate = np.ones((5, 5), np.uint8)
    binary = cv2.dilate(binary, kernel_dilate, iterations=1)

    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return []

    min_area = total_area * min_panel_area_pct
    max_area = total_area * max_panel_area_pct

    rectangles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        x = max(0, x - border_tolerance)
        y = max(0, y - border_tolerance)
        w = min(img_w - x, w + 2 * border_tolerance)
        h = min(img_h - y, h + 2 * border_tolerance)

        rect_area = w * h
        if rect_area < min_area:
            continue

        aspect_ratio = w / h if h > 0 else 0
        if aspect_ratio < 0.1 or aspect_ratio > 10:
            continue

        rectangles.append((x, y, w, h, rect_area))

    return rectangles


def _merge_overlapping_rectangles(
    rectangles: list[tuple[int, int, int, int, int]],
    total_area: int,
    overlap_threshold: float = 0.3,
) -> list[tuple[int, int, int, int, int]]:
    """
    Unisce rettangoli che si sovrappongono significativamente.

    Questo gestisce vignette con bordi decorativi dove i contorni interni
    vengono rilevati come rettangoli separati.

    Args:
        rectangles: Lista di (x, y, w, h, area)
        total_area: Area totale dell'immagine
        overlap_threshold: Frazione di overlap per unire (default: 0.3 = 30%)

    Returns:
        Lista di rettangoli uniti
    """
    if not rectangles:
        return []

    # Ordina per area (decrescente)
    sorted_rects = sorted(rectangles, key=lambda r: r[4], reverse=True)
    merged = []
    used = [False] * len(sorted_rects)

    for i, (x1, y1, w1, h1, a1) in enumerate(sorted_rects):
        if used[i]:
            continue

        # Prova a unire con rettangoli più piccoli contenuti al suo interno
        current = [x1, y1, x1 + w1, y1 + h1]
        for j, (x2, y2, w2, h2, a2) in enumerate(sorted_rects):
            if i == j or used[j]:
                continue

            # Calcola intersezione
            ix = max(current[0], x2)
            iy = max(current[1], y2)
            ix2 = min(current[2], x2 + w2)
            iy2 = min(current[3], y2 + h2)

            if ix < ix2 and iy < iy2:
                inter_area = (ix2 - ix) * (iy2 - iy)
                # Se il rettangolo interno è dentro quello esterno
                if inter_area / min(a1, a2) > overlap_threshold:
                    # Espandi il rettangolo corrente per includere questo
                    current[0] = min(current[0], x2)
                    current[1] = min(current[1], y2)
                    current[2] = max(current[2], x2 + w2)
                    current[3] = max(current[3], y2 + h2)
                    used[j] = True

        merged.append((
            current[0], current[1],
            current[2] - current[0],
            current[3] - current[1],
            (current[2] - current[0]) * (current[3] - current[1]),
        ))
        used[i] = True

    return merged


def save_panels_debug(
    page_image: Image.Image,
    panels: list[Panel],
    output_dir: str,
    page_num: int,
) -> str:
    """
    Salva un'immagine di debug con i pannelli evidenziati.

    Args:
        page_image: Immagine originale della pagina
        panels: Lista dei pannelli rilevati
        output_dir: Directory di output
        page_num: Numero della pagina

    Returns:
        Path dell'immagine di debug salvata
    """
    img_np = np.array(page_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    # Disegna rettangoli colorati per ogni pannello
    colors = [
        (0, 255, 0),    # Verde
        (255, 0, 0),    # Blu
        (0, 0, 255),    # Rosso
        (255, 255, 0),  # Ciano
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Giallo
    ]

    for i, panel in enumerate(panels):
        color = colors[i % len(colors)]
        cv2.rectangle(
            img_bgr,
            (panel.x, panel.y),
            (panel.x + panel.width, panel.y + panel.height),
            color, 3,
        )
        # Numero del pannello
        cv2.putText(
            img_bgr, str(i + 1),
            (panel.x + 10, panel.y + 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3,
        )

    debug_path = Path(output_dir) / "debug_panels"
    debug_path.mkdir(parents=True, exist_ok=True)
    out_path = debug_path / f"page_{page_num:04d}_panels.png"

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(img_rgb).save(str(out_path))

    return str(out_path)
