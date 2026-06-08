#!/usr/bin/env python3
"""
COMIC VIDEO CREATOR
===================
Genera video con voiceover dalle analisi dei fumetti.

Caratteristiche:
1. Traduce automaticamente le descrizioni in inglese (via Ollama)
2. Genera voiceover TTS (edge-tts) dal testo tradotto
3. Crea un clip video con l'immagine della pagina che scorre dall'alto verso il basso
4. Usa la durata REALE del TTS per sincronizzare perfettamente audio e video
5. Concatena tutti i clip in un video finale

Esempio:
    python comic-video-creator.py analisi.json --pages 1-10
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import edge_tts
import numpy as np
import requests

# Import moviepy (supports both v1 and v2)
try:
    from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips
    MOVIEPY_V2 = False
except ImportError:
    try:
        from moviepy import AudioFileClip, VideoClip, concatenate_videoclips
        MOVIEPY_V2 = True
    except ImportError:
        print("ERROR: moviepy not installed. Run: pip install moviepy")
        sys.exit(1)

from comic_video.utils import (
    RICH_AVAILABLE,
    TEMP_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    load_and_scale_image,
    load_blurred_background,
    log,
    parse_page_range,
    print_summary_table,
)


# ---------------------------------------------------------------------------
# Helpers: attach audio (moviepy v1/v2 compat)
# ---------------------------------------------------------------------------

def attach_audio(clip: VideoClip, audio: AudioFileClip) -> VideoClip:
    """Attach audio to a VideoClip, compatible with both moviepy v1 and v2."""
    if MOVIEPY_V2:
        return clip.with_audio(audio)
    return clip.set_audio(audio)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_VOICE = "en-US-ChristopherNeural"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llava:13b"


# ---------------------------------------------------------------------------
# TTS Generation (edge-tts)
# ---------------------------------------------------------------------------

async def generate_tts_async(
    text: str, output_path: str, voice: str = DEFAULT_VOICE
) -> str:
    communicate = edge_tts.Communicate(text, voice, rate="+0%", pitch="+0Hz")
    await communicate.save(output_path)
    return output_path


def generate_tts(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> str:
    return asyncio.run(generate_tts_async(text, output_path, voice))


def get_audio_duration(audio_path: str) -> float:
    """Get the exact duration of an audio file in seconds."""
    try:
        clip = AudioFileClip(audio_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Translation (Italian → English via Ollama)
# ---------------------------------------------------------------------------

TRANSLATION_PROMPT = """Translate the following Italian comic book page descriptions into NATURAL, FLOWING English.
Keep the dramatic, engaging tone suitable for a YouTube voiceover.
Preserve character names, sound effects, and proper nouns as-is.
Output a JSON array where each element corresponds to the input text at the same index.

Input:
{input_json}

Output ONLY a valid JSON array of strings, nothing else."""


def translate_to_english(
    texts: list[str],
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_OLLAMA_MODEL,
    timeout: int = 120,
) -> list[str]:
    """
    Translate a list of Italian texts to English using Ollama.
    Returns the translated texts.
    """
    # Join all texts with markers for batch translation
    input_json = json.dumps(texts, ensure_ascii=False)

    # Truncate if too long (Ollama context window)
    if len(input_json) > 8000:
        log("  Text too long for batch translation, translating individually...", "warning")
        # Fall back to individual translations
        translated = []
        for i, t in enumerate(texts):
            single_json = json.dumps([t], ensure_ascii=False)
            prompt = TRANSLATION_PROMPT.format(input_json=single_json)
            try:
                resp = requests.post(
                    f"{ollama_url.rstrip('/')}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
                    timeout=timeout,
                )
                resp.raise_for_status()
                result_text = resp.json().get("response", "")
                # Extract JSON array from response
                match = re.search(r'\[[\s\S]*?\]', result_text)
                if match:
                    result_list = json.loads(match.group(0))
                    translated.append(result_list[0] if result_list else t)
                else:
                    translated.append(t)
            except Exception as e:
                log(f"  Translation failed for text {i}: {e}", "warning")
                translated.append(t)
            log(f"  Translated text {i+1}/{len(texts)}", "info")
        return translated

    prompt = TRANSLATION_PROMPT.format(input_json=input_json)
    log(f"  Translating {len(texts)} descriptions via Ollama...", "info")

    try:
        resp = requests.post(
            f"{ollama_url.rstrip('/')}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
            timeout=timeout,
        )
        resp.raise_for_status()
        result_text = resp.json().get("response", "")

        # Extract JSON array from response
        # Try ```json ... ``` first, then bare [...]
        json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', result_text)
        if not json_match:
            json_match = re.search(r'(\[[\s\S]*?\])', result_text)
        if json_match:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list) and len(parsed) == len(texts):
                return [str(t) for t in parsed]
            else:
                log(f"  Translation returned {len(parsed)} items, expected {len(texts)}. Using originals.", "warning")
        else:
            log("  Could not parse translation response. Using original Italian texts.", "warning")
            log(f"  Raw response: {result_text[:200]}", "warning")
    except Exception as e:
        log(f"  Translation API error: {e}. Using original Italian texts.", "warning")

    return texts  # Fallback: return original


# ---------------------------------------------------------------------------
# Video Clip Creation (with zoom/scroll effect)
# ---------------------------------------------------------------------------

def create_page_clip(
    image_path: str,
    audio_path: str,
    duration: float,
    target_w: int = VIDEO_WIDTH,
    target_h: int = VIDEO_HEIGHT,
) -> VideoClip:
    """
    Create a cinematic video clip for a single page.

    EFFECT:
        - Background: same page super-zoomed, blurred & darkened (elegante)
        - Foreground: page with gentle zoom, centered, slowly scrolling top→bottom
        - No Ken Burns — scroll puro, lento, cinematografico

    The clip duration = actual audio duration (guarantees perfect sync).

    Args:
        image_path: Path to the page PNG image
        audio_path: Path to the TTS audio file
        duration: Exact duration in seconds (from TTS audio)
        target_w: Output video width
        target_h: Output video height

    Returns:
        A VideoClip ready to be concatenated
    """
    log(f"    Creating clip: {Path(image_path).name} ({duration:.1f}s)", "info")

    # 1. Load blurred background (full frame, super-zoomata + blur + dark)
    bg_array = load_blurred_background(image_path, target_w, target_h)

    # 2. Load foreground (reduced zoom per mostrare piu pagina)
    fg_array, fg_w, fg_h = load_and_scale_image(image_path, target_w, target_h)

    # 3. Calculate max scroll for foreground
    max_scroll = max(0, fg_h - target_h)

    # Pre-import PIL for resize in make_frame
    from PIL import Image as PILImage

    #    # Display area: foreground fills max 90% of frame (blur bordi elegante)
    fg_max_w = int(target_w * 0.90)
    fg_max_h = int(target_h * 0.90)

    def make_frame(t):
        progress = t / duration if duration > 0 else 0

        # --- Scroll: top to bottom — lento, fluido, elegante ---
        scroll_y = int(progress * max_scroll)
        scroll_y = min(scroll_y, fg_h - target_h)

        # Crop: usa tutta la larghezza e altezza disponibili
        crop_w = min(fg_w, target_w)
        crop_h = min(fg_h, target_h)

        # Centra orizzontalmente e scrolla verticalmente
        scroll_y = min(scroll_y, fg_h - crop_h)
        crop_x = max(0, (fg_w - crop_w) // 2)

        # Crop from foreground array
        fg_crop = fg_array[scroll_y:scroll_y + crop_h, crop_x:crop_x + crop_w, :]

        # Fit crop within display area preserving aspect ratio
        scale = min(fg_max_w / crop_w, fg_max_h / crop_h)
        display_w = int(crop_w * scale)
        display_h = int(crop_h * scale)
        dx = (target_w - display_w) // 2
        dy = (target_h - display_h) // 2

        # Single resize to display dimensions
        fg_display = np.array(
            PILImage.fromarray(fg_crop).resize((display_w, display_h), PILImage.LANCZOS)
        )

        # --- Composite background + foreground ---
        frame = bg_array.copy()
        frame[dy:dy + display_h, dx:dx + display_w, :] = fg_display

        return frame

    clip = VideoClip(make_frame, duration=duration)

    # Add audio (if exists)
    if os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        clip = attach_audio(clip, audio)

    return clip


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def create_video(
    json_path: str,
    pages_dir: str,
    output_path: str,
    page_range: Optional[list[int]] = None,
    voice: str = DEFAULT_VOICE,
    translate: bool = True,
    preview: bool = False,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
):
    """
    Main pipeline: read JSON, translate, generate TTS, create clips, concatenate.

    Args:
        json_path: Path to the analysis JSON file
        pages_dir: Directory containing page images
        output_path: Path for the output video file
        page_range: List of page numbers to include (None = all)
        voice: Edge-TTS voice name
        translate: If True, translate Italian descriptions to English via Ollama
        preview: If True, generate a low-res preview quickly
    """
    log("Comic Video Creator", "header")
    log(f"Pages dir: {pages_dir}", "info")
    log(f"Output: {output_path}", "info")
    log(f"Voice: {voice}", "info")
    if preview:
        log(f"PREVIEW MODE: reduced resolution", "warning")
    if translate:
        log(f"Translation: Italian → English (via Ollama)", "info")
    else:
        log(f"Translation: OFF (using original Italian)", "info")

    # Create temp directory
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load JSON analysis
    log("Loading analysis data...", "info")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Supporta sia formato v2 (analisi_pagine) che v3 (analisi_pannelli)
    analyses = data.get("analisi_pannelli", data.get("analisi_pagine", []))
    if not analyses:
        log("No page/panel analyses found in JSON!", "error")
        sys.exit(1)

    # Se abbiamo analisi per-pannello, raggruppa per pagina
    is_panel_format = "panel_num" in analyses[0] if analyses else False

    if is_panel_format:
        # Raggruppa pannelli per pagina
        from itertools import groupby
        analyses.sort(key=lambda a: a["page_num"])
        page_analyses = []
        for page_num, group in groupby(analyses, key=lambda a: a["page_num"]):
            panels = list(group)
            # Combina descrizioni di tutti i pannelli in un unico testo per pagina
            combined_desc = " ".join(
                p.get("descrizione", p.get("descrizione_narrativa", ""))
                for p in panels
            )
            combined_titolo = panels[0].get("titolo", panels[0].get("titolo_scena", f"Pagina {page_num}"))
            page_analyses.append({
                "page_num": page_num,
                "titolo_scena": combined_titolo,
                "descrizione_narrativa": combined_desc,
                "personaggi": ", ".join(filter(None, (p.get("personaggi", "") for p in panels))),
                "dialoghi": " | ".join(filter(None, (p.get("dialoghi", "") for p in panels))),
            })
        analyses = page_analyses

    # Filter by page range
    if page_range:
        analyses = [a for a in analyses if a["page_num"] in page_range]
        analyses.sort(key=lambda a: a["page_num"])

    total_pages = len(analyses)
    log(f"Selected {total_pages} pages for video generation", "success")

    if total_pages == 0:
        log("No pages to process!", "error")
        sys.exit(1)

    # Preview resolution
    target_w = VIDEO_WIDTH
    target_h = VIDEO_HEIGHT
    if preview:
        target_w, target_h = 854, 480

    # 2. Translate descriptions to English (if enabled)
    if translate:
        log("Translating descriptions Italian → English...", "header")
        texts_to_translate = []
        for page in analyses:
            titolo = page.get("titolo_scena", "")
            desc = page.get("descrizione_narrativa", "")
            texts_to_translate.append(f"{titolo}. {desc}")

        translated = translate_to_english(texts_to_translate, ollama_url=ollama_url, model=ollama_model)

        for i, page in enumerate(analyses):
            if i < len(translated):
                page["_tts_text"] = translated[i]
            else:
                page["_tts_text"] = texts_to_translate[i]
    else:
        log("Skipping translation, using original Italian.", "info")
        for page in analyses:
            titolo = page.get("titolo_scena", "")
            desc = page.get("descrizione_narrativa", "")
            page["_tts_text"] = f"{titolo}. {desc}"

    # 3. Process each page: generate TTS + create clip
    log("Generating voiceover and video clips...", "header")

    page_clips = []
    audio_files = []

    for i, page in enumerate(analyses):
        page_num = page["page_num"]
        tts_text = page["_tts_text"]
        titolo = page.get("titolo_scena", f"Page {page_num}")

        log(f"Page {page_num}/{total_pages}: {titolo}", "header")

        # Find page image (already exists, no regeneration)
        img_path = Path(pages_dir) / f"page_{page_num:04d}.png"
        if not img_path.exists():
            log(f"  Image not found: {img_path}", "error")
            continue

        # Generate TTS audio
        log(f"  Generating TTS ({len(tts_text)} chars, voice: {voice})...", "info")
        audio_path = TEMP_DIR / f"page_{page_num:04d}.mp3"
        try:
            generate_tts(tts_text, str(audio_path), voice)
            audio_files.append(str(audio_path))
        except Exception as e:
            log(f"  TTS generation failed: {e}", "error")
            continue

        # Get exact audio duration (guarantees sync - no overlap, no cut-off)
        audio_duration = get_audio_duration(str(audio_path))
        if audio_duration <= 0:
            log(f"  Could not read audio duration, using estimated", "warning")
            audio_duration = len(tts_text) / 15  # rough estimate

        clip_duration = audio_duration

        # Create clip (duration = exact audio length → perfect sync)
        try:
            clip = create_page_clip(
                str(img_path), str(audio_path), clip_duration, target_w, target_h,
            )
            page_clips.append(clip)
            log(f"  Clip created ({clip_duration:.1f}s, {target_w}x{target_h})", "success")
        except Exception as e:
            log(f"  Clip creation failed: {e}", "error")
            import traceback
            traceback.print_exc()
            continue

    if not page_clips:
        log("No clips were created!", "error")
        sys.exit(1)

    # 4. Concatenate all page clips
    log("Concatenating all clips...", "header")
    try:
        final_clip = concatenate_videoclips(page_clips, method="chain")
    except Exception as e:
        log(f"Concatenation failed: {e}", "error")
        # Fallback: try without audio
        log("Trying without audio...", "warning")
        try:
            clips_no_audio = []
            for pg in analyses[:len(page_clips)]:
                pn = pg["page_num"]
                img_p = Path(pages_dir) / f"page_{pn:04d}.png"
                if img_p.exists():
                    dur = get_audio_duration(str(TEMP_DIR / f"page_{pn:04d}.mp3")) or 10
                    clip_no_audio = create_page_clip(str(img_p), "", dur, target_w, target_h)
                    clips_no_audio.append(clip_no_audio)
            if clips_no_audio:
                final_clip = concatenate_videoclips(clips_no_audio, method="chain")
            else:
                raise
        except Exception as e2:
            log(f"Still failed: {e2}", "error")
            sys.exit(1)

    total_duration = sum(c.duration for c in page_clips)

    # 5. Write output video
    log(f"Writing video: {output_path}", "header")
    log(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)", "info")

    try:
        final_clip.write_videofile(
            str(output_path),
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            preset="fast" if not preview else "ultrafast",
            bitrate="5000k" if not preview else "2000k",
            threads=4,
            logger="bar",
        )
        log(f"Video saved: {output_path}", "success")
    except Exception as e:
        log(f"Video writing failed: {e}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup clips
        for clip in page_clips:
            try:
                clip.close()
            except Exception:
                pass
        try:
            final_clip.close()
        except Exception:
            pass
        # Cleanup temp audio files
        for audio_f in audio_files:
            try:
                os.remove(audio_f)
            except Exception:
                pass

    # 6. Summary
    print_summary_table("Video Creation Complete", [
        ("Pages", str(len(page_clips))),
        ("Duration", f"{total_duration:.1f}s ({total_duration/60:.1f} min)"),
        ("Resolution", f"{target_w}x{target_h}"),
        ("Voice", voice),
        ("Output", str(output_path)),
    ])

    log("Done! 🎉", "success")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Comic Video Creator — Genera video con voiceover (traduzione EN auto)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s test_output_full/analisi.json --pages 1-10
  %(prog)s analisi.json --voice en-GB-RyanNeural --no-translate
  %(prog)s analisi.json --pages 1-5 --preview
        """,
    )

    parser.add_argument("json", type=str, help="Percorso del file JSON di analisi")
    parser.add_argument("-o", "--output", type=str, default=None, help="Percorso del video output")
    parser.add_argument("--pages-dir", type=str, default=None, help="Directory immagini pagine")
    parser.add_argument("--pages", type=str, default=None, help="Pagine da includere (es. '1-10')")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE, help=f"Voce edge-tts (default: {DEFAULT_VOICE})")
    parser.add_argument("--no-translate", action="store_true", help="Disabilita traduzione in inglese (usa testo italiano originale)")
    parser.add_argument("--ollama-url", type=str, default=DEFAULT_OLLAMA_URL, help=f"URL Ollama (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--ollama-model", type=str, default=DEFAULT_OLLAMA_MODEL, help=f"Modello Ollama per traduzione (default: {DEFAULT_OLLAMA_MODEL})")
    parser.add_argument("--preview", action="store_true", help="Anteprima 480p per test veloci")
    parser.add_argument("--list-voices", action="store_true", help="Elenca voci edge-tts disponibili")

    args = parser.parse_args()

    # List voices
    if args.list_voices:
        log("Fetching available voices...", "info")
        voices = asyncio.run(edge_tts.list_voices())
        for v in voices:
            name = v.get("ShortName", v.get("Name", "?"))
            locale = v.get("Locale", "?")
            gender = v.get("Gender", "?")
            print(f"  {name} ({locale}, {gender})")
        return

    # Validate JSON
    json_path = Path(args.json)
    if not json_path.exists():
        log(f"JSON file not found: {json_path}", "error")
        sys.exit(1)

    # Pages directory
    if args.pages_dir:
        pages_dir = Path(args.pages_dir)
    else:
        pages_dir = json_path.parent / "pages"

    if not pages_dir.exists():
        log(f"Pages directory not found: {pages_dir}", "error")
        sys.exit(1)

    # Output path
    if args.output:
        output_path = args.output
    else:
        stem = json_path.stem.replace("_analisi", "")
        output_path = str(json_path.parent / f"{stem}_video_en.mp4")

    # Page range
    page_range = None
    if args.pages:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Supporta sia formato v2 (analisi_pagine) che v3 (analisi_pannelli)
        analyses_temp = data.get("analisi_pannelli", data.get("analisi_pagine", []))
        if analyses_temp and "panel_num" in analyses_temp[0]:
            total = len(set(a["page_num"] for a in analyses_temp))
        else:
            total = len(analyses_temp)
        page_range = parse_page_range(args.pages, total)
        log(f"Page range: {args.pages} ({len(page_range)} pages)", "info")

    # Create video
    create_video(
        json_path=str(json_path),
        pages_dir=str(pages_dir),
        output_path=output_path,
        page_range=page_range,
        voice=args.voice,
        translate=not args.no_translate,
        preview=args.preview,
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model,
    )


if __name__ == "__main__":
    main()
