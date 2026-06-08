# 🎬 Comic Video Maker

**Analizza fumetti PDF con un LLM locale (Ollama) e genera script narrativi per video YouTube.**

Prende un PDF di un fumetto, estrae ogni pagina come immagine, le segmenta in vignette con OpenCV, rileva balloon e testo con EasyOCR, e analizza ogni vignetta con un modello vision-language tramite Ollama (es. LLaVA 13B, Llama 3.2 Vision). Produce descrizioni narrative dettagliate, script video YouTube e transcript scena-per-scena.

> 🇮🇹 **Tool progettato per l'italiano** — prompt, descrizioni e dialoghi sono tutti in italiano.

---

## ✨ Funzionalità

| Funzionalità | Descrizione |
|---|---|
| 🖼️ **Estrazione PDF** | Estrae ogni pagina come PNG (200 DPI) con caching automatico |
| 📐 **Panel Detection** | Rileva vignette con doppio algoritmo (gutter + contour) — layout regolari e irregolari |
| 🎈 **Balloon OCR** | Rileva fumetti e estrae testo con EasyOCR (fallback full-image OCR) |
| 🤖 **Analisi LLM locale** | Usa Ollama con modelli vision (llava:13b, llama3.2-vision, gemma4:e4b) |
| 🦇 **Niente allucinazioni** | Ogni vignetta analizzata singolarmente + OCR affidabile dal balloon |
| 🎬 **Sintesi video** | Script YouTube unificato da TUTTE le vignette |
| 🎭 **Scene Transcript** | Raggruppa pagine in scene e produce JSON formato YouTube (--scene-json) |
| 🌍 **Global Analysis** | Analisi atmosfera globale della pagina oltre ai singoli pannelli (--global-analysis) |
| 🧪 **Dry-run skip** | Mostra quali pagine verrebbero saltate senza chiamare LLM (--dry-run-skip) |
| 🐞 **Debug visivo** | Immagini debug con pannelli e balloon evidenziati |
| 📊 **Output strutturato** | Salva analisi in JSON v4 + scene transcript separato |

---

## 📋 Prerequisiti

1. **Python 3.10+**
2. **Ollama** in esecuzione localmente ([scarica da ollama.com](https://ollama.com))
3. **Un modello vision** scaricato in Ollama

### Modelli consigliati

```bash
# Meta Llama 3.2 Vision (consigliato - 11B, contesto 128K)
ollama pull llama3.2-vision:11b

# LLaVA 13B (buon bilanciamento)
ollama pull llava:13b

# Google Gemma 4 E4B
ollama pull gemma4:e4b
```

### Dipendenze Python

```bash
pip install -r requirements-cli.txt
```

### Avvia Ollama

```bash
# Avvia il server Ollama (se non già attivo)
ollama serve
```

---

## 🚀 Utilizzo

### Base — analisi completa

```bash
python comic-video-maker.py "4fumetti-ita-batman-the-killing-joke-dc.pdf"
```

### Con tutte le feature avanzate

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Batman: The Killing Joke" \
  --model llava:13b \
  --global-analysis \
  --scene-json \
  --debug-panels \
  --no-skip-no-balloon \
  -o output
```

### Solo analisi pagine (senza sintesi video)

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Batman: The Killing Joke" \
  --no-synthesis \
  -o output
```

### Selezionare pagine specifiche

```bash
# Solo pagine 1-10
python comic-video-maker.py "fumetto.pdf" --pages 1-10

# Pagine specifiche
python comic-video-maker.py "fumetto.pdf" --pages 1,3,5,7
```

### Dry-run (solo estrazione pagine + panel detect, nessuna analisi)

```bash
python comic-video-maker.py "fumetto.pdf" --dry-run
```

### Dry-run skip (mostra quali pagine verrebbero saltate)

```bash
python comic-video-maker.py "fumetto.pdf" --dry-run-skip
```

### Modello personalizzato

```bash
python comic-video-maker.py "fumetto.pdf" \
  -m llama3.2-vision:11b \
  --ollama-url http://localhost:11434
```

---

## ⚙️ Argomenti CLI completi

| Argomento | Default | Descrizione |
|---|---|---|
| `pdf` | *(obbligatorio)* | Percorso del file PDF del fumetto |
| `-o, --output` | `output` | Directory di output |
| `-m, --model` | `llava:13b` | Modello Ollama da usare |
| `--ollama-url` | `http://localhost:11434` | URL del server Ollama |
| `--pages` | *(tutte)* | Pagine da elaborare (es. `1-10`, `1,3,5-7`) |
| `--dpi` | `200` | DPI per estrazione pagine |
| `--timeout` | `300` | Timeout per chiamata API (secondi) |
| `--title` | *(auto)* | Titolo del fumetto (es. `"Batman: The Killing Joke"`) |
| `--no-synthesis` | *(off)* | Salta la sintesi finale dello script video |
| `--no-panel-detect` | *(off)* | Disabilita panel detection (analisi pagina intera) |
| `--no-ocr` | *(off)* | Disabilita OCR EasyOCR |
| `--no-cache` | *(off)* | Rimuovi immagini pagina dopo analisi |
| `--no-balloon-ocr` | *(off)* | Disabilita rilevamento balloon + OCR |
| `--no-skip-no-balloon` | *(off)* | Analizza TUTTE le pagine (anche senza balloon) |
| `--global-analysis` | *(off)* | Aggiungi analisi globale della pagina (atmosfera, composizione) |
| `--scene-json` | *(off)* | Genera output scene JSON formato YouTube transcript |
| `--dry-run` | *(off)* | Solo estrai pagine + panel detect, nessuna chiamata LLM |
| `--dry-run-skip` | *(off)* | Mostra quali pagine verrebbero saltate |
| `--debug-panels` | *(off)* | Salva immagini debug con pannelli evidenziati |
| `--debug-balloons` | *(off)* | Salva immagini debug con balloon evidenziati e testi OCR |
| `--version` | — | Mostra versione |

---

## 🧪 Esempi completi

### 1. Analisi completa di Batman: The Killing Joke + scene transcript

```bash
python comic-video-maker.py "4fumetti-ita-batman-the-killing-joke-dc.pdf" \
  -o output_batman \
  --title "Batman: The Killing Joke" \
  --model llava:13b \
  --global-analysis \
  --scene-json \
  --debug-panels \
  --no-skip-no-balloon
```

### 2. Solo analisi pagine 1-10, senza sintesi

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Watchmen" \
  --pages 1-10 \
  --no-synthesis \
  -o output_10pg
```

### 3. Test veloce (prime 4 pagine)

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Batman: The Killing Joke" \
  --pages 1-4 \
  --no-synthesis \
  --debug-panels \
  --no-cache \
  -o test_fast
```

---

## 📂 Output

Lo script genera nella directory di output:

| File | Contenuto |
|---|---|
| `*_analisi_v4.json` | Dati strutturati completi (analisi pannelli, script video, analisi globali, scene) |
| `*_scene_transcript.json` | Transcript scene formato YouTube (solo con `--scene-json`) |
| `pages/` | Immagini delle pagine estratte (cache) |
| `debug_panels/` | Immagini debug con pannelli evidenziati (solo con `--debug-panels`) |
| `debug_balloons/` | Immagini debug con balloon evidenziati (solo con `--debug-balloons`) |

### Formato scene transcript

```json
{
  "project": {
    "title": "Batman: The Killing Joke",
    "language": "it",
    "format": "youtube_transcript_scene_json"
  },
  "scenes": [
    {
      "scene_id": 1,
      "title": "Il Sorriso di Gotham",
      "pages": "1-3",
      "location": "Vicolo di Gotham City, notte",
      "characters": ["Batman", "Joker"],
      "visual_description": "La città è avvolta nell'oscurità...",
      "voiceover": "Benvenuti a Gotham City...",
      "dialogue_summary": "Joker: 'Perché così serio?'",
      "mood": "Cupo, opprimente",
      "camera_style": "Slow pan dall'alto",
      "youtube_hook": "Cosa trasforma un uomo in un mostro?"
    }
  ]
}
```

---

## 🧠 Come funziona

```
PDF Fumetto
    │
    ▼
┌─────────────────────┐
│  Estrazione pagine   │  PyMuPDF (200 DPI)
│  (PNG + caching)     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Panel Detection     │  OpenCV (gutter + contour)
│  (vignette per pag.) │  Ordine di lettura Y→X
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Balloon OCR         │  EasyOCR
│  (testo dai fumetti) │  Fallback full-image OCR
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  LLM Vision          │  Ogni vignetta
│  (analisi per panel) │  USANDO il testo OCR
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Global Analysis     │  Analisi atmosfera
│  (opzionale)         │  intera pagina
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Scene Synthesis     │  Raggruppa pagine
│  (opzionale)         │  in scene YouTube
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Output JSON         │  v4: analisi + scene
│  + scene transcript  │  + script video
└─────────────────────┘
```

---

## 🛠️ Sviluppo

### Web UI (React + TypeScript)

Il progetto include anche un'interfaccia web in `src/`:

```bash
npm install
npm run dev
```

---

## 📝 Licenza

Progetto personale — MIT
