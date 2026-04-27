import logging
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

import scheduler as sched
from storage import ensure_dirs, list_downloaded_videos, list_downloaded_images
from drive_client import list_vids_projects, list_exported_files, download_file
from playwright_client import trigger_export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/sync.log"),
    ],
)
log = logging.getLogger(__name__)

_jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    sched.start()
    yield
    sched.stop()


app = FastAPI(title="Google Vids Downloader", lifespan=lifespan)


# ── Models ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    video_id: str


class DownloadRequest(BaseModel):
    video_id: str
    file_type: Literal["video", "image", "all"] = "all"


class SyncRequest(BaseModel):
    video_id: str
    file_type: Literal["video", "image", "all"] = "all"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/list")
async def list_projects():
    """List all Google Vids projects from Drive."""
    try:
        projects = list_vids_projects()
        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/downloads")
async def list_local_downloads():
    """List files already downloaded locally."""
    return {
        "videos": list_downloaded_videos(),
        "images": list_downloaded_images(),
    }


@app.post("/export")
async def export_project(req: ExportRequest, background_tasks: BackgroundTasks):
    """Trigger export on a Google Vids project (headless browser)."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "video_id": req.video_id}

    async def _run():
        _jobs[job_id]["status"] = "running"
        try:
            ok = await trigger_export(req.video_id)
            _jobs[job_id]["status"] = "done" if ok else "failed"
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            log.error("Export failed for %s: %s", req.video_id, e)

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "pending"}


@app.post("/download")
async def download_project(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Download exported files for a project from Drive."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "video_id": req.video_id, "files": []}

    async def _run():
        _jobs[job_id]["status"] = "running"
        try:
            files = list_exported_files(req.video_id)
            downloaded = []
            for f in files:
                is_video = "video" in f["mimeType"]
                file_type = "video" if is_video else "image"

                if req.file_type != "all" and req.file_type != file_type:
                    continue

                path = await download_file(f["id"], f["name"], file_type)
                downloaded.append(str(path))
                log.info("Downloaded %s -> %s", f["name"], path)

            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["files"] = downloaded
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            log.error("Download failed for %s: %s", req.video_id, e)

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "pending"}


@app.post("/sync")
async def sync_project(req: SyncRequest, background_tasks: BackgroundTasks):
    """Export + download in one step."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "video_id": req.video_id, "files": []}

    async def _run():
        _jobs[job_id]["status"] = "exporting"
        try:
            await trigger_export(req.video_id)
            _jobs[job_id]["status"] = "downloading"

            files = list_exported_files(req.video_id)
            downloaded = []
            for f in files:
                is_video = "video" in f["mimeType"]
                file_type = "video" if is_video else "image"

                if req.file_type != "all" and req.file_type != file_type:
                    continue

                path = await download_file(f["id"], f["name"], file_type)
                downloaded.append(str(path))

            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["files"] = downloaded
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            log.error("Sync failed for %s: %s", req.video_id, e)

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "pending"}


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a background job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/scheduler/trigger")
async def trigger_scheduler_now(background_tasks: BackgroundTasks):
    """Manually trigger the scheduled sync immediately."""
    from scheduler import _sync_all
    background_tasks.add_task(_sync_all)
    return {"status": "triggered"}
