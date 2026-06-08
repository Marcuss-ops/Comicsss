#!/usr/bin/env python3
"""
COMIC VIDEO MAKER v3 — CLI Tool
================================
Analizza fumetti PDF con LLM Vision + Panel Detection, genera script narrativi.

Pipeline v3:
    1. Estrai pagine PDF come immagini
    2. Per OGNI pagina: rileva pannelli/vignette con OpenCV
    3. Analizza OGNI vignetta SINGOLARMENTE con modello vision (llava:13b)
    4. Nessun "sliding context" — ogni vignetta è autonoma
    5. Sintesi script video finale da TUTTE le analisi

Esempi:
    python comic-video-maker.py "fumetto.pdf"
    python comic-video-maker.py "fumetto.pdf" -m llava:13b --pages 1-10
    python comic-video-maker.py "fumetto.pdf" --no-panel-detect
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

from comic_video.utils import (
    RICH_AVAILABLE,
    console,
    extract_comic_title_from_filename,
    log,
    parse_page_range,
    print_summary_table,
)
from comic_video.extractor import extract_pdf_pages, EASYOCR_AVAILABLE
from comic_video.analyzer import analyze_page_panels, analyze_full_page, synthesize_script, synthesize_scene_json
from comic_video.panel_detector import detect_panels, save_panels_debug
from comic_video.ollama import DEFAULT_OLLAMA_URL

# Rich helpers
if RICH_AVAILABLE:
    from rich.panel import Panel as RichPanel
    from rich.table import Table

# --- Modello vision predefinito (AGGIORNATO!) ---
DEFAULT_MODEL = "llava:13b"


# ---------------------------------------------------------------------------
# Save output
# ---------------------------------------------------------------------------

def save_output(
    panel_analyses: list[dict],
    synthesis: dict,
    output_dir: str,
    pdf_name: str,
    page_panels_map: dict[int, int] = None,
    global_analyses: list[dict] = None,
    scene_script: list[dict] = None,
):
    """
    Salva l'analisi in formato JSON strutturato.

    Args:
        panel_analyses: Lista di analisi per-pannello
        synthesis: Script video sintetizzato
        output_dir: Directory di output
        pdf_name: Nome del file PDF originale
        page_panels_map: Mappa {page_num: numero_pannelli}
        global_analyses: Lista opzionale di analisi globali per-pagina
        scene_script: Lista opzionale di scene YouTube transcript
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    base_name = Path(pdf_name).stem

    full_data = {
        "fonte": pdf_name,
        "modello": "llava:13b + panel detection",
        "riepilogo_pagine": page_panels_map or {},
        "analisi_pannelli": panel_analyses,
        "script_video": synthesis,
    }

    if global_analyses:
        full_data["analisi_globali_pagine"] = global_analyses

    if scene_script:
        full_data["scene_transcript"] = scene_script
        # Salva anche un file separato con solo le scene
        scene_path = out_path / f"{base_name}_youtube_scenes.json"
        total_pages_count = max(page_panels_map.keys()) if page_panels_map else 0
        scene_output = {
            "project": {
                "title": synthesis.get("titolo_video", base_name),
                "language": "it",
                "source_pdf": pdf_name,
                "total_pages": total_pages_count,
                "format": "youtube_transcript_scene_json",
            },
            "scenes": scene_script,
        }
        with open(scene_path, "w", encoding="utf-8") as f:
            json.dump(scene_output, f, ensure_ascii=False, indent=2)
        log(f"Saved scene transcript: {scene_path}", "success")

    json_path = out_path / f"{base_name}_analisi_v4.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    log(f"Saved: {json_path}", "success")
    return json_path


def print_summary(
    panel_analyses: list[dict],
    synthesis: dict,
    page_panels_map: dict[int, int],
    elapsed: float,
    total_panels_analyzed: int,
):
    """Print terminal summary."""
    num_pages = len(page_panels_map)
    total_panels = sum(page_panels_map.values())

    if not RICH_AVAILABLE:
        print(f"\n--- SUMMARY ---")
        print(f"Pages: {num_pages}")
        print(f"Panels detected: {total_panels}")
        print(f"Panels analyzed: {total_panels_analyzed}")
        print(f"Title: {synthesis.get('titolo_video', 'N/D')}")
        print(f"Time: {elapsed:.1f}s")
        return

    table = Table(title="Analysis Complete (v3)", style="bold green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Pages", str(num_pages))
    table.add_row("Panels detected", str(total_panels))
    table.add_row("Panels analyzed", str(total_panels_analyzed))
    table.add_row("Title", synthesis.get("titolo_video", "N/D"))
    table.add_row("Genre", synthesis.get("genere", "N/D"))
    table.add_row("Soundtrack", synthesis.get("colonna_sonora", "N/D"))
    table.add_row("Duration", f"{synthesis.get('durata_totale_stimata_minuti', '?')} min")
    table.add_row("Time", f"{elapsed:.1f}s")
    console.print(table)

    # Panel summary per pagina
    panel_table = Table(title="Panels per page", style="bold cyan")
    panel_table.add_column("Page", style="white")
    panel_table.add_column("Panels", style="cyan")
    for pn in sorted(page_panels_map.keys()):
        panel_table.add_row(str(pn), str(page_panels_map[pn]))
    console.print(panel_table)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Comic Video Maker v3 — Analizza fumetti PDF con LLM Vision + Panel Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s "fumetto.pdf"
  %(prog)s "fumetto.pdf" -o output -m llava:13b
  %(prog)s "fumetto.pdf" --pages 1-10 --no-synthesis
  %(prog)s "fumetto.pdf" --no-panel-detect  (analisi pagina intera)
  %(prog)s "fumetto.pdf" --dry-run
        """,
    )
    parser.add_argument("pdf", type=str, help="Percorso del PDF del fumetto")
    parser.add_argument("-o", "--output", type=str, default="output", help="Directory output")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL,
                        help=f"Modello Ollama con vision (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", type=str, default=DEFAULT_OLLAMA_URL,
                        help=f"URL Ollama (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--pages", type=str, default=None, help="Pagine es. '1-10'")
    parser.add_argument("--dpi", type=int, default=200, help="DPI estrazione")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout per chiamata API (secondi)")
    parser.add_argument("--title", type=str, default=None, help="Titolo fumetto")
    parser.add_argument("--no-synthesis", action="store_true", help="Salta sintesi script")
    parser.add_argument("--dry-run", action="store_true", help="Solo estrai pagine + panel detect")
    parser.add_argument("--dry-run-skip", action="store_true",
                        help="Solo mostra quali pagine verrebbero saltate (nessuna chiamata LLM)")
    parser.add_argument("--no-ocr", action="store_true", help="Disabilita OCR")
    parser.add_argument("--no-cache", action="store_true", help="Rimuovi immagini dopo analisi")
    parser.add_argument("--no-panel-detect", action="store_true",
                        help="Disabilita panel detection (analisi pagina intera, come v2)")
    parser.add_argument("--debug-panels", action="store_true",
                        help="Salva immagini di debug con pannelli evidenziati")
    parser.add_argument("--no-balloon-ocr", action="store_true",
                        help="Disabilita rilevamento balloon + OCR (usa solo LLM per i dialoghi)")
    parser.add_argument("--no-skip-no-balloon", action="store_true",
                        help="Analizza TUTTE le pagine anche quelle senza balloon (default: salta intro/credits)")
    parser.add_argument("--debug-balloons", action="store_true",
                        help="Salva immagini debug con balloon evidenziati e testi OCR")
    parser.add_argument("--global-analysis", action="store_true",
                        help="Aggiungi analisi GLOBALE della pagina (atmosfera, composizione) oltre ai pannelli")
    parser.add_argument("--full-global", action="store_true",
                        help="Analisi globale su TUTTE le pagine (default: ogni 5 pagine per risparmiare chiamate)")
    parser.add_argument("--scene-json", action="store_true",
                        help="Genera output scene JSON formato YouTube transcript (scena per scena)")
    parser.add_argument("--version", action="version", version="Comic Video Maker v4.0.0")

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        log(f"File not found: {pdf_path}", "error")
        sys.exit(1)

    comic_title = args.title or extract_comic_title_from_filename(args.pdf)
    start_time = time.time()

    # Ottieni il numero TOTALE di pagine del PDF (serve per classificare i credits)
    import fitz
    temp_doc = fitz.open(str(pdf_path))
    total_pdf_pages = len(temp_doc)
    temp_doc.close()

    # Header
    if RICH_AVAILABLE:
        console.print(RichPanel.fit(
            f"[bold magenta]COMIC VIDEO MAKER v3[/]\n"
            f"[white]Panel Detection + LLM Vision — Stile YouTube Narrativo[/]\n"
            f"[dim]Modello: {args.model} | Panel Detection: {'OFF' if args.no_panel_detect else 'ON'} | "
            f"Titolo: {comic_title}[/]",
            border_style="magenta",
        ))
    else:
        print("=" * 60)
        print(f"COMIC VIDEO MAKER v3 — {comic_title}")
        print(f"Modello: {args.model} | Panel Detection: {'OFF' if args.no_panel_detect else 'ON'}")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Extract pages from PDF
    # ------------------------------------------------------------------
    log("Step 1/3: Extracting PDF pages...", "header")
    use_ocr = not args.no_ocr and EASYOCR_AVAILABLE
    if use_ocr:
        log("  OCR enabled (EasyOCR)", "info")

    requested_set = None
    if args.pages:
        selected = parse_page_range(args.pages, total_pdf_pages)
        requested_set = set(selected)
        log(f"  Will extract {len(requested_set)}/{total_pdf_pages} pages", "info")

    extracted = extract_pdf_pages(
        str(pdf_path), args.output, args.dpi,
        use_ocr=use_ocr, requested_pages=requested_set,
    )

    # ------------------------------------------------------------------
    # Dry-run-skip: mostra quali pagine verrebbero saltate senza chiamare LLM
    # ------------------------------------------------------------------
    if args.dry_run_skip:
        log("Dry-run-skip: checking which pages would be skipped (no LLM calls)...", "header")
        log(f"Model: {args.model} | Panel detection: {'ON' if not args.no_panel_detect else 'OFF'}", "info")

        if args.no_balloon_ocr:
            log("  ⚠️  --no-balloon-ocr attivo: lo skip NON funzionerà nell'esecuzione reale!", "warning")

        from comic_video.balloon_detector import detect_balloons_in_panel

        pages_analyzed = []
        pages_skipped = []
        total_savings = 0

        for page_data in extracted:
            page_num = page_data["page_num"]
            page_image = page_data["image"]

            # Panel detection
            panels = _detect_page_panels(page_image, page_num, args.no_panel_detect)

            # Balloon detection per panel
            page_has_balloons = False
            balloon_texts = []
            for panel in panels:
                balloons, text = detect_balloons_in_panel(panel.image)
                balloon_texts.append((len(balloons), text[:60] if text else ""))
                if text.strip():
                    page_has_balloons = True

            # Classifica (usa len(extracted) come totale pagine)
            if not page_has_balloons:
                if page_num == 1:
                    tipo = "copertina"
                elif page_num <= 3:
                    tipo = "intro"
                elif total_pdf_pages > 0 and page_num >= total_pdf_pages - 2:
                    tipo = "credits"
                else:
                    tipo = "no_dialogo"
                pages_skipped.append((page_num, len(panels), tipo))
                total_savings += len(panels)
            else:
                pages_analyzed.append((page_num, len(panels), balloon_texts))

        # Stampa risultati
        log(f"{'='*60}", "info")
        log(f"DRY-RUN SKIP RESULTS for: {comic_title}", "header")
        log(f"{'='*60}", "info")

        if pages_analyzed:
            log(f"\n✅ PAGINE DA ANALIZZARE ({len(pages_analyzed)}):", "success")
            for pn, num_panels, btexts in pages_analyzed:
                balloons_summary = "; ".join(
                    f"panel {i+1}: {b[0]} balloon" + (f" '{b[1]}'" if b[1] else "")
                    for i, b in enumerate(btexts)
                )
                log(f"  Page {pn}: {num_panels} panel(s) — {balloons_summary}", "info")

        if pages_skipped:
            log(f"\n❌ PAGINE DA SALTARE ({len(pages_skipped)}):", "warning")
            for pn, num_panels, tipo in pages_skipped:
                log(f"  Page {pn}: {num_panels} panel(s) — {tipo} (no balloons)", "warning")

        log(f"\n{'='*60}", "info")
        log(f"Totale: {len(pages_analyzed)} pagine da analizzare, {len(pages_skipped)} da saltare", "info")
        log(f"Risparmio stimato: {total_savings} chiamate LLM evitate", "success")
        log(f"{'='*60}", "info")
        return

    if args.dry_run:
        log("Dry-run: pages extracted, no analysis.", "success")
        return

    # ------------------------------------------------------------------
    # Step 2: Detect panels + Analyze with LLM Vision
    # ------------------------------------------------------------------
    log("Step 2/3: Detecting panels and analyzing with LLM vision...", "header")
    log(f"Model: {args.model} | Panel detection: {'ON' if not args.no_panel_detect else 'OFF'}", "info")

    all_panel_analyses = []
    page_panels_map = {}  # {page_num: num_panels}
    total_panels_detected = 0
    total_panels_analyzed = 0
    num_pages = len(extracted)

    for page_idx, page_data in enumerate(extracted):
        page_num = page_data["page_num"]
        page_image = page_data["image"]

        # --- Progress logging con ETA ---
        elapsed = time.time() - start_time
        pages_done = page_idx + 1
        progress_pct = pages_done / num_pages * 100
        if page_idx > 0 and elapsed > 0:
            eta_remaining = (elapsed / page_idx) * (num_pages - page_idx)
            eta_str = str(datetime.timedelta(seconds=int(eta_remaining)))
        else:
            eta_str = "?"
        log(f"  [{pages_done}/{num_pages} | {elapsed:.0f}s elapsed | ETA: {eta_str}] Page {page_num}...", "info")

        # Check timeout globale (5 min = 300s per pagina)
        if args.timeout > 0 and elapsed > args.timeout:
            log(f"  GLOBAL TIMEOUT ({args.timeout}s) reached after page {page_num}. Stopping.", "warning")
            break

        # --- Panel detection ---
        panels = _detect_page_panels(page_image, page_num, args.no_panel_detect)

        page_panels_map[page_num] = len(panels)
        total_panels_detected += len(panels)

        if args.debug_panels:
            debug_path = save_panels_debug(page_image, panels, args.output, page_num)
            log(f"  Debug panels saved: {debug_path}", "info")

        # --- Analizza ogni pannello ---
        try:
            panel_results = analyze_page_panels(
                model=args.model,
                panels=panels,
                ollama_url=args.ollama_url,
                timeout=min(args.timeout, 300),  # Max 5 min per API call
                comic_title=comic_title,
                use_balloon_ocr=not args.no_balloon_ocr,
                debug_balloons=args.debug_balloons,
                debug_dir=args.output,
                skip_no_balloon=not args.no_skip_no_balloon,
                total_comic_pages=total_pdf_pages,
            )
            all_panel_analyses.extend(panel_results)
            total_panels_analyzed += len(panel_results)

            if num_pages > 1:
                time.sleep(1)

        except Exception as e:
            log(f"  Error analyzing page {page_num}: {e}", "error")
            for i, panel in enumerate(panels):
                all_panel_analyses.append({
                    "page_num": page_num,
                    "panel_num": i + 1,
                    "total_panels": len(panels),
                    "tipo": "fumetto",
                    "titolo": f"Pagina {page_num}, Vignetta {i + 1}",
                    "descrizione": f"(Errore: {e})",
                    "personaggi": "",
                    "dialoghi": "",
                    "effetto_sonoro": "",
                    "ambientazione": "",
                    "durata_stimata": 10,
                    "panel_bbox": {
                        "x": panel.x, "y": panel.y,
                        "width": panel.width, "height": panel.height,
                    },
                    "is_full_page": panel.is_full_page,
                })
            total_panels_analyzed += len(panels)

    if not all_panel_analyses:
        log("No panels analyzed!", "error")
        sys.exit(1)

    # Cleanup page images if requested
    if args.no_cache:
        pages_dir = Path(args.output) / "pages"
        if pages_dir.exists():
            import shutil
            shutil.rmtree(pages_dir)
            log("Removed page images (--no-cache)", "info")

    elapsed_step2 = time.time() - start_time
    log(f"Step 2 complete: {total_panels_detected} panels detected, {total_panels_analyzed} analyzed in {elapsed_step2:.0f}s", "success")

    # ------------------------------------------------------------------
    # Optional: Global page analysis
    # ------------------------------------------------------------------
    global_analyses = []
    if args.global_analysis:
        log("Step 3a/4: Analyzing full pages (global)...", "header")
        # Sample ogni 5 pagine per risparmiare chiamate (full-global = tutte)
        global_sample_step = 1 if args.full_global else 5
        pages_for_global = [
            p for p in extracted
            if (p["page_num"] - 1) % global_sample_step == 0
        ]
        total_global = len(pages_for_global)
        total_pages = len(extracted)
        if total_global < total_pages:
            log(f"  Global analysis: {total_global}/{total_pages} pages (sampling every {global_sample_step}th page)", "info")
        for g_idx, page_data in enumerate(pages_for_global):
            page_num = page_data["page_num"]
            page_image = page_data["image"]
            elapsed_global = time.time() - start_time
            log(f"  Global analysis [{g_idx+1}/{total_global}] page {page_num} (elapsed: {elapsed_global:.0f}s)...", "info")
            try:
                ga = analyze_full_page(
                    model=args.model,
                    page_image=page_image,
                    page_num=page_num,
                    total_comic_pages=total_pdf_pages,
                    ollama_url=args.ollama_url,
                    timeout=min(args.timeout, 300),
                    comic_title=comic_title,
                )
                global_analyses.append(ga)
            except Exception as e:
                log(f"  Global analysis error on page {page_num}: {e}", "warning")

    # ------------------------------------------------------------------
    # Step 3: Synthesize video script
    # ------------------------------------------------------------------
    if not args.no_synthesis:
        log("Step 3/4: Creating video script...", "header")
        try:
            synthesis = synthesize_script(
                args.model, all_panel_analyses,
                args.ollama_url, args.timeout, comic_title,
            )
        except Exception as e:
            log(f"  Synthesis error: {e}", "error")
            synthesis = create_fallback_script(comic_title, all_panel_analyses)
    else:
        log("  Skipping synthesis (--no-synthesis)", "info")
        synthesis = create_fallback_script(comic_title, all_panel_analyses)

    # ------------------------------------------------------------------
    # Optional: Scene-by-scene YouTube transcript JSON
    # ------------------------------------------------------------------
    scene_script = []
    if args.scene_json:
        log("Step 4/4: Creating scene-by-scene YouTube transcript...", "header")
        try:
            scene_script = synthesize_scene_json(
                model=args.model,
                panel_analyses=all_panel_analyses,
                page_analyses=global_analyses if global_analyses else None,
                ollama_url=args.ollama_url,
                timeout=args.timeout,
                comic_title=comic_title,
            )
        except Exception as e:
            log(f"  Scene synthesis error: {e}", "error")

    save_output(all_panel_analyses, synthesis, args.output, str(pdf_path), page_panels_map,
                global_analyses=global_analyses, scene_script=scene_script)
    elapsed = time.time() - start_time
    print_summary(all_panel_analyses, synthesis, page_panels_map, elapsed, total_panels_analyzed)
    if scene_script:
        log(f"Scene transcript: {len(scene_script)} scenes generated", "success")
    log("Done! 🎉", "success")


def _detect_page_panels(
    page_image,
    page_num: int,
    no_panel_detect: bool = False,
):
    """Helper: rileva pannelli in una pagina o tratta come full-page."""
    if no_panel_detect:
        from comic_video.panel_detector import Panel
        return [Panel(
            page_num=page_num, panel_index=0,
            x=0, y=0,
            width=page_image.width, height=page_image.height,
            image=page_image, is_full_page=True,
            page_width=page_image.width, page_height=page_image.height,
        )]
    return detect_panels(page_image, page_num)


def create_fallback_script(comic_title: str, panel_analyses: list[dict]) -> dict:
    """Create a fallback script from panel descriptions."""
    descriptions = []
    for p in panel_analyses:
        desc = p.get("descrizione", "")
        if desc:
            descriptions.append(desc)

    return {
        "titolo_video": comic_title,
        "genere": "",
        "personaggi_principali": [],
        "colonna_sonora": "",
        "script_narrativo": "\n\n".join(descriptions),
        "durata_totale_stimata_minuti": sum(
            p.get("durata_stimata", 10) for p in panel_analyses
        ) // 60,
    }


if __name__ == "__main__":
    main()
