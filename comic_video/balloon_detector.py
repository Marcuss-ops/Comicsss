"""
Modulo Rilevamento Balloon — trova i fumetti (balloon) in una vignetta
e ne estrae il testo tramite EasyOCR.

Algoritmo:
    1. Trova regioni bianche/chiare di forma ovale/rettangolare (balloon)
    2. Per ogni balloon, applica OCR (EasyOCR) per estrarre il testo
    3. Ordina i balloon per ordine di lettura (dall'alto, sinistra→destra)
    4. Restituisce il testo estratto con bounding box

Strategia:
    Invece di affidarsi alla capacità del LLM di leggere i balloon
    (spesso imprecisa), estraiamo il testo con OCR prima e lo passiamo
    come dato affidabile nel prompt.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from comic_video.utils import log


@dataclass
class Balloon:
    """Rappresenta un balloon (fumetto) rilevato."""
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    confidence: float = 0.0


# EasyOCR (lazy init, condiviso con extractor)
_ocr_reader = None


def _get_ocr_reader():
    """Get or initialize EasyOCR reader (lazy, shared)."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(["en", "it"], gpu=False)
        except ImportError:
            log("  EasyOCR not installed. Install with: pip install easyocr", "warning")
            return None
    return _ocr_reader


def detect_balloons(
    panel_image: Image.Image,
    min_area_pct: float = 0.005,
    max_area_pct: float = 0.60,
    circularity_min: float = 0.3,
) -> list[Balloon]:
    """
    Rileva balloon (fumetti) in una vignetta usando contour detection.

    I balloon sono tipicamente:
    - Bianchi o di colore chiaro
    - Forma ovale o rettangolare con angoli arrotondati
    - Contorno nero ben definito
    - Posizionati nella parte superiore della vignetta

    Args:
        panel_image: Immagine PIL della vignetta
        min_area_pct: Area minima del balloon (frazione area vignetta)
        max_area_pct: Area massima del balloon
        circularity_min: Circolarità minima (0.0 = linea, 1.0 = cerchio perfetto)

    Returns:
        Lista di Balloon ordinati per ordine di lettura (Y, poi X)
    """
    img_w, img_h = panel_image.size
    total_area = img_w * img_h

    # Converti in numpy
    img_np = np.array(panel_image.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # --- Preprocessing per balloon ---
    # 1. Sfoca leggermente per ridurre il rumore del tratto a matita
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Soglia binaria: balloon bianchi su sfondo scuro
    #    Usa Otsu per adattarsi a diverse tonalità di carta
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Operazioni morfologiche per chiudere contorni dei balloon
    kernel_close = np.ones((7, 7), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)

    # 4. Rimuovi piccoli punti di rumore
    kernel_open = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)

    # --- Trova contorni ---
    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return []

    min_area = total_area * min_area_pct
    max_area = total_area * max_area_pct

    balloons = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        # Calcola circolarità: 4π * area / perimetro²
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)

        # I balloon hanno circolarità media (ovali/rettangoli arrotondati)
        if circularity < circularity_min:
            continue

        # Approximate to rectangle
        x, y, w, h = cv2.boundingRect(cnt)

        # Filtra proporzioni strane (balloon non troppo stretti)
        aspect = w / h if h > 0 else 0
        if aspect < 0.3 or aspect > 3.5:
            continue

        # Espandi leggermente per includere il bordo
        pad = 3
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img_w - x, w + 2 * pad)
        h = min(img_h - y, h + 2 * pad)

        balloons.append(Balloon(x=x, y=y, width=w, height=h))

    # --- Unisci balloon sovrapposti (stesso fumetto, contorni multipli) ---
    balloons = _merge_overlapping_balloons(balloons)

    # --- Ordina per lettura: Y (dall'alto), poi X (sinistra→destra) ---
    balloons.sort(key=lambda b: (b.y, b.x))

    # --- Applica OCR su ogni balloon ---
    _apply_ocr_to_balloons(balloons, img_np)

    return balloons


def _merge_overlapping_balloons(
    balloons: list[Balloon],
    overlap_threshold: float = 0.4,
) -> list[Balloon]:
    """Unisce balloon che si sovrappongono significativamente."""
    if not balloons:
        return []

    merged = []
    used = [False] * len(balloons)

    for i, b1 in enumerate(balloons):
        if used[i]:
            continue

        current = Balloon(
            x=b1.x, y=b1.y,
            width=b1.width, height=b1.height,
        )

        for j, b2 in enumerate(balloons):
            if i == j or used[j]:
                continue

            # Calcola intersezione
            ix = max(current.x, b2.x)
            iy = max(current.y, b2.y)
            ix2 = min(current.x + current.width, b2.x + b2.width)
            iy2 = min(current.y + current.height, b2.y + b2.height)

            if ix < ix2 and iy < iy2:
                inter_area = (ix2 - ix) * (iy2 - iy)
                area_b2 = b2.width * b2.height
                if area_b2 > 0 and inter_area / area_b2 > overlap_threshold:
                    # Espandi per includere b2
                    current.x = min(current.x, b2.x)
                    current.y = min(current.y, b2.y)
                    current.width = max(current.x + current.width, b2.x + b2.width) - current.x
                    current.height = max(current.y + current.height, b2.y + b2.height) - current.y
                    used[j] = True

        merged.append(current)
        used[i] = True

    return merged


def _apply_ocr_to_balloons(
    balloons: list[Balloon],
    panel_np: np.ndarray,
):
    """Applica EasyOCR a ogni balloon rilevato."""
    reader = _get_ocr_reader()
    if reader is None:
        return

    for balloon in balloons:
        # Ritaglia la regione del balloon dall'immagine
        x2 = min(balloon.x + balloon.width, panel_np.shape[1])
        y2 = min(balloon.y + balloon.height, panel_np.shape[0])
        if balloon.y >= y2 or balloon.x >= x2:
            continue

        bbox_img = panel_np[balloon.y:y2, balloon.x:x2]

        if bbox_img.size == 0:
            continue

        # Converti in PIL per EasyOCR
        bbox_pil = Image.fromarray(bbox_img)

        # Salva temporaneamente (EasyOCR vuole un path o array)
        try:
            results = reader.readtext(np.array(bbox_pil), paragraph=False, detail=1)
            if results:
                # Prendi il testo con confidence più alta
                best = max(results, key=lambda r: r[2])
                balloon.text = best[1]
                balloon.confidence = best[2]
        except Exception as e:
            log(f"    OCR warning on balloon: {e}", "warning")


def _run_ocr_on_full_image(
    panel_image: Image.Image,
) -> list[Balloon]:
    """
    Fallback: esegue OCR sull'IMMAGINE INTERA del panel quando
    il contour detection dei balloon fallisce (tipico di fumetti
    con stili di disegno scuri o texture che confondono Otsu).

    Divide l'immagine in fasce orizzontali e cerca testo in ognuna,
    poi unisce i risultati in ordine di lettura.

    Args:
        panel_image: Immagine PIL del panel

    Returns:
        Lista di Balloon con testo OCR
    """
    reader = _get_ocr_reader()
    if reader is None:
        return []

    img_np = np.array(panel_image.convert("RGB"))
    h, w = img_np.shape[:2]

    try:
        # OCR su tutta l'immagine
        results = reader.readtext(img_np, paragraph=False, detail=1, min_size=5)
        if not results:
            return []

        balloons = []
        for bbox, text, conf in results:
            if conf < 0.15:  # Filtro confidence molto bassa
                continue
            if len(text.strip()) < 2:
                continue

            # Estrai bounding box dal risultato EasyOCR
            pts = np.array(bbox, dtype=np.int32)
            x = int(np.min(pts[:, 0]))
            y = int(np.min(pts[:, 1]))
            x2 = int(np.max(pts[:, 0]))
            y2 = int(np.max(pts[:, 1]))

            balloons.append(Balloon(
                x=max(0, x - 2),
                y=max(0, y - 2),
                width=min(w - x, x2 - x + 4),
                height=min(h - y, y2 - y + 4),
                text=text.strip(),
                confidence=conf,
            ))

        # Ordina per lettura: Y (dall'alto), poi X (sinistra→destra)
        balloons.sort(key=lambda b: (b.y, b.x))
        return balloons

    except Exception as e:
        log(f"    Full-image OCR fallback error: {e}", "warning")
        return []


def detect_balloons_in_panel(
    panel_image: Image.Image,
) -> tuple[list[Balloon], str]:
    """
    Rileva balloon in una vignetta e restituisce i testi OCR.

    STRATEGIA A DUE STADI:
    1. Prima prova con contour detection (balloon bianchi)
    2. Se non trova testo, FALLBACK: OCR su tutta l'immagine
       (utile per stili di disegno scuri o texture)

    Args:
        panel_image: Immagine PIL della vignetta

    Returns:
        Tuple di (lista_balloon, testo_combinato)
        dove testo_combinato è il testo di TUTTI i balloon unito,
        pronto per essere passato al prompt LLM.
    """
    # Stadio 1: Contour detection (balloon classici bianchi)
    balloons = detect_balloons(panel_image)
    texts = [b.text.strip() for b in balloons if b.text.strip()]

    # Stadio 2: Se contour non ha trovato testo, prova OCR su tutta l'immagine
    if not texts:
        balloons = _run_ocr_on_full_image(panel_image)
        texts = [b.text.strip() for b in balloons if b.text.strip()]
        if texts:
            log(f"      Full-image OCR fallback attivato: {len(texts)} testo/i trovato/i", "info")

    combined = "\n".join(texts) if texts else ""
    return balloons, combined


def save_balloon_debug(
    panel_image: Image.Image,
    balloons: list[Balloon],
    output_dir: str,
    page_num: int,
    panel_num: int,
) -> str:
    """
    Salva un'immagine di debug con i balloon evidenziati e testi OCR.

    Args:
        panel_image: Immagine della vignetta
        balloons: Lista balloon rilevati
        output_dir: Directory output
        page_num: Numero pagina
        panel_num: Numero pannello

    Returns:
        Path dell'immagine di debug
    """
    img_np = np.array(panel_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    for i, balloon in enumerate(balloons):
        # Rettangolo blu per balloon
        cv2.rectangle(
            img_bgr,
            (balloon.x, balloon.y),
            (balloon.x + balloon.width, balloon.y + balloon.height),
            (255, 0, 0), 2,
        )
        # Testo OCR sopra il balloon (con sfondo per leggibilità)
        if balloon.text:
            label = f"{i+1}: {balloon.text[:50]}"
            label_x = balloon.x
            label_y = max(15, balloon.y - 5)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            # Sfondo nero semitrasparente per il testo
            cv2.rectangle(
                img_bgr,
                (label_x - 2, label_y - th - 2),
                (label_x + tw + 2, label_y + 2),
                (0, 0, 0), -1,
            )
            cv2.putText(
                img_bgr, label,
                (label_x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
            )

    debug_path = Path(output_dir) / "debug_balloons"
    debug_path.mkdir(parents=True, exist_ok=True)
    out_path = debug_path / f"page_{page_num:04d}_panel{panel_num:02d}_balloons.png"

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(img_rgb).save(str(out_path))

    return str(out_path)
