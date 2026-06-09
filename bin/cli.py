#!/usr/bin/env python3
"""
Comic Video Maker — Unified CLI (Typer)
========================================
Entry point unificato per tutti i comandi Python del progetto.

Comandi:
    python bin/cli.py analyze <pdf>         — Pipeline completo di analisi
    python bin/cli.py page <num> [pdf]      — Analizza una singola pagina
    python bin/cli.py render <json> <dir>   — Renderizza JSON narrazione in video MP4
    python bin/cli.py bridge                — Avvia il micro-servizio OCR bridge
    python bin/cli.py test-ocr <page>       — Test approfondito OCR su una pagina

Esempi:
    python bin/cli.py analyze "fumetto.pdf" -o output -m qwen2.5vl:7b
    python bin/cli.py page 7 ./mio-fumetto.pdf
    python bin/cli.py render narrazione.json pages/ -o video.mp4
    python bin/cli.py render narrazione.json pages/ --voice it-IT-DiegoNeural
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
from comic_video.renderer import render_narration_video, get_narration_info
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
    page_json: bool = typer.Option(True, "--page-json/--no-page-json", help="Genera output page-by-page nel formato finale"),
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
            page_json=page_json,
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


@app.command(name="render")
def cmd_render(
    json_file: str = typer.Argument(..., help="Path al file JSON di narrazione"),
    pages_dir: str = typer.Argument(..., help="Directory con le immagini delle pagine"),
    output: str = typer.Option("output/video.mp4", "-o", "--output", help="Path video di output"),
    voice: str = typer.Option("it-IT-DiegoNeural", "--voice", help="Voce edge-tts (it-IT-DiegoNeural, it-IT-ElsaNeural)"),
    voice_rate: str = typer.Option("-30%", "--rate", help="Velocita voce (es. -30% = piu' lento)"),
    voice_pitch: str = typer.Option("-8Hz", "--pitch", help="Tono voce (es. -8Hz = piu' grave)"),
    fps: int = typer.Option(24, "--fps", help="Frame per second"),
    transition: float = typer.Option(0.8, "--transition", help="Durata transizione tra pagine (sec)"),
    no_subtitles: bool = typer.Option(False, "--no-subtitles", help="Disabilita sottotitoli"),
    tts_workers: int = typer.Option(3, "--tts-workers", help="Numero di TTS in parallelo"),
    chunk_size: int = typer.Option(3, "--chunk-size", help="Numero di pagine per chunk renderizzato in parallelo"),
    chunk_workers: int = typer.Option(2, "--chunk-workers", help="Numero di chunk renderizzati in parallelo"),
    fast_render: bool = typer.Option(False, "--fast-render", help="Riduce la qualità per velocizzare il render"),
    no_blur: bool = typer.Option(False, "--no-blur", help="Disabilita il background blur per velocizzare il render"),
    pages: Optional[str] = typer.Option(None, "--pages", help="Range pagine (es. 1-10)"),
    intro: Optional[str] = typer.Option(None, "--intro", help="Testo intro da leggere all'inizio"),
    outro: Optional[str] = typer.Option(None, "--outro", help="Testo outro da leggere alla fine"),
    info_only: bool = typer.Option(False, "--info", help="Mostra solo info sul JSON senza renderizzare"),
):
    """Renderizza un JSON di narrazione in video MP4 con voiceover.
    
    Esempio:
        python bin/cli.py render narrazione.json pages/ -o video.mp4
        python bin/cli.py render narrazione.json pages/ --voice it-IT-DiegoNeural
        python bin/cli.py render narrazione.json pages/ --info
    """
    try:
        # Mostra info se richiesto
        if info_only:
            info = get_narration_info(json_file)
            typer.echo(f"\nTitolo: {info['titolo']}")
            typer.echo(f"Pagine: {info['num_pagine']}")
            typer.echo(f"Pagine elenco: {info['pagine']}")
            typer.echo(f"Totale parole: {info['totale_parole']}")
            typer.echo(f"Durata stimata: {info['durata_stimata_minuti']} min ({info['durata_stimata_secondi']} sec)")
            raise typer.Exit()
        
        # Renderizza
        render_fps = 15 if fast_render else fps
        render_transition = 0.0 if fast_render else transition
        render_narration_video(
            json_path=json_file,
            pages_dir=pages_dir,
            output_path=output,
            voice=voice,
            voice_rate=voice_rate,
            voice_pitch=voice_pitch,
            fps=render_fps,
            transition_duration=render_transition,
            with_subtitles=not no_subtitles,
            page_range=pages,
            intro_text=intro,
            outro_text=outro,
            tts_workers=tts_workers,
            use_blur=not no_blur,
            chunk_size=chunk_size,
            chunk_workers=chunk_workers,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
