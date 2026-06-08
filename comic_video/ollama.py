"""
Modulo Ollama — chiamate API e prompt per analisi fumetti.

Contiene:
    - call_ollama()        — Chiamata API a Ollama
    - SYSTEM_PROMPT        — Prompt principale per analisi pagina singola
    - BATCH_PROMPT_TEMPLATE— Prompt per analisi batch
    - FINAL_SYNTHESIS_PROMPT — Prompt per sintesi video finale
    - parse_json_response()— Parsing risposte JSON
"""

import json
import re
import time
from typing import Any, Optional

import requests

from comic_video.utils import log
from comic_video.config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS

# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_URL = OLLAMA_URL
DEFAULT_MODEL = OLLAMA_MODEL


# ---------------------------------------------------------------------------
# Ollama API call
# ---------------------------------------------------------------------------

def call_ollama(
    model: str,
    prompt: str,
    images: Optional[list[str]] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    temperature: float = 0.1,
    max_retries: int = 3,
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
) -> str:
    """
    Call Ollama generate API with optional images (base64).
    TIMEOUT: default 300s (5 min). Logga ogni tentativo.
    Returns the generated text.
    """
    has_images = f" with {len(images)} image(s)" if images else ""
    log(f"    Calling Ollama {model}{has_images} (timeout={timeout}s)...", "info")

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if images:
        payload["images"] = images

    url = f"{ollama_url.rstrip('/')}/api/generate"

    for attempt in range(max_retries):
        try:
            log(f"      Ollama request attempt {attempt+1}/{max_retries}...", "info")
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            log(f"      Ollama response: {len(response_text)} chars", "success")
            return response_text
        except requests.exceptions.ConnectionError as e:
            log(f"      Cannot connect to Ollama at {ollama_url}: {e}", "error")
            if attempt < max_retries - 1:
                log(f"      Retrying in 2s... (attempt {attempt+1}/{max_retries})", "warning")
                time.sleep(2)
            else:
                raise
        except requests.exceptions.Timeout as e:
            log(f"      Ollama request TIMED OUT after {timeout}s (attempt {attempt+1}/{max_retries})", "warning")
            if attempt < max_retries - 1:
                log(f"      Retrying in 2s... (attempt {attempt+1}/{max_retries})", "warning")
                time.sleep(2)
            else:
                raise
        except Exception as e:
            log(f"      Ollama API error: {e}", "error")
            raise

    return ""


# ---------------------------------------------------------------------------
# Prompts — YouTube-NARRATIVE STYLE
# ---------------------------------------------------------------------------

PANEL_PROMPT = """Sei un narratore di fumetti per YouTube specializzato nell'analisi di singole vignette.

Fumetto: "{comic_title}"
Pagina: {page_num}
Vignetta: {panel_num}/{total_panels} (posizione: {position})

--- TESTO ESTRATTO DAI BALLOON (OCR) ---

Di seguito il testo ESTRATTO con OCR dai balloon di QUESTA vignetta.
QUESTO È il testo reale dei balloon — usalo FEDELMENTE per i dialoghi.

{ocr_text}

--- COSA DEVI FARE ---

Analizza SOLO QUESTA singola vignetta.

1. **AMBIENTAZIONE:** Dove siamo? (interno/esterno, giorno/notte, luogo)
2. **PERSONAGGI:** Chi vedi realmente? Cosa fanno? Espressioni?
3. **AZIONI:** Cosa succede nella scena?
4. **DIALOGHI:** Usa il TESTO OCR qui sopra per i dialoghi. È affidabile.
   Se l'OCR ha estratto testo, QUELLO è il dialogo — non cambiarlo.
   Se NON c'è testo OCR, NON inventare dialoghi.

--- REGOLE FERRENCE ---

- NON INVENTARE personaggi o dialoghi
- Scrivi in ITALIANO
- Non usare: atmosfera, tensione, palpabile, caos, follia, psicologico

--- OUTPUT JSON ---
{{
  "page_num": {page_num},
  "panel_num": {panel_num},
  "total_panels": {total_panels},
  "tipo": "fumetto" | "copertina" | "splash" | "credits",
  "titolo": "Titolo breve della scena",
  "ambientazione": "Dove siamo",
  "descrizione": "Racconto (4-6 frasi). Includi i dialoghi nella narrazione usando il TESTO OCR.",
  "personaggi": "Personaggi visibili",
  "dialoghi": "IL TESTO OCR SOPRA (o vuoto se nessun balloon)",
  "effetto_sonoro": "Onomatopea",
  "durata_stimata": 20
}}

Produci SOLO il JSON, nient'altro.
"""



SCENE_SYNTHESIS_PROMPT = """Sei un regista e sceneggiatore YouTube specializzato nella creazione di transcript per video narrazione di fumetti.

Fumetto: "{comic_title}"

Hai davanti le analisi complete di TUTTE le pagine del fumetto, suddivise in vignette.

Il tuo compito: RAGGRUPPA le pagine in SCENE (tipicamente 2-4 pagine per scena) e per
ogni scena produci un oggetto JSON con questo formato ESATTO:

{{
  "scene_id": 1,
  "title": "Titolo breve della scena",
  "pages": "1-3",
  "location": "Luogo della scena",
  "characters": ["Batman", "Joker"],
  "visual_description": "Descrizione visiva della scena (2-3 frasi)",
  "voiceover": "Testo che il narratore legge per questa scena (in italiano, 3-6 frasi)",
  "dialogue_summary": "Riassunto dei dialoghi principali della scena",
  "mood": "Tono emotivo (es. cupo, teso, malinconico, drammatico)",
  "camera_style": "Stile visuale suggerito (es. slow pan, zoom-in, fade)",
  "youtube_hook": "Frase di aggancio per mantenere l'attenzione (1 frase)"
}}

REGOLE:
- Ogni scena deve coprire 2-4 pagine consecutive
- Inizia con una scena hook (copertina o prime pagine)
- Raggruppa logicamente le pagine che condividono stesso luogo/evento
- Scrivi voiceover in ITALIANO, come se parlassi a voce alta
- La durata di ogni voce deve essere ~20-45 secondi letta
- Produci un ARRAY JSON di scene, nient'altro

Analisi completa del fumetto:
{full_context}
"""


FINAL_SYNTHESIS_PROMPT = """Sei un regista e narratore YouTube. Hai appena letto tutto il fumetto "{comic_title}".
Ora devi creare lo SCRIPT FINALE per il video.

--- STRUTTURA DELLO SCRIPT ---

Lo script deve avere TRE parti ben distinte:

**PARTE 1 — INTRODUZIONE (1-2 paragrafi):**
- Presenta il fumetto: titolo, autore, contesto, perche' e' importante
- Spiega chi sono i personaggi principali e qual e' il conflitto centrale
- Cattura l'attenzione nei primi 10 secondi con un gancio potente
- SCRITTA DOPO aver letto le pagine (non prima) — basata su quello che hai visto

**PARTE 2 — NARRAZIONE DELLE PAGINE (corpo principale):**
- Racconta l'INTERA STORIA dall'inizio alla fine, in modo fluido
- Alterna NARRAZIONE della scena e DIALOGHI dei personaggi
- Scrivila PER ESSERE LETTA AD ALTA VOCE (come un narratore YouTube)
- Includi le citazioni piu' importanti dei dialoghi
- Circa 2000-4000 parole totali

**PARTE 3 — FINALE RIASSUNTIVO (1-2 paragrafi):**
- Riassume il significato della storia
- Riflette sul messaggio del fumetto
- Lascia allo spettatore una riflessione finale coinvolgente
- Invita a guardare/leggere il fumetto completo

FORMATO RISPOSTA:
{{
  "titolo_video": "TITOLO ACCHIAPPANTE per il video",
  "genere": "Genere del fumetto",
  "personaggi_principali": ["Batman", "Joker"],
  "colonna_sonora": "Stile musicale suggerito",
  "script_narrativo": "Testo completo: prima l introduzione sul fumetto, poi la narrazione delle pagine con dialoghi, poi la conclusione riassuntiva.",
  "durata_totale_stimata_minuti": 15
}}

Ecco le analisi delle pagine (leggile TUTTE prima di scrivere l'intro e la conclusione):
{full_context}
"""


# ---------------------------------------------------------------------------
# Response sanitization helpers
# ---------------------------------------------------------------------------

# Patterns that indicate prompt leakage / placeholder text from the LLM
# These are matched ANYWHERE in the text.
_PROMPT_LEAKAGE_PATTERNS = [
    r"Racconto \(4-6 frasi\)\.?\s*",
    r"---\s*(TESTO ESTRATTO|COSA DEVI FARE|REGOLE|OUTPUT JSON)",
    r"Produci SOLO il JSON",
    r"Scrivi in ITALIANO",
    r"NON INVENTARE personaggi",
    r"Non usare:\s*atmosfera",
    r"Includi i dialoghi nella narrazione",
]

_PLACEHOLDER_EXACT = {
    "Racconto (4-6 frasi). Includi i dialoghi nella narrazione usando il TESTO OCR.": "",
    "Titolo breve della scena": "",
    "Personaggi visibili": "",
    "IL TESTO OCR SOPRA (o vuoto se nessun balloon)": "",
    "Onomatopea": "",
}


def _sanitize_llm_field(value: str, field_name: str = "") -> str:
    """
    Clean LLM response fields by removing prompt leakage and placeholder text.
    
    Returns the cleaned string, or an empty string if nothing usable remains.
    """
    if not isinstance(value, str):
        return ""
    
    cleaned = value.strip()
    
    # Remove exact placeholder matches (case-insensitive)
    for placeholder, replacement in _PLACEHOLDER_EXACT.items():
        cleaned = re.sub(re.escape(placeholder), replacement, cleaned, flags=re.IGNORECASE)
    
    # Remove prompt leakage patterns (case-insensitive)
    for pattern in _PROMPT_LEAKAGE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Remove lines that look like prompt instructions
    lines = cleaned.splitlines()
    filtered_lines = []
    for line in lines:
        line_stripped = line.strip()
        # Skip lines that are clearly prompt instructions (NOT real comic text)
        if any(
            line_stripped.lower().startswith(prefix)
            for prefix in [
                "---", "* * *", "regole:", "output json:", 
                "cosa devi fare:", "produci solo il json", "sei un narratore",
                "non usare:", "non inventare", "```"
            ]
        ):
            continue
        # Skip lines that are exactly the field example from the prompt JSON schema
        if re.match(r'^(descrizione|titolo|personaggi|ambientazione|dialoghi|effetto_sonoro|durata_stimata)\s*[:=]\s*"', line_stripped, re.IGNORECASE):
            continue
        filtered_lines.append(line)
    cleaned = "\n".join(filtered_lines)
    
    # Collapse multiple horizontal spaces but preserve newlines (for multi-line descriptions)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned).strip()
    # Strip leading residual punctuation left by partial regex matches
    cleaned = cleaned.lstrip('. ').strip()
    
    return cleaned


def _sanitize_panel_result(result: dict, page_num: int) -> dict:
    """
    Apply sanitization to all text fields in a panel analysis result dict.
    Falls back to raw value if sanitization empties the field.
    """
    # Fields to sanitize
    text_fields = ["descrizione", "titolo", "titolo_scena", "personaggi", "ambientazione", 
                   "dialoghi", "effetto_sonoro", "descrizione_narrativa"]
    
    for field in text_fields:
        if field in result and isinstance(result[field], str):
            original = result[field]
            sanitized = _sanitize_llm_field(original, field)
            # Heuristic: keep sanitized only if it retains a reasonable portion of
            # the original text (avoids over-sanitization of real content)
            min_kept_ratio = 0.25
            min_kept_chars = 8
            is_placeholder = original.strip() in _PLACEHOLDER_EXACT
            
            if is_placeholder:
                # Known placeholder → always use sanitized (usually empty)
                result[field] = sanitized
            elif sanitized and (len(sanitized) >= len(original) * min_kept_ratio or len(sanitized) >= min_kept_chars):
                # Sanitized result looks like real text → keep it
                result[field] = sanitized
            elif sanitized and len(original) < 20:
                # Very short original, accept whatever remains
                result[field] = sanitized
            # else: keep original (sanitization probably stripped real content)
    
    # Fallback for empty description
    if not result.get("descrizione", "").strip() and not result.get("descrizione_narrativa", "").strip():
        result["descrizione"] = f"(Descrizione non disponibile per pagina {page_num})"
        result["descrizione_narrativa"] = result["descrizione"]
    
    # Fallback for empty title
    if not result.get("titolo", "").strip() and not result.get("titolo_scena", "").strip():
        result["titolo"] = f"Pagina {page_num}"
        result["titolo_scena"] = result["titolo"]
    
    return result


# ---------------------------------------------------------------------------
# JSON Parsers
# ---------------------------------------------------------------------------

def parse_json_response(text: str, page_num: int) -> dict:
    """Extract JSON from the model response."""
    raw = text.strip()

    # Try extracting JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find { ... } object
        json_match = re.search(r'(\{[\s\S]*\})', raw)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = raw

    # Clean common JSON issues
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        parsed = json.loads(json_str)
        # Ensure we have a dict, not a string or list
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected dict, got {type(parsed).__name__}")
    except (json.JSONDecodeError, ValueError) as e:
        log(f"  Warning: JSON parse failed for page {page_num}: {e}", "warning")
        log(f"  Raw: {raw[:150]}", "warning")
        return {
            "page_num": page_num,
            "tipo_pagina": "fumetto",
            "titolo_scena": f"Pagina {page_num}",
            "descrizione_narrativa": raw[:500] or "(Nessuna descrizione)",
            "personaggi": "",
            "dialoghi": "",
            "effetto_sonoro": "",
            "durata_stimata": 10,
        }

    # Fill defaults for missing fields
    result: dict = parsed
    defaults = {
        "tipo_pagina": "fumetto",
        "titolo_scena": f"Pagina {page_num}",
        "descrizione_narrativa": raw[:500],
        "personaggi": "",
        "dialoghi": "",
        "effetto_sonoro": "",
        "durata_stimata": 10,
    }
    for key, default in defaults.items():
        if key not in result:
            result[key] = default

    # Sanitize prompt leakage / placeholders from LLM response fields
    result = _sanitize_panel_result(result, page_num)
    return result


def parse_batch_json_response(text: str, batch_pages: list[dict]) -> list[dict]:
    """Parse a JSON array response from batch analysis."""
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_match = re.search(r'(\[[\s\S]*\])', text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = text.strip()

    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        parsed_list = json.loads(json_str)
        if isinstance(parsed_list, list):
            results = []
            for item in parsed_list:
                pn = item.get("page_num", 0)
                defaults = {
                    "tipo_pagina": "fumetto",
                    "titolo_scena": f"Pagina {pn}" if pn else "Scena",
                    "descrizione_narrativa": "",
                    "personaggi": "",
                    "dialoghi": "",
                    "effetto_sonoro": "",
                    "durata_stimata": 10,
                }
                for key, default in defaults.items():
                    if key not in item:
                        item[key] = default
                # Sanitize each result
                item = _sanitize_panel_result(item, item.get("page_num", 0))
                results.append(item)
            return results
    except (json.JSONDecodeError, TypeError):
        log(f"  Warning: could not parse batch JSON array", "warning")

    # Fallback
    log(f"  Falling back to single-page parse", "warning")
    results = []
    for page_data in batch_pages:
        pn = page_data["page_num"]
        result = parse_json_response(text, pn)
        result["page_num"] = pn
        results.append(result)
    return results


def parse_synthesis_json(text: str) -> dict:
    """Parse the final synthesis JSON.

    Strategy:
        1. Look for ```json ... ``` (markdown block)
        2. Look for the LAST { ... } block (avoids matching braces in full_context)
        3. Fallback: raw text
    """
    raw = text.strip()
    if not raw:
        return {
            "titolo_video": "Analisi Fumetto",
            "genere": "",
            "personaggi_principali": [],
            "colonna_sonora": "",
            "script_narrativo": "",
            "durata_totale_stimata_minuti": 0,
        }

    # 1. Try markdown code blocks first (most reliable)
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # 2. Find the LAST JSON-like block by scanning from the end
        #    This avoids matching braces inside full_context
        last_brace_start = raw.rfind('{')
        last_brace_end = raw.rfind('}')
        if last_brace_start >= 0 and last_brace_end > last_brace_start:
            json_str = raw[last_brace_start:last_brace_end + 1]
        else:
            json_str = raw

    # Clean common JSON issues
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    # Fix invalid single backslashes that are not valid JSON escapes
    # Valid escapes: \" \\ \/ \b \f \n \r \t \uXXXX
    json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)

    try:
        result = json.loads(json_str)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        required = ["titolo_video", "script_narrativo"]
        for key in required:
            if key not in result:
                result[key] = f"(MISSING: {key})"
        # Sanitize synthesis text fields
        for field in ["titolo_video", "script_narrativo", "genere", "colonna_sonora"]:
            if field in result and isinstance(result[field], str):
                result[field] = _sanitize_llm_field(result[field], field)
        return result
    except (json.JSONDecodeError, ValueError) as e:
        log(f"  Warning: could not parse synthesis JSON: {e}", "warning")
        # Use raw text as fallback script narrativo
        return {
            "titolo_video": "Analisi Fumetto",
            "genere": "",
            "personaggi_principali": [],
            "colonna_sonora": "",
            "script_narrativo": _sanitize_llm_field(raw[:5000], "script_narrativo"),
            "durata_totale_stimata_minuti": 0,
        }
