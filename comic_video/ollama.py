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

# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"


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
    timeout: int = 600,
) -> str:
    """
    Call Ollama generate API with optional images (base64).
    Returns the generated text.
    """
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
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except requests.exceptions.ConnectionError:
            log(f"  Cannot connect to Ollama at {ollama_url} (attempt {attempt+1}/{max_retries})", "error")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
        except requests.exceptions.Timeout:
            log(f"  Ollama request timed out (attempt {attempt+1}/{max_retries})", "warning")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
        except Exception as e:
            log(f"  Ollama API error: {e}", "error")
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

    try:
        result = json.loads(json_str)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        required = ["titolo_video", "script_narrativo"]
        for key in required:
            if key not in result:
                result[key] = f"(MISSING: {key})"
        return result
    except (json.JSONDecodeError, ValueError) as e:
        log(f"  Warning: could not parse synthesis JSON: {e}", "warning")
        # Use raw text as fallback script narrativo
        return {
            "titolo_video": "Analisi Fumetto",
            "genere": "",
            "personaggi_principali": [],
            "colonna_sonora": "",
            "script_narrativo": raw[:5000],
            "durata_totale_stimata_minuti": 0,
        }
