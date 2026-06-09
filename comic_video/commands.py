"""
Comic Video — Core CLI Commands
================================
Funzioni orchestrazione estratte dagli script standalone per uso
con Typer (cli.py) e backward-compatibili (argparse wrapper).
"""

import datetime
import json
import time
from pathlib import Path
from typing import Optional

from .utils import (
    RICH_AVAILABLE,
    console,
    extract_comic_title_from_filename,
    log,
    parse_page_range,
    find_pdf,
)
from .extractor import extract_pdf_pages, EASYOCR_AVAILABLE
from .analyzer import (
    analyze_page_panels,
    analyze_full_page,
    synthesize_script,
    synthesize_scene_json,
    synthesize_page_digest_json,
    build_page_digest_fallback,
)
from .panel_detector import detect_panels, save_panels_debug
from .balloon_detector import detect_balloons, detect_balloons_in_panel
from .ollama import DEFAULT_OLLAMA_URL
from .config import OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS, OUTPUT_DIR, PROJECT_ROOT

if RICH_AVAILABLE:
    from rich.panel import Panel as RichPanel
    from rich.table import Table

# Rich helpers


def _draw_panel_with_balloons(panel_image, balloons, panel_num, page_num, debug_dir: Path):
    """Disegna TUTTI i balloon su una copia dell'immagine con numeri e testo."""
    import cv2
    import numpy as np
    img_np = np.array(panel_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    for i, b in enumerate(balloons):
        color = (
            (255, 0, 0) if i % 3 == 0 else
            (0, 255, 0) if i % 3 == 1 else
            (0, 0, 255)
        )
        cv2.rectangle(img_bgr,
            (b.x, b.y),
            (b.x + b.width, b.y + b.height),
            color, 2)

        label = f"B{i+1}: \"{b.text[:80]}\" [{b.confidence:.2f}]"
        label_y = max(20, b.y - 8)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(img_bgr,
            (b.x - 2, label_y - th - 2),
            (b.x + tw + 2, label_y + 2),
            (0, 0, 0), -1)
        cv2.putText(img_bgr, label, (b.x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    out = debug_dir / f"page{page_num:04d}_panel{panel_num:02d}_debug.png"
    cv2.imwrite(str(out), img_bgr)
    return out


# ---------------------------------------------------------------------------
# comic-video-maker helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Full pipeline (ex comic-video-maker.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Single page analysis (ex scripts/analyze_single_page.py)
# ---------------------------------------------------------------------------

def run_single_page(
    page: int,
    pdf: Optional[str] = None,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = OLLAMA_MODEL,
    comic_title: str = "Batman: The Killing Joke",
    timeout: int = OLLAMA_TIMEOUT_SECONDS,
) -> None:
    """Analizza una singola pagina PNG dal PDF usando panel detection + Ollama vision."""
    from PIL import Image

    if pdf:
        pdf_path = Path(pdf).resolve()
    else:
        pdf_path = find_pdf(PROJECT_ROOT)

    if not pdf_path.exists():
        log(f"Nessun PDF trovato in {PROJECT_ROOT} (ne in parent). Fornisci un percorso esplicito.", "error")
        raise FileNotFoundError(str(pdf_path))

    output_dir = OUTPUT_DIR
    page_path = output_dir / "pages" / f"page_{page:04d}.png"

    if not page_path.exists():
        print(f"  Pagina {page_path.name} non trovata. Estraggo dal PDF...")
        extracted = extract_pdf_pages(
            str(pdf_path), str(output_dir), dpi=200,
            use_ocr=True, requested_pages={page},
        )
        if not extracted:
            print(f"  ERRORE: impossibile estrarre la pagina {page}")
            raise RuntimeError(f"Could not extract page {page}")
        print(f"  Estratta: {page_path}")
    else:
        print(f"  Pagina gia' esistente: {page_path}")

    print("=" * 70)
    print(f"  ANALISI PAGINA: {page_path.name}")
    print(f"  Modello: {model}")
    print("=" * 70)

    img = Image.open(str(page_path))
    print(f"\n  Dimensioni: {img.width} x {img.height}")
    print(f"  Formato: {img.format}")
    print(f"  Modello: {img.mode}")
    print()

    print("  [Step 1] Rilevamento vignette...")
    panels = detect_panels(img, page_num=page)
    print(f"  -> Trovate {len(panels)} vignette\n")

    for i, p in enumerate(panels):
        print(f"    Vignetta {i+1}: ({p.x}, {p.y}) -> ({p.x + p.width}, {p.y + p.height}) "
              f"[{p.width}x{p.height}] full_page={p.is_full_page}")

    print()

    print(f"  [Step 2] Analisi con {model} (una vignetta alla volta)...")
    print()

    results = analyze_page_panels(
        model=model,
        panels=panels,
        ollama_url=ollama_url,
        timeout=timeout,
        comic_title=comic_title,
        use_balloon_ocr=True,
        skip_no_balloon=False,
    )

    print()
    print("=" * 70)
    print("  RISULTATI ANALISI")
    print("=" * 70)

    for r in results:
        print(f"\n  [+] Vignetta {r['panel_num']}/{r['total_panels']} (pagina {r['page_num']})")
        print(f"      Tipo: {r.get('tipo', '?')}")
        print(f"      Titolo: {r.get('titolo', '?')}")
        print(f"      Personaggi: {r.get('personaggi', '?')}")
        print(f"      Ambientazione: {r.get('ambientazione', '?')}")
        print(f"      Descrizione: {r.get('descrizione', '?')}")
        if r.get('dialoghi'):
            print(f"      Dialoghi: \"{r['dialoghi']}\"")
        if r.get('dialoghi_ocr'):
            print(f"      OCR Balloon: {r['dialoghi_ocr']}")
        if r.get('effetto_sonoro'):
            print(f"      Effetto sonoro: {r['effetto_sonoro']}")
        print(f"      Durata stimata: {r.get('durata_stimata', '?')}s")

    output = {
        "pagina": page_path.name,
        "dimensioni": f"{img.width}x{img.height}",
        "vignette_trovate": len(panels),
        "analisi": results
    }

    out_path = output_dir / f"page_{page:04d}_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  Analisi salvata in: {out_path}")
    print()


# ---------------------------------------------------------------------------
# OCR test (ex scripts/test_ocr_page7.py)
# ---------------------------------------------------------------------------

def run_ocr_test(page_num: int = 7) -> None:
    """Test approfondito OCR: mostra balloon rilevati, testo estratto e debug visivo."""
    from PIL import Image
    import cv2
    import numpy as np

    page_path = OUTPUT_DIR / "pages" / f"page_{page_num:04d}.png"

    if not page_path.exists():
        print(f"ERRORE: {page_path} non trovata. Estrai prima la pagina.")
        pdf_path = find_pdf(PROJECT_ROOT)
        if not pdf_path.exists():
            log(f"Nessun PDF trovato in {PROJECT_ROOT}. Fornisci un PDF o estrai prima la pagina.", "error")
            raise FileNotFoundError(str(pdf_path))
        extract_pdf_pages(str(pdf_path), str(OUTPUT_DIR), dpi=200,
                        use_ocr=False, requested_pages={page_num})

    img = Image.open(str(page_path))
    print("=" * 80)
    print(f"  TEST OCR PAGINA {page_num}")
    print(f"  Dimensioni: {img.width} x {img.height}")
    print("=" * 80)

    print("\n[STEP 1] Rilevamento vignette...")
    panels = detect_panels(img, page_num=page_num)
    print(f"  -> {len(panels)} vignette trovate\n")

    all_page_data = []
    debug_dir = OUTPUT_DIR / "debug_ocr_test"
    debug_dir.mkdir(parents=True, exist_ok=True)

    for i, panel in enumerate(panels):
        print(f"\n{'='*80}")
        print(f"  VIGNETTA {i+1}/{len(panels)}")
        print(f"  Posizione: ({panel.x}, {panel.y}) -> ({panel.x + panel.width}, {panel.y + panel.height})")
        print(f"  Dimensioni: {panel.width}x{panel.height}")
        print(f"{'='*80}")

        balloons = detect_balloons(panel.image,
                                    min_area_pct=0.003,
                                    max_area_pct=0.65,
                                    circularity_min=0.2)

        print(f"  Balloon rilevati: {len(balloons)}")
        print()

        panel_texts = []
        for j, b in enumerate(balloons):
            print(f"  Balloon #{j+1}:")
            print(f"    Pos: ({b.x}, {b.y}) -> ({b.x + b.width}, {b.y + b.height}) [{b.width}x{b.height}]")
            print(f"    Testo: \"{b.text}\"")
            print(f"    Confidenza: {b.confidence:.3f}")
            if b.text.strip():
                panel_texts.append(b.text.strip())
            print()

        combined = " | ".join(panel_texts) if panel_texts else "(NESSUN TESTO ESTRATTO)"
        print(f"  TESTO COMBINATO: \"{combined}\"")
        print()

        debug_path = _draw_panel_with_balloons(panel.image, balloons, i+1, page_num, debug_dir)
        print(f"  Debug image salvata: {debug_path}")

        print(f"\n  >>> OCR su TUTTA l'immagine del panel (non solo balloon)...")
        try:
            import easyocr
            reader = easyocr.Reader(["en", "it"], gpu=False)
            panel_np = np.array(panel.image.convert("RGB"))
            full_results = reader.readtext(panel_np, paragraph=False, detail=1)
            if full_results:
                print(f"  RISULTATI OCR COMPLETO:")
                for idx, (bbox, text, conf) in enumerate(full_results):
                    pts = [f"({int(p[0])},{int(p[1])})" for p in bbox]
                    print(f"    [{idx+1}] \"{text}\" (conf: {conf:.3f}) @ {', '.join(pts[:2])}")
            else:
                print(f"    (nessun testo rilevato su tutta l'immagine)")
        except Exception as e:
            print(f"    ERRORE OCR su tutta l'immagine: {e}")

        print()

        all_page_data.append({
            "panel": i+1,
            "bbox": f"({panel.x},{panel.y}) -> ({panel.x+panel.width},{panel.y+panel.height})",
            "balloons": [
                {
                    "pos": f"({b.x},{b.y}) -> ({b.x+b.width},{b.y+b.height})",
                    "text": b.text,
                    "conf": round(b.confidence, 3),
                }
                for b in balloons
            ],
            "combined_text": combined,
        })

    report = {
        "pagina": page_num,
        "file": page_path.name,
        "dimensioni": f"{img.width}x{img.height}",
        "vignette": len(panels),
        "dettaglio": all_page_data,
    }

    report_path = OUTPUT_DIR / f"page_{page_num:04d}_ocr_test.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport salvato: {report_path}")

    print("\n" + "=" * 80)
    print("  RIEPILOGO TESTO ESTRATTO PER VIGNETTA")
    print("=" * 80)
    for d in all_page_data:
        print(f"\n  Vignetta {d['panel']}:")
        for b in d['balloons']:
            if b['text']:
                print(f"    -> \"{b['text']}\" [{b['conf']:.2f}]")
        if not any(b['text'] for b in d['balloons']):
            print(f"    (nessun testo)")
