"""`analyze` command group — full pipeline command body.

LAYER SPLIT (split-commands-by-group, July 2026): extracted from
`comic_video.commands.run_analyze` along with the four private
helpers it owns. This file owns the end-to-end pipeline:

  1. Extract PDF pages (via extract_pdf_pages from .extractor).
  2. Detect panels per page (via detect_panels from .panel_detector).
  3. (Optional) Dry-run-skip diagnostic — pages without balloon text
     are flagged as `copertina` / `intro` / `credits` / `no_dialogo`.
  4. Analyse each panel with Ollama vision (via analyze_page_panels
     from .analyzer).
  5. (Optional) Global page-level analysis (--global-analysis).
  6. Synthesise the video script (via synthesize_script from
     .analyzer; falls back to `_create_fallback_script` on error).
  7. (Optional) scene-by-scene JSON transcript (--scene-json).
  8. (Optional) page-by-page digest JSON (--page-json, default ON).
  9. Save outputs + print summary table.

godlike/06 SSOT: this file is the SINGLE canonical owner of:

  - The full-pipeline orchestrator (`run_analyze`).
  - The output-JSON serialisation helper (`_save_output`).
  - The Rich-aware summary-table printer (`_print_summary`).
  - The panel-detection gate that produces a single full-page
    panel when `--no-panel-detect` is on (`_detect_page_panels`).
  - The LLM-failure-fallback script synthesiser
    (`_create_fallback_script`).

Wire contract: the `run_analyze(...)` callable signature is
preserved byte-byte. `comic_video.commands.COMMANDS["analyze"]`
binds to this exact function; cli.py / argparse pass kwargs
through directly.
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Optional

from .config import OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from .extractor import EASYOCR_AVAILABLE, extract_pdf_pages
from .analyzer import (
    analyze_full_page,
    analyze_page_panels,
    build_page_digest_fallback,
    synthesize_page_digest_json,
    synthesize_scene_json,
    synthesize_script,
)
from .balloon_detector import detect_balloons_in_panel
from .panel_detector import detect_panels, save_panels_debug
from .ollama import DEFAULT_OLLAMA_URL
from .utils import (
    RICH_AVAILABLE,
    console,
    extract_comic_title_from_filename,
    log,
    parse_page_range,
)


# Module-level imports gated on Rich availability — mirrors
# pre-split behaviour so the analysis header keeps rendering the
# RichPanel border when Rich is present and falls back to plain
# `print(...)` blocks otherwise.

if RICH_AVAILABLE:
    from rich.panel import Panel as RichPanel
    from rich.table import Table
else:
    RichPanel = None
    Table = None


# ── Private helpers ──────────────────────────────────────────────────────


def _save_output(
    panel_analyses: list[dict],
    synthesis: dict,
    output_dir: str,
    pdf_name: str,
    model_name: str = "qwen2.5vl:7b",
    page_panels_map: dict[int, int] = None,
    global_analyses: list[dict] = None,
    scene_script: list[dict] = None,
    page_digest: dict = None,
):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    base_name = Path(pdf_name).stem

    full_data = {
        "fonte": pdf_name,
        "modello": f"{model_name} + panel detection",
        "riepilogo_pagine": page_panels_map or {},
        "analisi_pannelli": panel_analyses,
        "script_video": synthesis,
    }

    if global_analyses:
        full_data["analisi_globali_pagine"] = global_analyses

    if scene_script:
        full_data["scene_transcript"] = scene_script
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

    if page_digest:
        full_data["page_digest"] = page_digest
        page_path = out_path / f"{base_name}_page_digest.json"
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump(page_digest, f, ensure_ascii=False, indent=2)
        log(f"Saved page digest: {page_path}", "success")

    json_path = out_path / f"{base_name}_analisi_v4.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    log(f"Saved: {json_path}", "success")
    return json_path


def _print_summary(
    panel_analyses: list[dict],
    synthesis: dict,
    page_panels_map: dict[int, int],
    elapsed: float,
    total_panels_analyzed: int,
):
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

    panel_table = Table(title="Panels per page", style="bold cyan")
    panel_table.add_column("Page", style="white")
    panel_table.add_column("Panels", style="cyan")
    for pn in sorted(page_panels_map.keys()):
        panel_table.add_row(str(pn), str(page_panels_map[pn]))
    console.print(panel_table)


def _detect_page_panels(page_image, page_num: int, no_panel_detect: bool = False):
    if no_panel_detect:
        from .panel_detector import Panel
        return [Panel(
            page_num=page_num, panel_index=0,
            x=0, y=0,
            width=page_image.width, height=page_image.height,
            image=page_image, is_full_page=True,
            page_width=page_image.width, page_height=page_image.height,
        )]
    return detect_panels(page_image, page_num)


def _create_fallback_script(comic_title: str, panel_analyses: list[dict]) -> dict:
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


# ── Public entry: full pipeline (ex comic-video-maker.py) ─────────────────


def run_analyze(
    pdf: str,
    output: str = "output",
    model: str = OLLAMA_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    pages: Optional[str] = None,
    dpi: int = 200,
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
    title: Optional[str] = None,
    no_synthesis: bool = False,
    dry_run: bool = False,
    dry_run_skip: bool = False,
    no_ocr: bool = False,
    no_cache: bool = False,
    no_panel_detect: bool = False,
    debug_panels: bool = False,
    no_balloon_ocr: bool = False,
    no_skip_no_balloon: bool = False,
    debug_balloons: bool = False,
    global_analysis: bool = False,
    full_global: bool = False,
    scene_json: bool = False,
    page_json: bool = True,
) -> None:
    """Pipeline completo: estrae pagine, rileva pannelli, analizza con LLM, sintetizza script."""
    pdf_path = Path(pdf)
    if not pdf_path.exists():
        log(f"File not found: {pdf_path}", "error")
        raise FileNotFoundError(str(pdf_path))

    comic_title = title or extract_comic_title_from_filename(pdf)
    start_time = time.time()

    import fitz
    temp_doc = fitz.open(str(pdf_path))
    total_pdf_pages = len(temp_doc)
    temp_doc.close()

    # Header
    if RICH_AVAILABLE:
        console.print(RichPanel.fit(
            f"[bold magenta]COMIC VIDEO MAKER v4[/]\n"
            f"[white]Panel Detection + LLM Vision — Stile YouTube Narrativo[/]\n"
            f"[dim]Modello: {model} | Panel Detection: {'OFF' if no_panel_detect else 'ON'} | "
            f"Titolo: {comic_title}[/]",
            border_style="magenta",
        ))
    else:
        print("=" * 60)
        print(f"COMIC VIDEO MAKER v4 — {comic_title}")
        print(f"Modello: {model} | Panel Detection: {'OFF' if no_panel_detect else 'ON'}")
        print("=" * 60)

    # Step 1: Extract pages
    log("Step 1/3: Extracting PDF pages...", "header")
    use_ocr = not no_ocr and EASYOCR_AVAILABLE
    if use_ocr:
        log("  OCR enabled (EasyOCR)", "info")

    requested_set = None
    if pages:
        selected = parse_page_range(pages, total_pdf_pages)
        requested_set = set(selected)
        log(f"  Will extract {len(requested_set)}/{total_pdf_pages} pages", "info")

    extracted = extract_pdf_pages(
        str(pdf_path), output, dpi,
        use_ocr=use_ocr, requested_pages=requested_set,
    )

    # Dry-run-skip
    if dry_run_skip:
        log("Dry-run-skip: checking which pages would be skipped (no LLM calls)...", "header")
        log(f"Model: {model} | Panel detection: {'ON' if not no_panel_detect else 'OFF'}", "info")

        if no_balloon_ocr:
            log("  ⚠️  --no-balloon-ocr attivo: lo skip NON funzionerà nell'esecuzione reale!", "warning")

        pages_analyzed = []
        pages_skipped = []
        total_savings = 0

        for page_data in extracted:
            page_num = page_data["page_num"]
            page_image = page_data["image"]
            panels = _detect_page_panels(page_image, page_num, no_panel_detect)

            page_has_balloons = False
            balloon_texts = []
            for panel in panels:
                balloons, text = detect_balloons_in_panel(panel.image)
                balloon_texts.append((len(balloons), text[:60] if text else ""))
                if text.strip():
                    page_has_balloons = True

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

    if dry_run:
        log("Dry-run: pages extracted, no analysis.", "success")
        return

    # Step 2: Detect panels + Analyze
    log("Step 2/3: Detecting panels and analyzing with LLM vision...", "header")
    log(f"Model: {model} | Panel detection: {'ON' if not no_panel_detect else 'OFF'}", "info")

    all_panel_analyses = []
    page_panels_map = {}
    total_panels_detected = 0
    total_panels_analyzed = 0
    num_pages = len(extracted)

    for page_idx, page_data in enumerate(extracted):
        page_num = page_data["page_num"]
        page_image = page_data["image"]

        elapsed = time.time() - start_time
        pages_done = page_idx + 1
        if page_idx > 0 and elapsed > 0:
            eta_remaining = (elapsed / page_idx) * (num_pages - page_idx)
            eta_str = str(datetime.timedelta(seconds=int(eta_remaining)))
        else:
            eta_str = "?"
        log(f"  [{pages_done}/{num_pages} | {elapsed:.0f}s elapsed | ETA: {eta_str}] Page {page_num}...", "info")

        panels = _detect_page_panels(page_image, page_num, no_panel_detect)
        page_panels_map[page_num] = len(panels)
        total_panels_detected += len(panels)

        if debug_panels:
            debug_path = save_panels_debug(page_image, panels, output, page_num)
            log(f"  Debug panels saved: {debug_path}", "info")

        try:
            panel_results = analyze_page_panels(
                model=model,
                panels=panels,
                ollama_url=ollama_url,
                timeout=min(timeout, OLLAMA_TIMEOUT_SECONDS),
                comic_title=comic_title,
                use_balloon_ocr=not no_balloon_ocr,
                debug_balloons=debug_balloons,
                debug_dir=output,
                skip_no_balloon=not no_skip_no_balloon,
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
        raise RuntimeError("No panels analyzed")

    if no_cache:
        pages_dir = Path(output) / "pages"
        if pages_dir.exists():
            import shutil
            try:
                shutil.rmtree(pages_dir)
                log("Removed page images (--no-cache)", "info")
            except Exception as e:
                log(f"Could not fully remove page images (--no-cache): {e}", "warning")

    elapsed_step2 = time.time() - start_time
    log(f"Step 2 complete: {total_panels_detected} panels detected, {total_panels_analyzed} analyzed in {elapsed_step2:.0f}s", "success")

    # Optional global analysis
    global_analyses = []
    if global_analysis:
        log("Step 3a/4: Analyzing full pages (global)...", "header")
        global_sample_step = 1 if full_global else 5
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
                    model=model,
                    page_image=page_image,
                    page_num=page_num,
                    total_comic_pages=total_pdf_pages,
                    ollama_url=ollama_url,
                    timeout=min(timeout, OLLAMA_TIMEOUT_SECONDS),
                    comic_title=comic_title,
                )
                global_analyses.append(ga)
            except Exception as e:
                log(f"  Global analysis error on page {page_num}: {e}", "warning")

    # Step 3: Synthesize
    if not no_synthesis:
        log("Step 3/4: Creating video script...", "header")
        try:
            synthesis = synthesize_script(
                model, all_panel_analyses,
                ollama_url, timeout, comic_title,
            )
        except Exception as e:
            log(f"  Synthesis error: {e}", "error")
            synthesis = _create_fallback_script(comic_title, all_panel_analyses)
    else:
        log("  Skipping synthesis (--no-synthesis)", "info")
        synthesis = _create_fallback_script(comic_title, all_panel_analyses)

    # Optional scene JSON
    scene_script = []
    if scene_json:
        log("Step 4/4: Creating scene-by-scene YouTube transcript...", "header")
        try:
            scene_script = synthesize_scene_json(
                model=model,
                panel_analyses=all_panel_analyses,
                page_analyses=global_analyses if global_analyses else None,
                ollama_url=ollama_url,
                timeout=timeout,
                comic_title=comic_title,
            )
        except Exception as e:
            log(f"  Scene synthesis error: {e}", "error")

    page_digest = None
    if page_json:
        log("Step 4b/4: Creating page-by-page digest JSON...", "header")
        try:
            page_digest = synthesize_page_digest_json(
                model=model,
                panel_analyses=all_panel_analyses,
                page_analyses=global_analyses if global_analyses else None,
                ollama_url=ollama_url,
                timeout=timeout,
                comic_title=comic_title,
                total_pages=total_pdf_pages,
            )
        except Exception as e:
            log(f"  Page digest synthesis error: {e}", "error")
            page_digest = build_page_digest_fallback(
                panel_analyses=all_panel_analyses,
                page_analyses=global_analyses if global_analyses else None,
                comic_title=comic_title,
                total_pages=total_pdf_pages,
            )

    _save_output(all_panel_analyses, synthesis, output, str(pdf_path), model,
                page_panels_map,
                global_analyses=global_analyses, scene_script=scene_script, page_digest=page_digest)
    elapsed = time.time() - start_time
    _print_summary(all_panel_analyses, synthesis, page_panels_map, elapsed, total_panels_analyzed)
    if scene_script:
        log(f"Scene transcript: {len(scene_script)} scenes generated", "success")
    log("Done! 🎉", "success")
