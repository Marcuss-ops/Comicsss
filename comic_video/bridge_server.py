#!/usr/bin/env python3
"""
FastBridge — micro-servizio Python persistente per OCR dei fumetti.

Endpoint:
    POST /ocr
    Body: {"image_path": "path/to/page.png"}
    Response: {"page_width": ..., "page_height": ..., "panel_count": ..., "panels": [...]}

Avvio:
    python comic_video/bridge_server.py
    oppure: uvicorn comic_video.bridge_server:app --host 127.0.0.1 --port 8081
"""

import sys
from pathlib import Path

from comic_video.config import BRIDGE_PORT

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from comic_video.bridge_ocr import run_ocr

app = FastAPI(title="ComicBridge OCR", version="1.0.0")


class OcrRequest(BaseModel):
    image_path: str


class OcrResponse(BaseModel):
    page_width: int
    page_height: int
    panel_count: int
    panels: list[dict]


@app.post("/ocr", response_model=OcrResponse)
async def ocr_endpoint(req: OcrRequest):
    result = run_ocr(req.image_path)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return OcrResponse(
        page_width=result["page_width"],
        page_height=result["page_height"],
        panel_count=result["panel_count"],
        panels=result["panels"],
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


def run_bridge(port: int = BRIDGE_PORT, host: str = "127.0.0.1"):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_bridge(port=BRIDGE_PORT)
