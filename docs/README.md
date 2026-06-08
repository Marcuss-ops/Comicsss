# Comic Video Maker

Local-only comic PDF analysis toolkit.

## What it does

- Renders PDF pages to images with PyMuPDF
- Detects panels with OpenCV
- Extracts balloon text with EasyOCR
- Exposes a small Express API for panel extraction
- Runs a Python bridge for OCR and panel detection
- Provides a CLI for full local analysis

## What was removed

- No web UI
- No online model calls
- No online image, speech, or video generation routes

## Run

```bash
npm install
npm run dev
```

The API listens on `PORT` from `.env` and exposes:

- `GET /health`
- `POST /api/extract-panels`

For full local analysis, use the Python CLI:

```bash
python bin/cli.py analyze "inputs/your-comic.pdf" --scene-json
```
