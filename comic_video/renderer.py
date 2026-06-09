"""
Comic Video — Video Renderer (veloce)
- Immagine pagina su sfondo blurato
- Voiceover TTS
"""

import asyncio
import concurrent.futures
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

from .utils import log, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

try:
    from moviepy import ImageClip, concatenate_videoclips, ColorClip, AudioFileClip, VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips, ColorClip, AudioFileClip, VideoFileClip
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


def validate_narration_json(data):
    if "pagine" not in data:
        return False, "Campo 'pagine' mancante"
    for i, p in enumerate(data["pagine"]):
        if "pagina" not in p:
            return False, f"Pagina {i+1} manca campi"
        if not _page_narration_text(p).strip():
            return False, f"Pagina {i+1} manca campo narrazione"
    return True, ""


async def _tts(text, out, voice="it-IT-DiegoNeural", rate="-30%", pitch="-8Hz"):
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)

def tts(text, out, voice="it-IT-DiegoNeural", rate="-30%", pitch="-8Hz"):
    asyncio.run(_tts(text, out, voice, rate, pitch))


@dataclass
class _TTSJob:
    key: str
    text: str
    out: Path


async def _generate_tts_jobs(jobs: list[_TTSJob], voice: str, rate: str, pitch: str, workers: int = 3):
    sem = asyncio.Semaphore(max(1, workers))

    async def _run(job: _TTSJob):
        async with sem:
            await edge_tts.Communicate(job.text, voice, rate=rate, pitch=pitch).save(str(job.out))

    await asyncio.gather(*(_run(job) for job in jobs))

def audio_dur(path):
    from mutagen import File as M
    try:
        a = M(path)
        if a and a.info: return a.info.length
    except: pass
    return 10.0


def _page_narration_text(page: dict) -> str:
    return (
        page.get("narrazione_video")
        or page.get("cosa_succede")
        or page.get("descrizione")
        or page.get("description")
        or ""
    )


def make_page_frame(image_path, use_blur: bool = True, page_scale: float = 0.68):
    """Crea UN SOLO frame statico per pagina, da riusare per tutta la durata."""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    # Sfondo: sempre la stessa immagine riempita a tutto schermo e sfocata.
    scale = max(VIDEO_WIDTH / w, VIDEO_HEIGHT / h)
    bg = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    l = (bg.width - VIDEO_WIDTH) // 2
    t = (bg.height - VIDEO_HEIGHT) // 2
    bg = bg.crop((l, t, l + VIDEO_WIDTH, t + VIDEO_HEIGHT))
    blur_amount = 35 if use_blur else 14
    bg = bg.filter(ImageFilter.GaussianBlur(blur_amount))
    bg = ImageEnhance.Brightness(bg).enhance(0.5)
    bg_arr = np.array(bg)
    bg.close()

    # Primo piano: sempre piccolo e centrato, mai stretchato a schermo intero
    fw = int(VIDEO_WIDTH * page_scale)
    fh = int(VIDEO_HEIGHT * page_scale)
    fscale = min(fw / w, fh / h)
    fg = img.resize((max(1, int(w * fscale)), max(1, int(h * fscale))), Image.LANCZOS)
    fw = fg.width
    fh = fg.height
    fg_arr = np.array(fg)
    fg.close()
    img.close()

    # Composite al centro
    canvas = bg_arr.copy()
    ox = (VIDEO_WIDTH - fw) // 2
    oy = (VIDEO_HEIGHT - fh) // 2
    canvas[oy:oy+fh, ox:ox+fw] = fg_arr

    return canvas


def make_page_frame_file(image_path: str, out_path: Path, use_blur: bool = True):
    """Crea e salva il frame statico della pagina come PNG cache."""
    if out_path.exists():
        return out_path
    frame = make_page_frame(image_path, use_blur=use_blur)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(out_path)
    return out_path


def _zoom_frame(frame: np.ndarray, t: float, duration: float, start_scale: float = 1.0, end_scale: float = 1.02) -> np.ndarray:
    if duration <= 0:
        return frame
    progress = min(max(t / duration, 0.0), 1.0)
    scale = start_scale + (end_scale - start_scale) * progress
    if abs(scale - 1.0) < 1e-3:
        return frame

    h, w = frame.shape[:2]
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    img = Image.fromarray(frame).resize((new_w, new_h), Image.LANCZOS)

    left = max(0, (new_w - w) // 2)
    top = max(0, (new_h - h) // 2)
    img = img.crop((left, top, left + w, top + h))
    return np.array(img)


def _split_into_chunks(items: list, chunk_size: int) -> list[list]:
    if chunk_size <= 0:
        return [items]
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def _render_pages_chunk(
    chunk_pages: list[dict],
    pages_dir: str,
    audio_dir: str,
    chunk_output: str,
    use_blur: bool,
    fps: int,
) -> str:
    pages_path = Path(pages_dir)
    audio_path = Path(audio_dir)
    out_path = Path(chunk_output)
    temp = Path(tempfile.mkdtemp(prefix="cv_chunk_"))
    fdir = temp / "f"
    fdir.mkdir()

    clips = []
    audio_clips = []

    for pagina in chunk_pages:
        num = pagina["pagina"]
        img_path = None
        for pat in [f"page_{num:04d}.png", f"page_{num}.png", f"page{num:04d}.png"]:
            candidate = pages_path / pat
            if candidate.exists():
                img_path = candidate
                break
        if not img_path:
            continue

        ap = audio_path / f"p{num}.mp3"
        if not ap or not ap.exists():
            continue

        audio_clip = AudioFileClip(str(ap))
        duration = max(float(audio_clip.duration or 0.0), 0.1) + 0.05
        frame_path = make_page_frame_file(
            str(img_path),
            fdir / f"page_{num:04d}_blur{int(use_blur)}.png",
            use_blur=use_blur,
        )
        page_clip = ImageClip(str(frame_path)).with_duration(duration).with_audio(audio_clip)
        page_clip = page_clip.transform(lambda gf, t: _zoom_frame(gf(t), t, duration))
        clips.append(page_clip)
        audio_clips.append(audio_clip)

    if not clips:
        raise RuntimeError("Chunk without clips")

    final = concatenate_videoclips(clips, method="chain")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(out_path), fps=fps, codec="libx264", audio_codec="aac",
        bitrate="3000k", logger=None, preset="ultrafast", threads=4)

    for c in clips:
        try:
            c.close()
        except:
            pass
    for a in audio_clips:
        try:
            a.close()
        except:
            pass
    try:
        final.close()
    except:
        pass
    try:
        import shutil
        shutil.rmtree(temp, ignore_errors=True)
    except:
        pass
    return str(out_path)


def render_narration_video(json_path, pages_dir, output_path,
    voice="it-IT-DiegoNeural", voice_rate="-30%", voice_pitch="-8Hz",
    fps=VIDEO_FPS, transition_duration=1.0, with_subtitles=True,
    page_range=None, intro_text=None, outro_text=None, tts_workers: int = 3,
    use_blur: bool = True, chunk_size: int = 3, chunk_workers: int = 2):

    if not MOVIEPY_AVAILABLE: raise ImportError("moviepy non installato")
    if not EDGE_TTS_AVAILABLE: raise ImportError("edge-tts non installato")

    pages_path = Path(pages_dir)
    if not pages_path.exists(): raise FileNotFoundError(f"Directory non trovata: {pages_dir}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ok, err = validate_narration_json(data)
    if not ok: raise ValueError(f"JSON non valido: {err}")

    pagine = data["pagine"]
    if page_range:
        from .utils import parse_page_range
        allowed = set(parse_page_range(page_range, 9999))
        pagine = [p for p in pagine if p["pagina"] in allowed]

    log(f"Rendering: {data.get('titolo_video','Video')}", "header")
    log(f"Pagine: {len(pagine)} | Voce: {voice}", "info")

    temp = Path(tempfile.mkdtemp(prefix="cv_"))
    adir = temp / "a"
    adir.mkdir()
    fdir = temp / "f"
    fdir.mkdir()

    page_jobs: list[_TTSJob] = []
    if intro_text:
        page_jobs.append(_TTSJob("intro", intro_text, adir / "intro.mp3"))
    if outro_text:
        page_jobs.append(_TTSJob("outro", outro_text, adir / "outro.mp3"))

    page_audio_map: dict[int, Path] = {}
    for idx, pagina in enumerate(pagine):
        num = pagina["pagina"]
        nar = _page_narration_text(pagina)
        if not nar.strip():
            log(f"  #{num}: salto", "warning")
            continue

        img_path = None
        for pat in [f"page_{num:04d}.png", f"page_{num}.png", f"page{num:04d}.png"]:
            c = pages_path / pat
            if c.exists():
                img_path = c
                break
        if not img_path:
            log(f"    Non trovata", "warning")
            continue

        page_audio_map[num] = adir / f"p{num}.mp3"
        page_jobs.append(_TTSJob(str(num), nar, page_audio_map[num]))

    if page_jobs:
        log(f"  Generating audio in parallel ({min(tts_workers, len(page_jobs))} workers)...", "info")
        try:
            asyncio.run(_generate_tts_jobs(page_jobs, voice, voice_rate, voice_pitch, workers=tts_workers))
        except Exception as e:
            log(f"  TTS batch error: {e}", "error")
            raise

    # Render pages in parallel chunks, then concatenate chunk videos.
    page_chunks = _split_into_chunks(pagine, max(1, chunk_size))
    chunk_paths = []
    if page_chunks:
        log(f"  Rendering {len(page_chunks)} chunk(s) in parallel...", "info")
        chunk_workers = max(1, chunk_workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=chunk_workers) as pool:
            futures = []
            for i, chunk in enumerate(page_chunks, start=1):
                chunk_out = temp / f"chunk_{i:03d}.mp4"
                futures.append(pool.submit(
                    _render_pages_chunk,
                    chunk,
                    pages_dir,
                    str(adir),
                    str(chunk_out),
                    use_blur,
                    fps,
                ))
            for fut in futures:
                chunk_paths.append(fut.result())

    clips = []

    if intro_text:
        log("  Intro...", "info")
        ap = adir / "intro.mp3"
        if ap.exists():
            d = audio_dur(str(ap))
            intro_frame = fdir / "intro.png"
            if not intro_frame.exists():
                Image.fromarray(np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), (8,8,12), dtype=np.uint8)).save(intro_frame)
            clips.append(ImageClip(str(intro_frame)).with_duration(d).with_audio(AudioFileClip(str(ap))))
            log(f"    {d:.1f}s", "success")

    for chunk_path in chunk_paths:
        clips.append(VideoFileClip(str(chunk_path)))

    if outro_text:
        log("  Outro...", "info")
        ap = adir / "outro.mp3"
        if ap.exists():
            d = audio_dur(str(ap))
            outro_frame = fdir / "outro.png"
            if not outro_frame.exists():
                Image.fromarray(np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), (8,8,12), dtype=np.uint8)).save(outro_frame)
            clips.append(ImageClip(str(outro_frame)).with_duration(d).with_audio(AudioFileClip(str(ap))))
            log(f"    {d:.1f}s", "success")

    if not clips:
        raise RuntimeError("Nessun clip")

    log(f"Unione {len(clips)} clip...", "info")
    final = concatenate_videoclips(clips, method="chain")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    log(f"Export: {final.duration:.1f}s ({final.duration/60:.1f} min)", "info")

    final.write_videofile(str(out), fps=fps, codec="libx264", audio_codec="aac",
        bitrate="3000k", logger=None, preset="ultrafast", threads=4)

    for c in clips:
        try: c.close()
        except: pass
    final.close()

    try:
        import shutil
        shutil.rmtree(temp, ignore_errors=True)
    except: pass

    log(f"Fatto: {output_path}", "success")
    return str(out)


def get_narration_info(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pagine = data.get("pagine", [])
    tp = sum(len(_page_narration_text(p).split()) for p in pagine)
    d = tp / 2.8
    return {"titolo": data.get("titolo_video","N/D"), "num_pagine": len(pagine),
            "pagine": [p["pagina"] for p in pagine], "totale_parole": tp,
            "durata_stimata_secondi": round(d,1), "durata_stimata_minuti": round(d/60,1)}

def validate_json_structure(d): return validate_narration_json(d)
def extract_panels_from_json(d): return d.get("pagine", d.get("analisi_pannelli", []))
def render_video_from_json(j, p, o, **kw): return render_narration_video(j, p, o, **kw)
