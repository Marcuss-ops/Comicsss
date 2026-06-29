# Comic Video Maker - GEMINI.md

## Overview
This module is a toolkit for analyzing comic PDFs, extracting panels, and performing OCR. It was integrated from the `Comicsss` repository.

## Architecture
The module uses a hybrid stack:
- **Backend API**: Node.js/Express server in `backend/`.
- **Core Logic**: Python modules in `comic_video/`.
- **Bridge**: A Python FastAPI bridge (`comic_video/bridge_server.py`) started by the Node.js backend to handle heavy processing (OCR, panel detection).

## Integration
- **Directory**: `comic-video-maker/` at the root.
- **Makefile**: Use `make comic-video-maker-run` to start the service.
- **Configuration**: Managed via `comic_video_maker` section in `config.yaml`.
- **Google Drive**: Dedicated folder `1VlGieAZBqediQvLXcKDTLmHTy0e9Ujek` configured in `drive.comics_root_folder`.

## Ingestion & Semantic Search
To index comic analysis results into the main database and enable semantic search in Qdrant:
```bash
python3 scripts/ingest_comic.py path/to/analysis.json --qdrant-url http://localhost:6333
```
This script will:
1. Parse the JSON output from the comic analyzer.
2. Generate rich semantic metadata for each page.
3. Compute E5 embeddings for the text.
4. Store the data in `data/media/media.db.sqlite`.
5. Push the vectors to the `pipelinegen_assets` collection in Qdrant.

## Key Components
- `comic_video/panel_detector.py`: Logic for identifying panels in comic pages.
- `comic_video/bridge_ocr.py`: Interfaces with OCR engines.
- `backend/server.ts`: The main Express server that orchestrates the pipeline.

## Operational Notes
- **Starting**: Run `npm run dev` or `make comic-video-maker-run`.
- **Dependencies**: Requires both Node.js and Python 3.10+ environments.
- **Inputs**: Place PDF files in `inputs/` for manual CLI processing or upload via the API.
