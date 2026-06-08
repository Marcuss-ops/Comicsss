"""
Modulo Analisi — analizza pannelli (vignette) di fumetti tramite Ollama vision.

NON usa più il "sliding context" tra pagine, che causava allucinazioni.
Ogni vignetta viene analizzata INDIPENDENTEMENTE basandosi SOLO sull'immagine.

Contiene:
    - analyze_panel()        — Analisi singola vignetta
    - analyze_page_panels()  — Analisi di TUTTI i pannelli di una pagina
    - synthesize_script()    — Sintesi script video finale
"""

import json
from itertools import groupby
from typing import Optional

from comic_video.utils import log, image_to_base64
from comic_video.ollama import (
    call_ollama,
    PANEL_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
    parse_json_response,
    parse_synthesis_json,
    DEFAULT_OLLAMA_URL,
)
from comic_video.panel_detector import Panel
from comic_video.balloon_detector import detect_balloons_in_panel, Balloon, save_balloon_debug


# ---------------------------------------------------------------------------
# Single panel analysis
# ---------------------------------------------------------------------------

def analyze_panel(
    model: str,
    panel: Panel,
    total_panels: int,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 300,
    comic_title: str = "",
    use_balloon_ocr: bool = True,
    debug_balloons: bool = False,
    debug_dir: str = "",
    precomputed_balloons: Optional[list] = None,
    precomputed_text: str = "",
) -> dict:
    """
    Analizza UNA singola vignetta con il modello vision.

    INTEGRAZIONE BALLOON: prima di chiamare il LLM, rileva i balloon
    con OpenCV e ne estrae il testo con EasyOCR. Il testo OCR viene
    passato nel prompt come "dialogo affidabile", così il LLM non
    deve leggere i balloon (operazione in cui spesso fallisce).

    Args:
        model: Nome del modello Ollama (es. "llava:13b")
        panel: Oggetto Panel da analizzare
        total_panels: Numero totale di pannelli nella pagina
        comic_title: Titolo del fumetto
        use_balloon_ocr: Se True, rileva balloon e passa OCR nel prompt
        debug_balloons: Se True, salva immagini debug con balloon evidenziati
        debug_dir: Directory per immagini debug
        precomputed_balloons: Balloon già rilevati (evita doppia detection)
        precomputed_text: Testo OCR già estratto

    Returns:
        Dict con analisi strutturata della vignetta + testo OCR
    """
    page_num = panel.page_num
    panel_num = panel.panel_index + 1

    # Posizione descrittiva
    pos_x = "sinistra" if panel.x < 0.3 else "destra" if panel.x > 0.7 else "centro"
    pos_y = "alto" if panel.y < 0.3 else "basso" if panel.y > 0.7 else "centro"
    if pos_x == "centro" and pos_y == "centro":
        position = "centrale"
    else:
        position = f"{pos_y}-{pos_x}"

    # --- Balloon detection + OCR (usa precomputed se disponibili) ---
    balloon_text = precomputed_text
    balloons = precomputed_balloons if precomputed_balloons is not None else []

    if use_balloon_ocr and precomputed_balloons is None:
        # Solo se non abbiamo già i precomputed da analyze_page_panels
        balloons, balloon_text = detect_balloons_in_panel(panel.image)
        if balloon_text:
            log(f"      Balloon OCR: {len(balloons)} balloon(s)", "info")

        # Debug balloons
        if debug_balloons and debug_dir and balloons:
            bdebug_path = save_balloon_debug(
                panel.image, balloons, debug_dir, page_num, panel_num,
            )
            log(f"      Balloon debug: {bdebug_path}", "info")

    # Converti immagine a base64
    b64_image = image_to_base64(panel.image)

    # Costruisci prompt con OCR text
    ocr_display = balloon_text if balloon_text else "(nessun balloon rilevato)"
    prompt = PANEL_PROMPT.format(
        comic_title=comic_title,
        page_num=page_num,
        panel_num=panel_num,
        total_panels=total_panels,
        position=position,
        ocr_text=ocr_display,
    )

    log(f"    Analyzing panel {panel_num}/{total_panels} (page {page_num})...", "info")

    try:
        response_text = call_ollama(
            model=model,
            prompt=prompt,
            images=[b64_image],
            ollama_url=ollama_url,
            timeout=timeout,
            temperature=0.1,
        )

        result = parse_json_response(response_text, page_num)
        return {
            "page_num": page_num,
            "panel_num": panel_num,
            "total_panels": total_panels,
            "tipo": result.get("tipo", result.get("tipo_pagina", "fumetto")),
            "titolo": result.get("titolo", result.get("titolo_scena", f"Pagina {page_num}, Vignetta {panel_num}")),
            "descrizione": result.get("descrizione", result.get("descrizione_narrativa", "")),
            "personaggi": result.get("personaggi", ""),
            "dialoghi": balloon_text or result.get("dialoghi", ""),  # Prefer OCR text!
            "dialoghi_ocr": balloon_text,  # Nuovo campo: testo OCR originale
            "balloon_count": len(balloons),
            "effetto_sonoro": result.get("effetto_sonoro", ""),
            "ambientazione": result.get("ambientazione", ""),
            "durata_stimata": result.get("durata_stimata", 15),
            "panel_bbox": {
                "x": panel.x, "y": panel.y,
                "width": panel.width, "height": panel.height,
            },
            "is_full_page": panel.is_full_page,
        }
    except Exception as e:
        log(f"    Error analyzing panel {panel_num}: {e}", "error")
        return {
            "page_num": page_num,
            "panel_num": panel_num,
            "total_panels": total_panels,
            "tipo": "fumetto",
            "titolo": f"Vignetta {panel_num}",
            "descrizione": f"(Errore analisi: {e})",
            "personaggi": "",
            "dialoghi": balloon_text or "",
            "dialoghi_ocr": balloon_text,
            "balloon_count": len(balloons),
            "effetto_sonoro": "",
            "ambientazione": "",
            "durata_stimata": 10,
            "panel_bbox": {
                "x": panel.x, "y": panel.y,
                "width": panel.width, "height": panel.height,
            },
            "is_full_page": panel.is_full_page,
        }


# ---------------------------------------------------------------------------
# Full page analysis (all panels on a page)
# ---------------------------------------------------------------------------

def analyze_page_panels(
    model: str,
    panels: list[Panel],
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 300,
    comic_title: str = "",
    use_balloon_ocr: bool = True,
    debug_balloons: bool = False,
    debug_dir: str = "",
    skip_no_balloon: bool = True,
    total_comic_pages: int = 0,
) -> list[dict]:
    """
    Analizza TUTTI i pannelli di una pagina, uno per uno.

    INTEGRAZIONE BALLOON: per ogni pannello, prima rileva i balloon
    con OpenCV + EasyOCR, poi passa il testo OCR al prompt LLM.

    SKIP NO-BALLOON: se una pagina NON ha balloon in nessun pannello,
    viene classificata e saltata (nessuna chiamata LLM).
    La classificazione usa total_comic_pages per distinguere
    "intro", "credits" e "no_dialogo".

    Args:
        use_balloon_ocr: Se True, attiva rilevamento balloon + OCR
        debug_balloons: Se True, salva immagini debug con balloon
        debug_dir: Directory per debug images
        skip_no_balloon: Se True, salta pagine senza balloon (default)
        total_comic_pages: Numero TOTALE di pagine nel fumetto
                           (serve per classificare correttamente i credits)

    Returns:
        Lista di dict, uno per pannello
    """
    if not panels:
        return []

    page_num = panels[0].page_num
    total_panels = len(panels)

    # --- Prima passata: rileva balloon in TUTTI i pannelli ---
    # per decidere se analizzare o saltare la pagina
    page_has_balloons = False
    panel_balloon_texts = []

    if skip_no_balloon and use_balloon_ocr:
        for panel in panels:
            balloons, balloon_text = detect_balloons_in_panel(panel.image)
            panel_balloon_texts.append((balloons, balloon_text))
            if balloon_text.strip():
                page_has_balloons = True

        if not page_has_balloons:
            # Nessun balloon → classifica in base alla posizione
            pn = panels[0].page_num
            if pn == 1:
                tipo = "copertina"
            elif pn <= 3:
                tipo = "intro"
            elif total_comic_pages > 0 and pn >= total_comic_pages - 2:
                tipo = "credits"
            else:
                tipo = "no_dialogo"

            log(f"  Page {page_num}: NO balloons detected → skipping LLM ({tipo})", "info")

            # Nome leggibile per il tipo
            tipo_label = {
                "copertina": "Copertina",
                "intro": "Introduzione",
                "credits": "Credits",
                "no_dialogo": "Senza dialogo",
            }.get(tipo, tipo)

            results = []
            for i, panel in enumerate(panels):
                results.append({
                    "page_num": page_num,
                    "panel_num": i + 1,
                    "total_panels": total_panels,
                    "tipo": tipo,
                    "titolo": f"Pagina {page_num} — {tipo_label}",
                    "descrizione": f"(Pagina senza dialoghi — saltata automaticamente)",
                    "personaggi": "",
                    "dialoghi": "",
                    "dialoghi_ocr": "",
                    "balloon_count": 0,
                    "effetto_sonoro": "",
                    "ambientazione": "",
                    "durata_stimata": 8,
                    "panel_bbox": {
                        "x": panel.x, "y": panel.y,
                        "width": panel.width, "height": panel.height,
                    },
                    "is_full_page": panel.is_full_page,
                    "skipped": True,
                    "skip_reason": "no_balloons",
                })
            return results

    # --- La pagina HA balloon → analisi completa LLM ---
    log(f"  Analyzing {total_panels} panel(s) on page {page_num}...", "info")

    results = []
    for i, panel in enumerate(panels):
        # Se abbiamo già i balloon dalla prima passata, usali
        if panel_balloon_texts:
            balloons, balloon_text = panel_balloon_texts[i]
        else:
            balloons, balloon_text = [], ""

        result = analyze_panel(
            model=model,
            panel=panel,
            total_panels=total_panels,
            ollama_url=ollama_url,
            timeout=timeout,
            comic_title=comic_title,
            use_balloon_ocr=use_balloon_ocr,
            debug_balloons=debug_balloons,
            debug_dir=debug_dir,
            precomputed_balloons=balloons if use_balloon_ocr else None,
            precomputed_text=balloon_text if use_balloon_ocr else "",
        )
        results.append(result)

        # Log breve
        titolo = result.get("titolo", f"Panel {i + 1}")
        personaggi = result.get("personaggi", "")
        dialoghi = result.get("dialoghi", "")
        if dialoghi:
            log(f"    Panel {i + 1}: {titolo} [{personaggi}] \"{dialoghi[:50]}...\"", "success")
        else:
            log(f"    Panel {i + 1}: {titolo} [{personaggi}]", "success")

    return results


# ---------------------------------------------------------------------------
# Final video script synthesis
# ---------------------------------------------------------------------------

def synthesize_script(
    model: str,
    panel_analyses: list[dict],
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 600,
    comic_title: str = "",
) -> dict:
    """
    Combina TUTTE le analisi dei pannelli e sintetizza uno script YouTube.

    A differenza della vecchia versione, usa le analisi per-pannello
    (più dettagliate e accurate) invece di analisi per-pagina.

    Args:
        panel_analyses: Lista di analisi di tutti i pannelli (da analyze_page_panels)
    """
    log("Synthesizing final video script...", "header")

    # Raggruppa per pagina per contesto migliore
    page_groups = {}
    for panel in panel_analyses:
        pn = panel["page_num"]
        if pn not in page_groups:
            page_groups[pn] = []
        page_groups[pn].append(panel)

    context_parts = []
    for page_num in sorted(page_groups.keys()):
        panels = page_groups[page_num]
        page_text = f"=== PAGINA {page_num} ({len(panels)} vignette) ==="
        for p in panels:
            page_text += f"\nVignetta {p['panel_num']}/{p['total_panels']}: "
            page_text += json.dumps(p, ensure_ascii=False, indent=2)
        context_parts.append(page_text)

    full_context = "\n\n".join(context_parts)

    # Truncate if too long
    if len(full_context) > 60000:
        log("  Many panels, sampling for synthesis...", "warning")
        n = len(panel_analyses)
        sampled = [panel_analyses[0]]
        for i in range(1, n - 1, max(1, n // 5)):
            sampled.append(panel_analyses[i])
        if n > 1:
            sampled.append(panel_analyses[-1])

        context_parts = []
        for panel in sampled:
            context_parts.append(
                f"Pagina {panel['page_num']}, Vignetta {panel['panel_num']}: "
                + json.dumps(panel, ensure_ascii=False)
            )
        full_context = "\n\n".join(context_parts)

    prompt = FINAL_SYNTHESIS_PROMPT.format(
        comic_title=comic_title,
        full_context=full_context,
    )

    response_text = call_ollama(
        model=model,
        prompt=prompt,
        ollama_url=ollama_url,
        temperature=0.4,
        timeout=timeout,
    )

    return parse_synthesis_json(response_text)
