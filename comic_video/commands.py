"""
Comic Video — Core CLI Commands
================================
Funzioni orchestrazione estratte dagli script standalone per uso
con Typer (cli.py) e backward-compatibili (argparse wrapper).

LAYER SPLIT (split-commands-by-group, July 2026): the 3 static
top-level command entry points (`run_analyze`, `run_single_page`,
`run_ocr_test`) plus their per-command private helpers have been
extracted into dedicated sibling modules:

  - commands_analyze.py     — `run_analyze` + the helpers it owns
    (`_save_output`, `_print_summary`, `_detect_page_panels`,
    `_create_fallback_script`). Full pipeline: extract pages, detect
    panels, analyse with Ollama vision, synthesise script, save
    outputs.

  - commands_single_page.py — `run_single_page`. Single-page
    analysis CLI: extract one page, detect panels, run Ollama vision
    per panel, dump results into a per-page JSON file.

  - commands_ocr_test.py    — `run_ocr_test` + the OCR debug-image
    helper (`_draw_panel_with_balloons`). Per-page OCR deep-debug:
    show balloons + their texts, run whole-image EasyOCR as
    cross-check, emit a typed OCR report.

This file retains the canonical PUBLIC bridge surface so the CLI
layer (Typer `cli.py` and the legacy argparse wrapper) keeps the
same import shape and the same wire contract:

  - `run_analyze`, `run_single_page`, `run_ocr_test` remain
    importable as `from comic_video.commands import run_analyze`
    (the back-compat path stays pinned by re-exports below).
  - `COMMANDS` is the typed registry the dispatcher iterates.
  - `dispatch(command_name, **kwargs)` is the SINGLE entry-point
    for cli.py / argparse to invoke a command by name without
    caring about which sibling module owns the body.
  - `COMMAND_NAMES` is the ordered, frozen list of registered
    commands — used by `--help` and Typer autocomplete to surface
    the canonical inventory.

godlike/06 SSOT (one canonical owner per fact, July 2026): each
sibling owns exactly the helpers + orchestrator body that belong to
its semantic group; a future command group MUST land in a new
`commands_<group>.py` sibling with an explicit registration in
`COMMANDS` + an updated forward-pointer comment here.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, FrozenSet

from .commands_analyze import run_analyze
from .commands_ocr_test import run_ocr_test
from .commands_single_page import run_single_page


# ── Public re-exports (back-compat) ──────────────────────────────────────
# These re-exports pin the legacy import path
# (`from comic_video.commands import run_analyze`) so a Typer
# `cli.py` or argparse wrapper that depends on the legacy module
# shape compiles against the post-split tree byte-identical.

__all__ = [
    "run_analyze",
    "run_single_page",
    "run_ocr_test",
    "COMMANDS",
    "COMMAND_NAMES",
    "dispatch",
]


# ── Command registry (single source of truth) ────────────────────────────
# Typed mapping from canonical command name (the string `cli.py` and
# the argparse wrapper pass to `dispatch()`) to the top-level
# callable that owns the body. godlike/06 SSOT: adding a new command
# means appending one entry here AND creating the
# `commands_<group>.py` sibling — never edit other command bodies
# from outside their sibling module.

COMMANDS: Dict[str, Callable[..., Any]] = {
    "analyze": run_analyze,
    "single-page": run_single_page,
    "ocr-test": run_ocr_test,
}


# Frozen set of registered names — used by `--help` and Typer
# autocomplete to print the canonical inventory. Iterated as a
# sorted list for deterministic help output.

COMMAND_NAMES: FrozenSet[str] = frozenset(COMMANDS.keys())


# ── Dispatcher (single entry-point) ──────────────────────────────────────

def dispatch(command_name: str, **kwargs: Any) -> Any:
    """Single entry-point for cli.py / argparse wire-up.

    Looks up `command_name` in the typed `COMMANDS` registry and
    invokes the bound callable with the provided kwargs. Raises
    `ValueError` for unknown commands so the caller can decide
    between exit-code strategies (`sys.exit(2)` vs. friendly error
    JSON). Returns whatever the command returns (typically `None`
    for the three current commands; future commands that need
    structured stdout outputs MUST stay back-compat by returning
    `None` and printing themselves, OR update the dispatcher to
    capture / forward return values).

    Wire contract:
      - `command_name` MUST be one of `COMMAND_NAMES` (frozen).
      - kwargs are forwarded as-is to the underlying callable.
        The CLI layer is responsible for adapting argparse
        namespaces / Typer arguments into the kwargs signature
        each command expects — the dispatcher does NOT
        re-validate kwargs to preserve byte-byte compatibility
        with the pre-split `cli.py` wrapper.
    """
    if command_name not in COMMANDS:
        raise ValueError(
            f"comic-video-maker: unknown command {command_name!r}; "
            f"expected one of {sorted(COMMAND_NAMES)}"
        )
    return COMMANDS[command_name](**kwargs)
