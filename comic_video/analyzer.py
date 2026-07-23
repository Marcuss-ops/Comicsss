"""
Modulo Analisi — analizza pannelli (vignette) di fumetti tramite Ollama vision.

NON usa più il "sliding context" tra pagine, che causava allucinazioni.
Ogni vignetta viene analizzata INDIPENDENTEMENTE basandosi SOLO sull'immagine.

Contiene (re-export facade):
    - analyze_panel()        — Analisi singola vignetta   [EXTRACT phase]
    - analyze_page_panels()  — Analisi di TUTTI i pannelli di una pagina
                               [EXTRACT phase]
    - analyze_full_page()    — Analisi globale dell'intera pagina
                               [EXTRACT phase]
    - synthesize_script()    — Sintesi script video finale
                               [SUMMARIZE phase]
    - synthesize_scene_json()   — Sintesi scena-per-scena YouTube
                                  transcript  [SUMMARIZE phase]
    - synthesize_page_digest_json() — Sintesi digest JSON
                                  pagina-per-pagina  [SUMMARIZE phase]
    - build_page_digest_fallback()  — Fallback deterministico del
                                  page-digest (no-LLM)  [SUMMARIZE phase]

Layer-split (July 2026): the 1066-LOC monolith is split per pipeline
phase into:

  - comic_video.analyzer_extract     — EXTRACT phase
                                        (parse frames + extract cues:
                                         analyze_panel, analyze_page_panels,
                                         analyze_full_page)
  - comic_video.analyzer_summarize   — SUMMARIZE phase
                                        (synthesize_script, synthesize_scene_json,
                                         synthesize_page_digest_json,
                                         build_page_digest_fallback +
                                         all _parse_*/_validate_*/_normalize_*
                                         private helpers)
  - comic_video.analyzer             — THIS MODULE: facade + back-compat
                                        re-exports so existing CLI
                                        consumers (commands_analyze.py,
                                        commands_single_page.py) import
                                        unchanged.

Per godlike/06 SSOT: this module is the SINGLE canonical import path
for `comic_video.analyzer` symbols; the phase split is an internal
implementation detail invisible to CLI consumers.
"""

# Phase 1: EXTRACT — parse frames + extract cues (panel/page/global LLM)
from comic_video.analyzer_extract import (
    analyze_panel,
    analyze_page_panels,
    analyze_full_page,
)

# Phase 2: SUMMARIZE — synthesize script/scene/digest from per-phase
# analyses, plus deterministic fallback (no-LLM)
from comic_video.analyzer_summarize import (
    synthesize_script,
    synthesize_scene_json,
    synthesize_page_digest_json,
    build_page_digest_fallback,
)

__all__ = [
    # ── EXTRACT phase ──
    "analyze_panel",
    "analyze_page_panels",
    "analyze_full_page",
    # ── SUMMARIZE phase ──
    "synthesize_script",
    "synthesize_scene_json",
    "synthesize_page_digest_json",
    "build_page_digest_fallback",
]
