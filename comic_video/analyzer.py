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
import re
import time
from itertools import groupby
from typing import Optional

from comic_video.utils import log, image_to_base64
from comic_video.ollama import (
    call_ollama,
    PANEL_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
    SCENE_SYNTHESIS_PROMPT,
    parse_json_response,
    parse_synthesis_json,
    DEFAULT_OLLAMA_URL,
    _sanitize_llm_field,
)
from comic_video.config import OLLAMA_TIMEOUT_SECONDS
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
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
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
        model: Nome del modello Ollama (es. "qwen2.5vl:7b")
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

    # Posizione descrittiva — NORMALIZZA le coordinate (erano confrontate come pixel!)
    pw = panel.page_width if panel.page_width > 0 else panel.image.width
    ph = panel.page_height if panel.page_height > 0 else panel.image.height
    center_x = (panel.x + panel.width / 2) / pw if pw > 0 else 0.5
    center_y = (panel.y + panel.height / 2) / ph if ph > 0 else 0.5
    pos_x = "sinistra" if center_x < 0.35 else "destra" if center_x > 0.65 else "centro"
    pos_y = "alto" if center_y < 0.35 else "basso" if center_y > 0.65 else "centro"
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

    log(f"    Analyzing panel {panel_num}/{total_panels} (page {page_num})... waiting for LLM...", "info")
    t_start = time.time()

    try:
        response_text = call_ollama(
            model=model,
            prompt=prompt,
            images=[b64_image],
            ollama_url=ollama_url,
            timeout=timeout,
            temperature=0.1,
        )
        t_elapsed = time.time() - t_start
        log(f"      LLM response received in {t_elapsed:.1f}s", "success")

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
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
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
            # Solo credits/pagine vuote finali vengono saltate
            is_credits = total_comic_pages > 0 and pn >= total_comic_pages - 2
            
            if pn == 1:
                tipo = "visual_storytelling"
                tipo_label = "Copertina — Attenzione visiva"
                skip = False
            elif is_credits:
                tipo = "credits"
                tipo_label = "Credits"
                skip = True
            else:
                tipo = "visual_storytelling"
                tipo_label = "Racconto visivo (nessun dialogo)"
                skip = False  # NON saltare pagine narrative importanti!

            if skip:
                log(f"  Page {page_num}: NO balloons detected — skipping ({tipo})", "info")
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
                        "skip_reason": "credits_no_balloons",
                        "keep_in_story": False,
                    })
                return results
            else:
                log(f"  Page {page_num}: NO balloons — narrative page (visual_storytelling)", "info")
                # Le pagine narrative senza dialoghi vengono analizzate lo stesso!

    # Analizza la pagina (con o senza balloon)
    if page_has_balloons:
        log(f"  Analyzing {total_panels} panel(s) on page {page_num} (with balloon OCR)...", "info")
    else:
        log(f"  Analyzing {total_panels} panel(s) on page {page_num} (visual storytelling, no balloons)...", "info")

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
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
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


# ---------------------------------------------------------------------------
# Global page analysis (full page, not just panels)
# ---------------------------------------------------------------------------

def analyze_full_page(
    model: str,
    page_image,
    page_num: int,
    total_comic_pages: int,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
    comic_title: str = "",
) -> dict:
    """
    Analizza l'INTERA pagina (non solo le singole vignette) per catturare
    l'atmosfera globale, la composizione e il ruolo narrativo della tavola.

    Questa analisi globale serve come CONTESTO per la scene synthesis,
    perché molte scene sono costruite dall'intera tavola, non da un singolo panel.

    Args:
        model: Nome del modello Ollama
        page_image: Immagine PIL della pagina intera
        page_num: Numero della pagina
        total_comic_pages: Numero totale di pagine
        comic_title: Titolo del fumetto

    Returns:
        Dict con analisi globale della pagina
    """
    prompt = f"""Sei un regista cinematografico specializzato in fumetti.

Fumetto: "{comic_title}"
Pagina: {page_num}/{total_comic_pages}

Osserva QUESTA INTERA PAGINA. Non concentrarti sulle singole vignette,
ma analizza l'effetto GLOBALE della tavola.

Rispondi in JSON:
{{
  "atmosfera": "Cupo e opprimente, malinconico, dinamico, ecc.",
  "ruolo_narrativo": "Introduzione, climax, transizione, rivelazione, ecc.",
  "composizione": "Griglia regolare 3x3, splash page, layout irregolare, ecc.",
  "elementi_chiave": "Cosa colpisce di piu' visivamente in questa pagina",
  "transizione_emotiva": "Come cambia il tono dall'inizio alla fine della pagina"
}}

Produci SOLO il JSON.
"""

    b64_image = image_to_base64(page_image)

    log(f"  Analyzing full page {page_num} (global)...", "info")
    try:
        response_text = call_ollama(
            model=model,
            prompt=prompt,
            images=[b64_image],
            ollama_url=ollama_url,
            timeout=timeout,
            temperature=0.2,
        )
        # Parse JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_match = re.search(r'(\{[\s\S]*\})', response_text)
            json_str = json_match.group(1).strip() if json_match else "{}"

        result = json.loads(json_str)
        result["page_num"] = page_num
        # Sanitize global page analysis fields
        text_fields = ["atmosfera", "ruolo_narrativo", "composizione", "elementi_chiave", "transizione_emotiva"]
        for field in text_fields:
            if field in result and isinstance(result[field], str):
                result[field] = _sanitize_llm_field(result[field], field)
        return result
    except Exception as e:
        log(f"    Warning: global page analysis failed for page {page_num}: {e}", "warning")
        return {
            "page_num": page_num,
            "atmosfera": "",
            "ruolo_narrativo": "",
            "composizione": "",
            "elementi_chiave": "",
            "transizione_emotiva": "",
        }


# ---------------------------------------------------------------------------
# YouTube Scene Transcript Synthesis
# ---------------------------------------------------------------------------

def synthesize_scene_json(
    model: str,
    panel_analyses: list[dict],
    page_analyses: list[dict] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
    comic_title: str = "",
) -> list[dict]:
    """
    Sintetizza le analisi dei pannelli in un formato JSON scena-per-scena
    stile YouTube transcript.

    RAGGRUPPA 2-4 pagine consecutive in una scena, e per ogni scena produce:
      - scene_id, title, pages, location, characters
      - visual_description, voiceover, dialogue_summary
      - mood, camera_style, youtube_hook

    Args:
        model: Modello Ollama
        panel_analyses: Lista di analisi per-pannello
        page_analyses: Lista opzionale di analisi globali per-pagina
        comic_title: Titolo del fumetto

    Returns:
        Lista di dict, uno per scena
    """
    log("Synthesizing scene-by-scene YouTube transcript...", "header")

    # Costruisci contesto combinato: analisi pagina globale + pannelli
    context_parts = []

    # Raggruppa pannelli per pagina
    page_groups = {}
    for panel in panel_analyses:
        pn = panel["page_num"]
        if pn not in page_groups:
            page_groups[pn] = []
        page_groups[pn].append(panel)

    # Trova analisi globali per pagina
    page_analysis_map = {}
    if page_analyses:
        for pa in page_analyses:
            page_analysis_map[pa.get("page_num", 0)] = pa

    for page_num in sorted(page_groups.keys()):
        panels = page_groups[page_num]

        # Aggiungi analisi globale se disponibile
        if page_num in page_analysis_map:
            g = page_analysis_map[page_num]
            context_parts.append(
                f"=== PAGINA {page_num} (ANALISI GLOBALE) ===\n"
                f"Atmosfera: {g.get('atmosfera', 'N/D')}\n"
                f"Ruolo narrativo: {g.get('ruolo_narrativo', 'N/D')}\n"
                f"Composizione: {g.get('composizione', 'N/D')}\n"
                f"Elementi chiave: {g.get('elementi_chiave', 'N/D')}\n"
            )

        # Dettaglio pannelli
        page_text = f"=== PAGINA {page_num} ({len(panels)} vignette) ==="
        for p in panels:
            page_text += f"\nVignetta {p['panel_num']}/{p['total_panels']}: "
            desc = p.get("descrizione", "")
            dialog = p.get("dialoghi", "")
            chars = p.get("personaggi", "")
            page_text += f"[{chars}] {desc}"
            if dialog:
                page_text += f" Dialogo: \"{dialog}\""
        context_parts.append(page_text)

    full_context = "\n\n".join(context_parts)

    # Truncate if too long
    if len(full_context) > 50000:
        log("  Context too long, sampling for scene synthesis...", "warning")
        pages_list = sorted(page_groups.keys())
        if len(pages_list) > 30:
            # Prendi prime e ultime pagine, e un campione del mezzo
            sampled_indices = list(range(0, min(5, len(pages_list))))
            sampled_indices += list(range(max(5, len(pages_list) - 5), len(pages_list)))
            step = max(1, (len(pages_list) - 10) // 5)
            sampled_indices += list(range(5, len(pages_list) - 5, step))
            sampled_pages = sorted(set(pages_list[i] for i in sampled_indices if i < len(pages_list)))
        else:
            sampled_pages = pages_list

        context_parts = []
        for pn in sampled_pages:
            panels = page_groups[pn]
            if pn in page_analysis_map:
                g = page_analysis_map[pn]
                context_parts.append(f"=== PAGINA {pn} ===\nAtmosfera: {g.get('atmosfera', '')}")
            for p in panels:
                context_parts.append(
                    f"Pagina {pn}, Panel {p['panel_num']}: {p.get('descrizione', '')[:200]}"
                )
        full_context = "\n".join(context_parts)

    prompt = SCENE_SYNTHESIS_PROMPT.format(
        comic_title=comic_title,
        full_context=full_context,
    )

    response_text = call_ollama(
        model=model,
        prompt=prompt,
        ollama_url=ollama_url,
        temperature=0.3,
        timeout=timeout,
    )

    return _parse_scene_json(response_text)


# ---------------------------------------------------------------------------
# Page-by-page digest JSON
# ---------------------------------------------------------------------------

def synthesize_page_digest_json(
    model: str,
    panel_analyses: list[dict],
    page_analyses: list[dict] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
    comic_title: str = "",
    total_pages: int = 0,
) -> dict:
    """
    Produce un digest JSON pagina-per-pagina nello schema richiesto.

    Output atteso:
    {
      "titolo": "...",
      "tipo": "riassunto_pagina_per_pagina",
      "lingua_del_pdf": "italiano",
      "pagine_totali": 52,
      "pagine": [...]
    }
    """
    log("Synthesizing page-by-page digest JSON...", "header")

    page_groups = {}
    for panel in panel_analyses:
        pn = panel["page_num"]
        page_groups.setdefault(pn, []).append(panel)

    page_analysis_map = {}
    if page_analyses:
        for pa in page_analyses:
            page_analysis_map[pa.get("page_num", 0)] = pa

    context_parts = []
    for page_num in sorted(page_groups.keys()):
        panels = page_groups[page_num]
        page_text = f"=== PAGINA {page_num} ({len(panels)} vignette) ==="
        if page_num in page_analysis_map:
            g = page_analysis_map[page_num]
            page_text += (
                f"\nANALISI GLOBALE: atmosfera={g.get('atmosfera', '')}; "
                f"ruolo_narrativo={g.get('ruolo_narrativo', '')}; "
                f"composizione={g.get('composizione', '')}; "
                f"elementi_chiave={g.get('elementi_chiave', '')}; "
                f"transizione_emotiva={g.get('transizione_emotiva', '')}"
            )
        for p in panels:
            page_text += (
                f"\nVignetta {p['panel_num']}/{p['total_panels']}: "
                f"[{p.get('personaggi', '')}] {p.get('descrizione', '')}"
            )
            if p.get("dialoghi"):
                page_text += f" Dialogo: \"{p['dialoghi']}\""
        context_parts.append(page_text)

    full_context = "\n\n".join(context_parts)

    prompt = f"""Sei un analista editoriale di fumetti.

Fumetto: "{comic_title}"
Numero pagine totali: {total_pages or len(page_groups)}

Devi produrre un JSON pagina-per-pagina nello schema esatto seguente:

{{
  "titolo": "{comic_title}",
  "tipo": "riassunto_pagina_per_pagina",
  "lingua_del_pdf": "italiano",
  "pagine_totali": {total_pages or len(page_groups)},
  "pagine": [
    {{
      "pagina": 1,
      "tipo_pagina": "copertina | crediti | apertura atmosferica | storia | flashback | transizione | climax | finale | pagina senza dialoghi",
      "personaggi": ["Batman", "Joker"],
      "luogo": "descrizione sintetica del luogo",
      "cosa_succede": "descrizione originale, chiara e naturale di ciò che accade nella pagina",
      "funzione_narrativa": "ruolo della pagina nel racconto"
    }}
  ]
}}

Regole:
- Scrivi in italiano.
- Non trascrivere i balloon parola per parola.
- Ogni pagina deve avere una descrizione originale e sintetica ma specifica.
- Se una pagina non ha dialoghi, descrivila comunque.
- Mantieni il tono coerente con il fumetto.
- Produci SOLO JSON valido, senza markdown.

Contesto analitico:
{full_context}
"""

    response_text = call_ollama(
        model=model,
        prompt=prompt,
        ollama_url=ollama_url,
        temperature=0.2,
        timeout=timeout,
    )

    return _parse_page_digest_json(response_text, comic_title, total_pages or len(page_groups), page_groups, page_analysis_map)


def _validate_scene_list(scenes: list) -> list[dict]:
    """Validate and normalize a list of scene dicts."""
    results = []
    for item in scenes:
        if not isinstance(item, dict):
            continue
        defaults = {
            "scene_id": len(results) + 1,
            "title": "Scena",
            "pages": "",
            "location": "",
            "characters": [],
            "visual_description": "",
            "voiceover": "",
            "dialogue_summary": "",
            "mood": "",
            "camera_style": "",
            "youtube_hook": "",
        }
        for key, default in defaults.items():
            if key not in item:
                item[key] = default
        results.append(item)
    return results if results else _empty_scene_list()


def _parse_scene_json(text: str) -> list[dict]:
    """Parse the scene synthesis JSON array response."""
    raw = text.strip()
    if not raw:
        return _empty_scene_list()

    # 1. Try direct JSON.parse first (fast path for clean responses)
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return _validate_scene_list(result)
        if isinstance(result, dict):
            if "scenes" in result:
                return _validate_scene_list(result["scenes"])
            return _validate_scene_list([result])
    except json.JSONDecodeError:
        pass

    # 2. Fallback: markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return _validate_scene_list(result)
            if isinstance(result, dict) and "scenes" in result:
                return _validate_scene_list(result["scenes"])
        except json.JSONDecodeError:
            pass

    # 3. Final fallback: find last [...] array and clean trailing commas
    json_match = re.search(r'(\[[\s\S]*\])', raw)
    if json_match:
        json_str = json_match.group(1).strip()
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return _validate_scene_list(result)
        except json.JSONDecodeError:
            pass

    log(f"  Warning: could not parse scene JSON", "warning")
    log(f"  Raw (first 200): {raw[:200]}", "warning")
    return _empty_scene_list()


def _empty_scene_list() -> list[dict]:
    """Return a fallback empty scene list."""
    return [{
        "scene_id": 1,
        "title": "Analisi completa",
        "pages": "1-50",
        "location": "",
        "characters": [],
        "visual_description": "",
        "voiceover": "",
        "dialogue_summary": "",
        "mood": "",
        "camera_style": "",
        "youtube_hook": "",
    }]


def _parse_page_digest_json(
    text: str,
    comic_title: str,
    total_pages: int,
    page_groups: dict,
    page_analysis_map: dict,
) -> dict:
    """Parse the page-by-page digest JSON object."""
    raw = text.strip()
    fallback_pages = []

    for page_num in sorted(page_groups.keys()):
        panels = page_groups[page_num]
        page_kind = "storia"
        if page_num == 1:
            page_kind = "copertina"
        elif page_num <= 3:
            page_kind = "apertura atmosferica"
        elif total_pages > 0 and page_num >= total_pages - 1:
            page_kind = "crediti"
        elif page_num in page_analysis_map and page_analysis_map[page_num].get("ruolo_narrativo"):
            page_kind = page_analysis_map[page_num]["ruolo_narrativo"]

        combined_dialogs = " ".join(
            p.get("dialoghi", "").strip()
            for p in panels
            if p.get("dialoghi", "").strip()
        ).strip()
        combined_desc = " ".join(
            p.get("descrizione", "").strip()
            for p in panels
            if p.get("descrizione", "").strip()
        ).strip()
        fallback_pages.append({
            "pagina": page_num,
            "tipo_pagina": page_kind,
            "personaggi": sorted({c for p in panels for c in _normalize_people_field(p.get("personaggi", ""))}),
            "luogo": page_analysis_map.get(page_num, {}).get("composizione", "") or "luogo non specificato",
            "cosa_succede": combined_desc or combined_dialogs or f"Pagina {page_num} analizzata con {len(panels)} vignette.",
            "funzione_narrativa": page_analysis_map.get(page_num, {}).get("ruolo_narrativo", "") or "Sviluppo della trama",
        })

    fallback = {
        "titolo": comic_title,
        "tipo": "riassunto_pagina_per_pagina",
        "lingua_del_pdf": "italiano",
        "pagine_totali": total_pages,
        "pagine": fallback_pages,
    }

    if not raw:
        return fallback

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        if isinstance(result, dict) and "pagine" in result:
            return _normalize_page_digest_object(result, comic_title, total_pages, page_groups, page_analysis_map, fallback)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if json_match:
        try:
            result = json.loads(json_match.group(1).strip())
            if isinstance(result, dict) and "pagine" in result:
                return _normalize_page_digest_object(result, comic_title, total_pages, page_groups, page_analysis_map, fallback)
        except json.JSONDecodeError:
            pass

    if "```" in raw:
        candidate = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.split("```", 1)[-1]
        candidate = candidate.replace("json", "", 1).strip()
        try:
            result = json.loads(candidate)
            if isinstance(result, dict) and "pagine" in result:
                return _normalize_page_digest_object(result, comic_title, total_pages, page_groups, page_analysis_map, fallback)
        except json.JSONDecodeError:
            pass

    json_match = re.search(r'(\{[\s\S]*\})', raw)
    if json_match:
        try:
            result = json.loads(json_match.group(1).strip())
            if isinstance(result, dict) and "pagine" in result:
                return _normalize_page_digest_object(result, comic_title, total_pages, page_groups, page_analysis_map, fallback)
        except json.JSONDecodeError:
            pass

    log("  Warning: could not parse page digest JSON, using fallback", "warning")
    return fallback


def _normalize_page_digest_object(
    obj: dict,
    comic_title: str,
    total_pages: int,
    page_groups: dict,
    page_analysis_map: dict,
    fallback: dict,
) -> dict:
    """Normalize model output and remove prompt leakage."""
    normalized = {
        "titolo": obj.get("titolo", comic_title) or comic_title,
        "tipo": obj.get("tipo", "riassunto_pagina_per_pagina") or "riassunto_pagina_per_pagina",
        "lingua_del_pdf": obj.get("lingua_del_pdf", "italiano") or "italiano",
        "pagine_totali": obj.get("pagine_totali", total_pages) or total_pages,
        "pagine": [],
    }

    raw_pages = obj.get("pagine", [])
    page_map = {item.get("pagina"): item for item in raw_pages if isinstance(item, dict)}

    for page_num in sorted(page_groups.keys()):
        panels = page_groups[page_num]
        page_item = page_map.get(page_num, {})
        fallback_item = next((p for p in fallback["pagine"] if p["pagina"] == page_num), {})

        tipo = _clean_page_digest_tipo(page_item.get("tipo_pagina"), page_num, total_pages, page_analysis_map)
        personaggi = _normalize_people_field(
            page_item.get("personaggi", [])
            if isinstance(page_item.get("personaggi"), str)
            else ", ".join(page_item.get("personaggi", [])) if isinstance(page_item.get("personaggi"), list) else ""
        )
        if not personaggi:
            personaggi = fallback_item.get("personaggi", [])
        luogo = _clean_page_digest_text(page_item.get("luogo"), fallback_item.get("luogo", "luogo non specificato"))
        cosa = _clean_page_digest_text(page_item.get("cosa_succede"), fallback_item.get("cosa_succede", ""))
        funzione = _clean_page_digest_text(page_item.get("funzione_narrativa"), fallback_item.get("funzione_narrativa", "Sviluppo della trama"))

        normalized["pagine"].append({
            "pagina": page_num,
            "tipo_pagina": tipo,
            "personaggi": personaggi,
            "luogo": luogo,
            "cosa_succede": cosa,
            "funzione_narrativa": funzione,
        })

    return normalized


def _clean_page_digest_text(value, fallback: str) -> str:
    if isinstance(value, str):
        cleaned = _sanitize_llm_field(value)
        if cleaned and "|" not in cleaned and cleaned.lower() not in {
            "luogo", "cosa succede", "funzione narrativa",
            "descrizione sintetica del luogo",
        }:
            return cleaned
    return fallback


def _clean_page_digest_tipo(value, page_num: int, total_pages: int, page_analysis_map: dict) -> str:
    if isinstance(value, str):
        cleaned = _sanitize_llm_field(value)
        if cleaned and "|" not in cleaned and len(cleaned) < 60:
            return cleaned

    if page_num == 1:
        return "copertina"
    if page_num == 2:
        return "crediti"
    if page_num <= 3:
        return "apertura atmosferica"
    if total_pages > 0 and page_num >= total_pages - 1:
        return "finale"

    page_analysis = page_analysis_map.get(page_num, {})
    role = _sanitize_llm_field(page_analysis.get("ruolo_narrativo", "")) if page_analysis else ""
    if role and "|" not in role:
        return role

    return "storia"


def _normalize_people_field(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.extend(re.split(r"[,\n;/|]+", item))
            elif item is not None:
                parts.append(str(item))
    else:
        parts = re.split(r"[,\n;/|]+", str(value))
    cleaned = []
    for part in parts:
        part = part.strip()
        if part and part.lower() not in {"nessuno", "n/a", "n.d.", "nd"}:
            cleaned.append(part)
    return cleaned


def build_page_digest_fallback(
    panel_analyses: list[dict],
    page_analyses: list[dict] = None,
    comic_title: str = "",
    total_pages: int = 0,
) -> dict:
    """Build a deterministic page-by-page digest without calling the model."""
    page_groups = {}
    for panel in panel_analyses:
        pn = panel["page_num"]
        page_groups.setdefault(pn, []).append(panel)

    page_analysis_map = {}
    if page_analyses:
        for pa in page_analyses:
            page_analysis_map[pa.get("page_num", 0)] = pa

    pagine = []
    for page_num in sorted(page_groups.keys()):
        panels = page_groups[page_num]
        page_analysis = page_analysis_map.get(page_num, {})
        dialoghi = " ".join(
            p.get("dialoghi_ocr", p.get("dialoghi", "")).strip()
            for p in panels
            if p.get("dialoghi_ocr", p.get("dialoghi", "")).strip()
        ).strip()
        descrizioni = " ".join(
            p.get("descrizione", "").strip()
            for p in panels
            if p.get("descrizione", "").strip() and not p.get("descrizione", "").strip().startswith("(Errore")
        ).strip()
        personaggi = sorted({
            c for p in panels for c in _normalize_people_field(p.get("personaggi", ""))
        })

        if not descrizioni and dialoghi:
            descrizioni = f"La pagina mostra una vignetta con il testo OCR '{dialoghi}'."
        elif not descrizioni:
            descrizioni = f"Pagina {page_num} analizzata con {len(panels)} vignette."

        pagine.append({
            "pagina": page_num,
            "tipo_pagina": _clean_page_digest_tipo(None, page_num, total_pages, page_analysis_map),
            "personaggi": personaggi,
            "luogo": _clean_page_digest_text(page_analysis.get("composizione", ""), "luogo non specificato"),
            "cosa_succede": descrizioni,
            "funzione_narrativa": _clean_page_digest_text(page_analysis.get("ruolo_narrativo", ""), "Sviluppo della trama"),
        })

    return {
        "titolo": comic_title,
        "tipo": "riassunto_pagina_per_pagina",
        "lingua_del_pdf": "italiano",
        "pagine_totali": total_pages or len(pagine),
        "pagine": pagine,
    }
