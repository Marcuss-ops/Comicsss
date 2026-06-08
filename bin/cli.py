#!/usr/bin/env python3
"""
Comic Video Maker — Unified CLI (Typer)
========================================
Entry point unificato per tutti i comandi Python del progetto.

Comandi:
    python bin/cli.py analyze <pdf>         — Pipeline completo di analisi
    python bin/cli.py page <num> [pdf]      — Analizza una singola pagina
    python bin/cli.py bridge                — Avvia il micro-servizio OCR bridge
    python bin/cli.py test-ocr <page>       — Test approfondito OCR su una pagina

Esempi:
    python bin/cli.py analyze "fumetto.pdf" -o output -m llava:13b
    python bin/cli.py page 7 ./mio-fumetto.pdf
    python bin/cli.py bridge --port 8081
    python bin/cli.py test-ocr 7
"""

import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from typing import Optional

# Fix encoding per Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from comic_video.commands import run_analyze, run_single_page, run_ocr_test
from comic_video.bridge_server import run_bridge
from comic_video.config import (
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
    BRIDGE_PORT,
    OUTPUT_DIR,
)
from comic_video.ollama import DEFAULT_OLLAMA_URL

def version_callback(value: bool):
    if value:
        typer.echo("Comic Video Maker v4.0.0")
        raise typer.Exit()

app = typer.Typer(
    help="Comic Video Maker — Analizza fumetti PDF con LLM Vision + Panel Detection",
)


@app.callback()
def common(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True, help="Show version and exit."),
):
    pass


@app.command(name="analyze")
def cmd_analyze(
    pdf: str = typer.Argument(..., help="Percorso del PDF del fumetto"),
    output: str = typer.Option(str(OUTPUT_DIR), "-o", "--output", help="Directory output"),
    model: str = typer.Option(OLLAMA_MODEL, "-m", "--model", help="Modello Ollama con vision"),
    ollama_url: str = typer.Option(DEFAULT_OLLAMA_URL, "--ollama-url", help="URL Ollama"),
    pages: Optional[str] = typer.Option(None, "--pages", help="Pagine es. '1-10'"),
    dpi: int = typer.Option(200, "--dpi", help="DPI estrazione immagini"),
    timeout: int = typer.Option(OLLAMA_TIMEOUT_SECONDS, "--timeout", help="Timeout per chiamata API (secondi)"),
    title: Optional[str] = typer.Option(None, "--title", help="Titolo del fumetto"),
    no_synthesis: bool = typer.Option(False, "--no-synthesis", help="Salta sintesi script video"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo estrai pagine + panel detect"),
    dry_run_skip: bool = typer.Option(False, "--dry-run-skip", help="Mostra quali pagine verrebbero saltate (nessuna chiamata LLM)"),
    no_ocr: bool = typer.Option(False, "--no-ocr", help="Disabilita OCR"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Rimuovi immagini dopo analisi"),
    no_panel_detect: bool = typer.Option(False, "--no-panel-detect", help="Disabilita panel detection (analisi pagina intera)"),
    debug_panels: bool = typer.Option(False, "--debug-panels", help="Salva immagini debug con pannelli evidenziati"),
    no_balloon_ocr: bool = typer.Option(False, "--no-balloon-ocr", help="Disabilita rilevamento balloon + OCR"),
    no_skip_no_balloon: bool = typer.Option(False, "--no-skip-no-balloon", help="Analizza TUTTE le pagine anche senza balloon"),
    debug_balloons: bool = typer.Option(False, "--debug-balloons", help="Salva immagini debug con balloon evidenziati"),
    global_analysis: bool = typer.Option(False, "--global-analysis", help="Aggiungi analisi globale della pagina"),
    full_global: bool = typer.Option(False, "--full-global", help="Analisi globale su TUTTE le pagine"),
    scene_json: bool = typer.Option(False, "--scene-json", help="Genera output scene JSON YouTube transcript"),
):
    """Pipeline completo: estrae pagine, rileva pannelli, analizza con LLM, sintetizza script."""
    try:
        run_analyze(
            pdf=pdf,
            output=output,
            model=model,
            ollama_url=ollama_url,
            pages=pages,
            dpi=dpi,
            timeout=timeout,
            title=title,
            no_synthesis=no_synthesis,
            dry_run=dry_run,
            dry_run_skip=dry_run_skip,
            no_ocr=no_ocr,
            no_cache=no_cache,
            no_panel_detect=no_panel_detect,
            debug_panels=debug_panels,
            no_balloon_ocr=no_balloon_ocr,
            no_skip_no_balloon=no_skip_no_balloon,
            debug_balloons=debug_balloons,
            global_analysis=global_analysis,
            full_global=full_global,
            scene_json=scene_json,
        )
    except (FileNotFoundError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(name="page")
def cmd_page(
    page: int = typer.Argument(..., help="Numero della pagina da analizzare"),
    pdf: Optional[str] = typer.Argument(None, help="Percorso del PDF (opzionale)"),
    ollama_url: str = typer.Option(DEFAULT_OLLAMA_URL, "--ollama-url", help="URL Ollama"),
    model: str = typer.Option(OLLAMA_MODEL, "--model", help="Modello Ollama con vision"),
    timeout: int = typer.Option(OLLAMA_TIMEOUT_SECONDS, "--timeout", help="Timeout per chiamata API (secondi)"),
    comic_title: str = typer.Option("Batman: The Killing Joke", "--comic-title", help="Titolo del fumetto"),
):
    """Analizza una singola pagina PNG dal PDF usando panel detection + Ollama vision."""
    try:
        run_single_page(
            page=page,
            pdf=pdf,
            ollama_url=ollama_url,
            model=model,
            timeout=timeout,
            comic_title=comic_title,
        )
    except (FileNotFoundError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(name="bridge")
def cmd_bridge(
    port: int = typer.Option(BRIDGE_PORT, "--port", help="Porta del bridge server"),
):
    """Avvia il micro-servizio FastAPI per OCR dei fumetti."""
    run_bridge(port=port)


@app.command(name="test-ocr")
def cmd_test_ocr(
    page: int = typer.Argument(7, help="Numero della pagina da testare"),
):
    """Test approfondito OCR: mostra balloon rilevati, testo estratto e immagini debug."""
    try:
        run_ocr_test(page_num=page)
    except (FileNotFoundError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
