import logging
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

import scheduler as sched
from storage import ensure_dirs, list_downloaded_videos, list_downloaded_images
from playwright_client import list_projects, download_project, download_images, sync_project

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


class DownloadRequest(BaseModel):
    video_id: str
    file_type: Literal["video", "image", "all"] = "all"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/list")
async def get_projects():
    """List all Google Vids projects (scraped via headless browser)."""
    try:
        projects = await list_projects()
        return {"projects": projects, "count": len(projects)}
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/downloads")
async def get_local_downloads():
    """List files already downloaded locally."""
    return {
        "videos": list_downloaded_videos(),
        "images": list_downloaded_images(),
    }


@app.post("/download")
async def download(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Download video and/or images from a Google Vids project."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "video_id": req.video_id, "files": []}

    async def _run():
        _jobs[job_id]["status"] = "running"
        try:
            paths = await sync_project(req.video_id, req.file_type)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["files"] = [str(p) for p in paths]
        except PermissionError as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            log.error("Download failed for %s: %s", req.video_id, e)

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "pending"}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Check the status of a background download job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/scheduler/trigger")
async def trigger_sync_now(background_tasks: BackgroundTasks):
    """Manually trigger the scheduled sync immediately."""
    from scheduler import _sync_all
    background_tasks.add_task(_sync_all)
    return {"status": "triggered"}
