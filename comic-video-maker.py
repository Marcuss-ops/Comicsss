#!/usr/bin/env python3
"""
COMIC VIDEO MAKER — CLI Tool
=============================
Prende un PDF di un fumetto, estrae le pagine come immagini,
le analizza con un modello LLM locale via Ollama (con supporto visione),
e genera uno script narrativo completo per video YouTube.

Analisi in BATCH: invia 3-4 immagini per chiamata Ollama per velocizzare il processo.

Esempio:
    python comic-video-maker.py "fumetto.pdf" -o output --batch-size 4
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

import requests
from PIL import Image
import fitz  # PyMuPDF

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_OUTPUT_DIR = "output"
PAGE_IMAGE_FORMAT = "PNG"
PAGE_DPI = 200  # DPI for PDF rendering — good balance quality/speed
MAX_IMAGE_SIZE = (2048, 2048)  # Resize if larger to save tokens
BATCH_SIZE_DEFAULT = 4  # Default pages per Ollama call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

console = Console() if RICH_AVAILABLE else None


def log(msg: str, style: str = "info"):
    """Print a colored log message if rich is available."""
    # Safe encoding for Windows console
    safe_msg = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
    if console:
        try:
            if style == "info":
                console.print(f"[bold cyan]>>[/] {safe_msg}")
            elif style == "success":
                console.print(f"[bold green]OK[/] {safe_msg}")
            elif style == "warning":
                console.print(f"[bold yellow]!![/] {safe_msg}")
            elif style == "error":
                console.print(f"[bold red]XX[/] {safe_msg}")
            elif style == "header":
                console.print(Panel(safe_msg, style="bold magenta"))
            else:
                print(f"  {safe_msg}")
        except (UnicodeEncodeError, UnicodeError):
            print(f"  [{style.upper()}] {safe_msg}")
    else:
        print(f"  [{style.upper()}] {safe_msg}")


def progress_bar(iterable, description: str = "Processing", total: Optional[int] = None):
    """Wrap an iterable with a progress bar if rich is available."""
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ).track(iterable, description=description, total=total)
    return iterable


def image_to_base64(image: Image.Image) -> str:
    """Convert a PIL Image to base64-encoded PNG."""
    import io
    buf = io.BytesIO()
    image.save(buf, format=PAGE_IMAGE_FORMAT)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def resize_image_if_needed(image: Image.Image) -> Image.Image:
    """Resize image if it exceeds MAX_IMAGE_SIZE (to save tokens)."""
    w, h = image.size
    max_w, max_h = MAX_IMAGE_SIZE
    if w > max_w or h > max_h:
        ratio = min(max_w / w, max_h / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        image = image.resize((new_w, new_h), Image.LANCZOS)
        log(f"  Image resized to {new_w}x{new_h} (was {w}x{h})", "info")
    return image


# ---------------------------------------------------------------------------
# PDF Extraction
# ---------------------------------------------------------------------------

def extract_pdf_pages(pdf_path: str, output_dir: str, dpi: int = PAGE_DPI) -> list[dict]:
    """
    Extract each page of a PDF as an image file.
    Returns a list of dicts: [{page_num, path, image}, ...]
    Saves pixmap directly to avoid in-memory corruption issues.
    """
    log(f"Opening PDF: {pdf_path}", "info")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    log(f"Total pages: {total_pages}", "info")

    pages_dir = Path(output_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    extracted = []
    for page_num in range(total_pages):
        try:
            page = doc.load_page(page_num)
            zoom = dpi / 72  # 72 is the default PDF resolution
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Save directly from pixmap (avoids BytesIO corruption risk)
            img_path = pages_dir / f"page_{page_num + 1:04d}.png"
            pix.save(str(img_path))

            # Load as PIL Image for analysis
            img = Image.open(str(img_path))
            img = resize_image_if_needed(img)

            extracted.append({
                "page_num": page_num + 1,
                "path": str(img_path),
                "image": img,  # PIL Image
            })

            log(f"  Page {page_num + 1}/{total_pages} extracted", "info")

        except Exception as e:
            log(f"  Warning: could not extract page {page_num + 1}: {e}", "warning")
            # Try with lower DPI as fallback
            try:
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))  # 72 DPI fallback
                img_path = pages_dir / f"page_{page_num + 1:04d}.png"
                pix.save(str(img_path))
                img = Image.open(str(img_path))
                extracted.append({
                    "page_num": page_num + 1,
                    "path": str(img_path),
                    "image": img,
                })
                log(f"  Page {page_num + 1} extracted at low DPI (fallback)", "info")
            except Exception as e2:
                log(f"  Skipping page {page_num + 1}: {e2}", "error")

    doc.close()
    log(f"Extracted {len(extracted)} pages to {pages_dir}", "success")
    return extracted


# ---------------------------------------------------------------------------
# Ollama API
# ---------------------------------------------------------------------------

def call_ollama(
    model: str,
    prompt: str,
    images: Optional[list[str]] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    temperature: float = 0.3,
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
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Sei un esperto narratore di fumetti italiano. Analizzi ogni pagina del fumetto "{comic_title}" e produci una descrizione narrativa dettagliata, coinvolgente e pronta per essere usata come voiceover per un video YouTube.

IDENTIFICA SEMPRE I VERI PERSONAGGI DEL FUMETTO guardando le immagini. Non inventare nomi di personaggi. Usa i NOMI REALI dei personaggi del fumetto (es. Batman, Joker, Robin, Harley Quinn, ecc.) basandoti su ciò che vedi nelle immagini.

Per OGNI pagina devi produrre:

1. **TITOLO_SCENA**: Un titolo breve e drammatico per questa pagina.
2. **DESCRIZIONE_NARRATIVA**: Una descrizione RICCA e DETTAGLIATA (minimo 100-150 parole) in italiano semplice e coinvolgente. Descrivi:
   - Cosa succede visivamente nella pagina (ambientazione, azioni, espressioni)
   - I personaggi presenti e cosa stanno facendo (usa i LORO VERI NOMI)
   - L'atmosfera e le emozioni trasmesse
   - Il significato psicologico/profondo della scena
   - Scrivi come un appassionato YouTuber che spiega il fumetto ai suoi fan
3. **PERSONAGGI**: Elenco dei personaggi presenti separati da virgola (USA I VERI NOMI).
4. **DIALOGHI**: Trascrizione dei dialoghi presenti, indicando chi parla.
5. **EFFETTO_SONORO**: Un effetto sonoro onomatopeico che rappresenta la scena (BOOM, WHOOSH, CRASH, ecc.)
6. **DURATA_STIMATA**: Secondi stimati per la narrazione (tra 8 e 20 secondi)

REGOLE IMPORTANTI:
- Scrivi SEMPRE in ITALIANO, usando parole semplici e comprensibili
- Non usare MAI il carattere '/' (barra) — scrivi "e" o "o" invece
- Non usare caratteri accentati corrotti — usa sempre UTF-8 pulito (à, è, é, ì, ò, ù corretti)
- Sii coinvolgente e drammatico, come un vero storyteller
- Descrivi anche ciò che NON è detto esplicitamente: le emozioni dei personaggi, il sottotesto
- Collega le scene tra loro per creare una narrazione fluida
- Per pagine senza dialoghi, descrizioni atmosferiche accurate
- **NON INVENTARE PERSONAGGI** — usa solo i personaggi che vedi realmente nelle immagini

FORMATO RISPOSTA (solo questo JSON, nient'altro):
{
  "titolo_scena": "...",
  "descrizione_narrativa": "...",
  "personaggi": "...",
  "dialoghi": "...",
  "effetto_sonoro": "...",
  "durata_stimata": 10
}"""

BATCH_PROMPT_TEMPLATE = """Sei un esperto narratore di fumetti italiano con capacità di analisi multipla.

Stai analizzando il fumetto "{comic_title}".
Ti vengono mostrate PIU' PAGINE consecutive, in ordine numerico.
La PRIMA immagine corrisponde alla pagina {start_page}, e così via per {num_pages} pagine.

IDENTIFICA SEMPRE I VERI PERSONAGGI DEL FUMETTO guardando le immagini. Non inventare nomi. Usa i NOMI REALI (es. Batman, Joker, Robin, Harley Quinn, ecc.) basandoti su ciò che vedi.

Devi analizzare OGNI pagina INDIVIDUALMENTE e produrre una descrizione narrativa dettagliata per ciascuna.

Per ogni pagina devi includere:
1. titolo_scena: Un titolo breve e drammatico
2. descrizione_narrativa: Descrizione RICCA (minimo 100 parole) in italiano, come per un voiceover YouTube
3. personaggi: Elenco personaggi separati da virgola (USA I VERI NOMI)
4. dialoghi: Dialoghi indicando chi parla
5. effetto_sonoro: Effetto onomatopeico (BOOM, WHOOSH, ecc.)
6. durata_stimata: Secondi (8-20)

REGOLE:
- Scrivi SEMPRE in ITALIANO
- Non usare MAI il carattere '/'
- Usa solo UTF-8 pulito
- **NON INVENTARE PERSONAGGI** — usa solo quelli che vedi realmente
- Analizza OGNI pagina individualmente in sequenza
- Le immagini sono in ordine numerico: pagina {start_page}, {start_page_plus_1}, ...

Rispondi SOLO con un array JSON contenente ESATTAMENTE {num_pages} oggetti (uno per pagina):
{json_template}"""

FINAL_SYNTHESIS_PROMPT = """Sei un regista e narratore che deve creare lo script finale per un video YouTube sul fumetto "{comic_title}".

Hai a disposizione le analisi dettagliate di TUTTE le pagine del fumetto (in formato JSON qui sotto).

Il tuo compito è:
1. Leggere tutte le descrizioni delle pagine
2. Creare uno SCRIPT NARRATIVO UNICO E COESO che:
   - Racconti l'intera storia dall'inizio alla fine
   - Sia scritto in ITALIANO semplice e coinvolgente
   - Sia lungo circa 2000-4000 parole (abbastanza per un video di 10-20 minuti)
   - Includa i dialoghi importanti dei personaggi
   - Spieghi la psicologia dei personaggi e il significato della storia
   - Sia pronto per essere letto da un narratore/voce fuori campo
   - Non usi MAI il carattere '/' (scrivi "e" o "o")
   - Usi solo UTF-8 pulito (senza caratteri accentati corrotti)
   - **USA I VERI NOMI DEI PERSONAGGI** (es. Batman, Joker, Robin, Barbara Gordon, ecc.)
3. Determinare il titolo del video, i personaggi principali, il genere
4. Suggerire uno stile di colonna sonora

FORMATO RISPOSTA (SOLO JSON):
{
  "titolo_video": "...",
  "genere": "...",
  "personaggi_principali": ["..."],
  "colonna_sonora": "...",
  "script_narrativo": "TESTO COMPLETO DELLO SCRIPT...",
  "durata_totale_stimata_minuti": 15
}

SCRIPT NARRATIVO - RACCOMANDAZIONI:
- Inizia con un'introduzione che catturi l'attenzione ("Benvenuti ragazzi! Oggi analizziamo...")
- Racconta la scena per scena, seguendo l'ordine cronologico del fumetto
- Ogni paragrafo dovrebbe descrivere una scena/pagina importante
- Alterna descrizione visiva, dialoghi e riflessioni psicologiche
- Verso la fine, fai un'analisi complessiva del significato della storia
- Concludi con una riflessione personale e un invito a commentare
- Deve sembrare un vero script di un canale YouTube di divulgazione fumettistica"""


# ---------------------------------------------------------------------------
# Page Analysis — Single
# ---------------------------------------------------------------------------

def analyze_page(
    model: str,
    page_data: dict,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 600,
    context: str = "",
    comic_title: str = "",
) -> dict:
    """
    Send a single page image to Ollama and get structured analysis.
    """
    page_num = page_data["page_num"]
    img = page_data["image"]

    # Convert to base64
    b64_image = image_to_base64(img)

    # Inject comic_title into SYSTEM_PROMPT
    sys_prompt = SYSTEM_PROMPT.format(comic_title=comic_title)

    # Build prompt
    if context:
        prompt = f"""CONTESTO DELLA PAGINA PRECEDENTE:
{context}

Ora analizza QUESTA PAGINA (Pagina {page_num}) del fumetto "{comic_title}" seguendo le istruzioni originali. Produci il JSON richiesto."""
    else:
        prompt = f"""{sys_prompt.split('REGOLE IMPORTANTI')[0]}

REGOLE IMPORTANTI:
- Scrivi SEMPRE in ITALIANO
- Non usare MAI il carattere '/'
- Usa solo UTF-8 pulito
- Sii coinvolgente e drammatico
- NON INVENTARE PERSONAGGI — usa i veri nomi dei personaggi del fumetto
- Produci SOLO il JSON, nient'altro"""

    log(f"  Analyzing page {page_num}...", "info")

    response_text = call_ollama(
        model=model,
        prompt=prompt,
        images=[b64_image],
        ollama_url=ollama_url,
        timeout=timeout,
    )

    # Extract JSON from response
    result = parse_json_response(response_text, page_num)
    result["page_num"] = page_num
    return result


# ---------------------------------------------------------------------------
# Page Analysis — Batch (multiple pages in one call)
# ---------------------------------------------------------------------------

def analyze_batch(
    model: str,
    batch_pages: list[dict],
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 600,
    comic_title: str = "",
) -> list[dict]:
    """
    Send MULTIPLE page images in a single Ollama call for analysis.
    Returns a list of analysis dicts, one per page.
    The prompt template is dynamically generated with N JSON slots to match batch size.
    """
    start_page = batch_pages[0]["page_num"]
    end_page = batch_pages[-1]["page_num"]
    num_pages = len(batch_pages)

    log(f"  Batch pages {start_page}-{end_page} ({num_pages} pages)...", "info")

    # Convert all images to base64
    b64_images = [image_to_base64(p["image"]) for p in batch_pages]

    # Build dynamic JSON template with EXACTLY N items (one per image)
    json_items = []
    for i in range(num_pages):
        pn = start_page + i
        json_items.append(f'''  {{
    "page_num": {pn},
    "titolo_scena": "...",
    "descrizione_narrativa": "...",
    "personaggi": "...",
    "dialoghi": "...",
    "effetto_sonoro": "...",
    "durata_stimata": 12
  }}''')
    json_template = "[\n" + ",\n".join(json_items) + "\n]"

    # Build batch prompt
    prompt = BATCH_PROMPT_TEMPLATE.format(
        comic_title=comic_title,
        start_page=start_page,
        start_page_plus_1=start_page + 1,
        num_pages=num_pages,
        json_template=json_template,
    )

    response_text = call_ollama(
        model=model,
        prompt=prompt,
        images=b64_images,
        ollama_url=ollama_url,
        timeout=timeout,
    )

    # Parse the response as a JSON array
    results = parse_batch_json_response(response_text, batch_pages)
    return results


def parse_batch_json_response(text: str, batch_pages: list[dict]) -> list[dict]:
    """
    Parse a JSON array response from batch analysis.
    Falls back to individual page parsing if array parsing fails.
    """
    # Try to find JSON array between ``` markers
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find anything that looks like [ ... ]
        json_match = re.search(r'(\[[\s\S]*\])', text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = text.strip()

    # Clean common issues
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        parsed_list = json.loads(json_str)
        if isinstance(parsed_list, list):
            results = []
            for item in parsed_list:
                pn = item.get("page_num", 0)
                defaults = {
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
        log(f"  Warning: could not parse batch JSON array, falling back to single-page parse", "warning")
        log(f"  Raw response (first 300 chars): {text[:300]}", "warning")

    # Fallback: try to parse individual objects from the response
    log(f"  Warning: batch parsing failed, falling back to single-object extraction. "
        f"All pages in this batch may get similar descriptions.", "warning")
    results = []
    for page_data in batch_pages:
        pn = page_data["page_num"]
        result = parse_json_response(text, pn)
        result["page_num"] = pn
        results.append(result)

    return results


def parse_json_response(text: str, page_num: int) -> dict:
    """Extract JSON from the model response, handling markdown fences."""
    # Try to find JSON between ``` markers
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find anything that looks like { ... }
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = text.strip()

    # Clean common issues
    json_str = re.sub(r',\s*}', '}', json_str)  # trailing commas
    json_str = re.sub(r',\s*]', ']', json_str)  # trailing commas in arrays

    try:
        result = json.loads(json_str)
        # Ensure all expected fields exist
        defaults = {
            "titolo_scena": f"Pagina {page_num}",
            "descrizione_narrativa": text[:500],
            "personaggi": "",
            "dialoghi": "",
            "effetto_sonoro": "",
            "durata_stimata": 10,
        }
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
        return result
    except json.JSONDecodeError:
        log(f"  Warning: could not parse JSON from response for page {page_num}", "warning")
        log(f"  Raw response (first 200 chars): {text[:200]}", "warning")
        return {
            "page_num": page_num,
            "titolo_scena": f"Pagina {page_num}",
            "descrizione_narrativa": text.strip() or f"(Nessuna descrizione disponibile per la pagina {page_num})",
            "personaggi": "",
            "dialoghi": "",
            "effetto_sonoro": "",
            "durata_stimata": 10,
        }


# ---------------------------------------------------------------------------
# Final Synthesis
# ---------------------------------------------------------------------------

def synthesize_video_script(
    model: str,
    analyses: list[dict],
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 600,
    comic_title: str = "",
) -> dict:
    """
    Combine all page analyses and ask the model to create a cohesive video script.
    """
    log("Synthesizing final video script...", "header")

    # Build context from all analyses
    context_parts = []
    for analysis in analyses:
        page_text = json.dumps(analysis, ensure_ascii=False, indent=2)
        context_parts.append(f"=== PAGINA {analysis['page_num']} ===\n{page_text}")

    full_context = "\n\n".join(context_parts)

    # Check total length — if too long, sample pages
    if len(full_context) > 50000:
        log("  Many pages detected, using sampling for synthesis...", "warning")
        # Take first pages, some middle pages, and last pages
        n = len(analyses)
        sampled = []
        sampled.append(analyses[0])
        for i in range(1, n - 1, max(1, n // 5)):
            sampled.append(analyses[i])
        if n > 1:
            sampled.append(analyses[-1])
        context_parts = []
        for analysis in sampled:
            page_text = json.dumps(analysis, ensure_ascii=False, indent=2)
            context_parts.append(f"=== PAGINA {analysis['page_num']} ===\n{page_text}")
        full_context = "\n\n".join(context_parts)

    prompt = f"""{FINAL_SYNTHESIS_PROMPT.format(comic_title=comic_title)}

Ecco l'analisi completa delle pagine del fumetto "{comic_title}":

{full_context}

Producimi ora lo script video finale nel formato JSON richiesto."""

    response_text = call_ollama(
        model=model,
        prompt=prompt,
        ollama_url=ollama_url,
        temperature=0.4,
        timeout=timeout,
    )

    # Parse the JSON response
    result = parse_synthesis_json(response_text)
    return result


def parse_synthesis_json(text: str) -> dict:
    """Parse the final synthesis JSON."""
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = text.strip()

    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        result = json.loads(json_str)
        required = ["titolo_video", "script_narrativo"]
        for key in required:
            if key not in result:
                result[key] = f"(MISSING: {key})"
        return result
    except json.JSONDecodeError:
        log("  Warning: could not parse synthesis JSON, using raw text", "warning")
        return {
            "titolo_video": "Analisi Fumetto",
            "genere": "",
            "personaggi_principali": [],
            "colonna_sonora": "",
            "script_narrativo": text.strip(),
            "durata_totale_stimata_minuti": 0,
        }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_output(
    analyses: list[dict],
    synthesis: dict,
    output_dir: str,
    pdf_name: str,
):
    """Save all output files."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    base_name = Path(pdf_name).stem

    # 1. Save full data as JSON
    full_data = {
        "fonte": pdf_name,
        "analisi_pagine": analyses,
        "script_video": synthesis,
    }
    json_path = out_path / f"{base_name}_analisi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    log(f"Saved structured data: {json_path}", "success")

    # 2. Save video script as TXT
    script_text = synthesis.get("script_narrativo", "")
    if script_text:
        txt_path = out_path / f"{base_name}_script_video.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"""{"=" * 60}
TITOLO: {synthesis.get('titolo_video', 'N/D')}
GENERE: {synthesis.get('genere', 'N/D')}
COLONNA SONORA: {synthesis.get('colonna_sonora', 'N/D')}
DURATA STIMATA: {synthesis.get('durata_totale_stimata_minuti', '?')} minuti
PERSONAGGI: {', '.join(synthesis.get('personaggi_principali', []))}
{"=" * 60}

{script_text}

{"=" * 60}
Script generato automaticamente da Comic Video Maker CLI
Modello: {DEFAULT_MODEL}
Fonte: {pdf_name}
{"=" * 60}
""")
        log(f"Saved video script: {txt_path}", "success")

    # 3. Save per-page scripts
    pages_script_path = out_path / f"{base_name}_script_pagine.txt"
    with open(pages_script_path, "w", encoding="utf-8") as f:
        for i, a in enumerate(analyses):
            f.write(f"""{"=" * 60}
PAGINA {a['page_num']} — {a.get('titolo_scena', f'Scena {i+1}')}
{"=" * 60}

🎬 DESCRIZIONE NARRATIVA:
{a.get('descrizione_narrativa', 'N/D')}

💬 DIALOGHI:
{a.get('dialoghi', 'N/D')}

👥 PERSONAGGI: {a.get('personaggi', 'N/D')}
🔊 EFFETTO SONORO: {a.get('effetto_sonoro', 'N/D')}!
⏱ DURATA: {a.get('durata_stimata', 10)} secondi

""")
    log(f"Saved per-page script: {pages_script_path}", "success")

    return json_path, txt_path


def print_summary(analyses: list[dict], synthesis: dict, elapsed: float):
    """Print a terminal summary."""
    if not RICH_AVAILABLE:
        print(f"\n--- SUMMARY ---")
        print(f"Pages analyzed: {len(analyses)}")
        print(f"Video title: {synthesis.get('titolo_video', 'N/D')}")
        print(f"Duration: {synthesis.get('durata_totale_stimata_minuti', '?')} min")
        print(f"Time elapsed: {elapsed:.1f}s")
        return

    table = Table(title="Analysis Complete", style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Pages Analyzed", str(len(analyses)))
    table.add_row("Video Title", synthesis.get("titolo_video", "N/D"))
    table.add_row("Genre", synthesis.get("genere", "N/D"))
    table.add_row("Soundtrack", synthesis.get("colonna_sonora", "N/D"))
    table.add_row("Est. Duration", f"{synthesis.get('durata_totale_stimata_minuti', '?')} minutes")
    table.add_row("Characters", ", ".join(synthesis.get("personaggi_principali", [])))
    table.add_row("Time Elapsed", f"{elapsed:.1f} seconds")

    console.print(table)


# ---------------------------------------------------------------------------
# Batch Helper
# ---------------------------------------------------------------------------

def chunk_pages(pages: list[dict], batch_size: int) -> list[list[dict]]:
    """Split pages into chunks of batch_size."""
    return [pages[i:i + batch_size] for i in range(0, len(pages), batch_size)]


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def extract_comic_title_from_filename(filename: str) -> str:
    """
    Extract a readable comic title from the PDF filename.
    E.g. '4fumetti-ita-batman-the-killing-joke-dc.pdf' -> 'Batman: The Killing Joke'
    """
    stem = Path(filename).stem
    # Remove common prefixes like '4fumetti-ita-', 'ita-', etc.
    name = re.sub(r'^[\d]*fumetti[-_]*', '', stem, flags=re.IGNORECASE)
    name = re.sub(r'^ita[-_]', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]dc$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]eng$', '', name, flags=re.IGNORECASE)
    # Replace hyphens and underscores with spaces, capitalize
    name = name.replace('-', ' ').replace('_', ' ')
    # Capitalize each word
    name = ' '.join(w.capitalize() if w.lower() not in ('the', 'a', 'an', 'of', 'in', 'and') else w for w in name.split())
    return name.strip() or Path(filename).stem


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Comic Video Maker — Analizza fumetti PDF con LLM locale e genera script video YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s "4fumetti-ita-batman-the-killing-joke-dc.pdf"
  %(prog)s "fumetto.pdf" -o analisi -m llama3.2-vision --ollama-url http://localhost:11434
  %(prog)s "fumetto.pdf" --pages 1-10 --no-synthesis
  %(prog)s "fumetto.pdf" --batch-size 4
  %(prog)s "fumetto.pdf" --title "Batman: The Killing Joke"
  %(prog)s "fumetto.pdf" --dry-run  (solo estrai pagine, non analizzare)
        """,
    )

    parser.add_argument(
        "pdf",
        type=str,
        help="Percorso del file PDF del fumetto",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory di output (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Modello Ollama da usare (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=DEFAULT_OLLAMA_URL,
        help=f"URL del server Ollama (default: {DEFAULT_OLLAMA_URL})",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Pagine da elaborare, es. '1-10' o '1,3,5-7' (default: tutte)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE_DEFAULT,
        help=f"Pagine da analizzare in ogni chiamata Ollama (default: {BATCH_SIZE_DEFAULT})",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=PAGE_DPI,
        help=f"DPI per l'estrazione delle pagine (default: {PAGE_DPI})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in secondi per ogni chiamata API a Ollama (default: 600 = 10 minuti)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Temperature per il modello (default: 0.3)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Titolo del fumetto (es. 'Batman: The Killing Joke'). Se non specificato, viene estratto automaticamente dal nome del file.",
    )
    parser.add_argument(
        "--no-synthesis",
        action="store_true",
        help="Salta la sintesi finale dello script video completo",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo estrai le pagine, non chiamare Ollama",
    )
    parser.add_argument(
        "--keep-images",
        action="store_true",
        help="Mantieni le immagini delle pagine dopo l'analisi",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Comic Video Maker v1.0.0",
    )

    args = parser.parse_args()

    # Validate PDF
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        log(f"File not found: {pdf_path}", "error")
        sys.exit(1)
    if pdf_path.suffix.lower() not in (".pdf",):
        log(f"File must be a PDF: {pdf_path}", "error")
        sys.exit(1)

    # Determine comic title
    comic_title = args.title if args.title else extract_comic_title_from_filename(args.pdf)

    start_time = time.time()

    # Header
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold magenta]COMIC VIDEO MAKER[/]\n"
            "[white]Analisi automatica di fumetti PDF con LLM locale[/]\n"
            f"[dim]Modello: {args.model} | Batch: {args.batch_size} pagine/call | Titolo: {comic_title}[/]",
            border_style="magenta",
        ))
    else:
        print("=" * 60)
        print("COMIC VIDEO MAKER")
        print(f"Modello: {args.model} | Batch: {args.batch_size} | Titolo: {comic_title}")
        print("=" * 60)

    # Step 1: Extract PDF pages
    log("Step 1/3: Extracting PDF pages...", "header")
    extracted = extract_pdf_pages(str(pdf_path), args.output, args.dpi)

    if args.dry_run:
        log("Dry-run mode — pages extracted, no analysis performed.", "success")
        log(f"Pages saved to: {Path(args.output) / 'pages'}", "info")
        return

    # Parse page range
    if args.pages:
        selected_pages = parse_page_range(args.pages, len(extracted))
        extracted = [p for p in extracted if p["page_num"] in selected_pages]
        log(f"Selected {len(extracted)} pages for analysis", "info")

    # Step 2: Analyze pages in BATCHES with Ollama
    log("Step 2/3: Analyzing pages with Ollama (batch mode)...", "header")
    log(f"Model: {args.model} | Batch size: {args.batch_size} pages/call | Comic: {comic_title}", "info")

    # Split pages into batches
    batches = chunk_pages(extracted, args.batch_size)
    log(f"Split {len(extracted)} pages into {len(batches)} batches", "info")

    analyses = []
    for batch_idx, batch in enumerate(batches):
        batch_start = batch[0]["page_num"]
        batch_end = batch[-1]["page_num"]
        try:
            log(f"Batch {batch_idx + 1}/{len(batches)} (pages {batch_start}-{batch_end})...", "info")

            if len(batch) == 1:
                # Single page: use individual analysis
                result = analyze_page(args.model, batch[0], args.ollama_url, timeout=args.timeout, comic_title=comic_title)
                analyses.append(result)
                if RICH_AVAILABLE:
                    console.print(
                        f"  [bold green]Page {batch_start}[/]: "
                        f"[bold white]{result.get('titolo_scena', 'N/D')}[/] "
                        f"[dim]({result.get('personaggi', '?')})[/]"
                    )
                else:
                    print(f"  Page {batch_start}: {result.get('titolo_scena', 'N/D')}")
            else:
                # Multiple pages: use batch analysis
                results = analyze_batch(args.model, batch, args.ollama_url, timeout=args.timeout, comic_title=comic_title)
                for result in results:
                    analyses.append(result)
                    pn = result.get("page_num", "?")
                    if RICH_AVAILABLE:
                        console.print(
                            f"  [bold green]Page {pn}[/]: "
                            f"[bold white]{result.get('titolo_scena', 'N/D')}[/] "
                            f"[dim]({result.get('personaggi', '?')})[/]"
                        )
                    else:
                        print(f"  Page {pn}: {result.get('titolo_scena', 'N/D')}")

        except Exception as e:
            log(f"  Error analyzing batch pages {batch_start}-{batch_end}: {e}", "error")
            for page_data in batch:
                pn = page_data["page_num"]
                analyses.append({
                    "page_num": pn,
                    "titolo_scena": f"Pagina {pn}",
                    "descrizione_narrativa": f"(Errore nell'analisi: {e})",
                    "personaggi": "",
                    "dialoghi": "",
                    "effetto_sonoro": "",
                    "durata_stimata": 10,
                })

        # Small delay between batches
        if batch_idx < len(batches) - 1:
            time.sleep(1)

    # Clean up images unless requested to keep
    if not args.keep_images:
        pages_dir = Path(args.output) / "pages"
        if pages_dir.exists():
            import shutil
            shutil.rmtree(pages_dir)
            log("Cleaned up page images (use --keep-images to retain)", "info")

    if not analyses:
        log("No pages were analyzed successfully.", "error")
        sys.exit(1)

    # Step 3: Synthesize final video script
    if not args.no_synthesis and len(analyses) > 0:
        log("Step 3/3: Creating final video script...", "header")
        try:
            synthesis = synthesize_video_script(args.model, analyses, args.ollama_url, timeout=args.timeout, comic_title=comic_title)
        except Exception as e:
            log(f"Error during synthesis: {e}", "error")
            synthesis = {
                "titolo_video": comic_title,
                "genere": "",
                "personaggi_principali": [],
                "colonna_sonora": "",
                "script_narrativo": "\n\n".join(
                    a.get("descrizione_narrativa", "") for a in analyses
                ),
                "durata_totale_stimata_minuti": sum(a.get("durata_stimata", 10) for a in analyses) // 60,
            }
    else:
        log("Skipping final synthesis (--no-synthesis)", "info")
        synthesis = {
            "titolo_video": comic_title,
            "genere": "",
            "personaggi_principali": [],
            "colonna_sonora": "",
            "script_narrativo": "\n\n".join(
                a.get("descrizione_narrativa", "") for a in analyses
            ),
            "durata_totale_stimata_minuti": sum(a.get("durata_stimata", 10) for a in analyses) // 60,
        }

    # Save outputs
    log("Saving outputs...", "header")
    save_output(analyses, synthesis, args.output, str(pdf_path))

    # Summary
    elapsed = time.time() - start_time
    print_summary(analyses, synthesis, elapsed)

    log("Done! 🎉", "success")


def parse_page_range(range_str: str, total_pages: int) -> list[int]:
    """Parse a page range string like '1-10' or '1,3,5-7'."""
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


if __name__ == "__main__":
    main()
