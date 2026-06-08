# Comic Video Maker

Backend-only comic PDF analysis toolkit.

## What remains

- Python CLI for local analysis
- Express API for panel extraction
- Python bridge for OCR and panel detection

## Removed

- Web UI
- Online model routes
- Online image, speech, and video generation

## Run

```bash
npm install
npm run dev
```

For full analysis from the command line:

```bash
python bin/cli.py analyze "inputs/your-comic.pdf" --scene-json
```
