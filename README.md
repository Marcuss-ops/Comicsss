# 🎬 Comic Video Maker

**Analizza fumetti PDF con un LLM locale (Ollama) e genera script narrativi per video YouTube.**

Prende un PDF di un fumetto, estrae ogni pagina come immagine, le analizza con un modello vision-language tramite Ollama (es. Gemma 4 E4B, Llama 3.2 Vision), e produce descrizioni narrative dettagliate per ogni pagina — con supporto batch per velocizzare l'elaborazione.

> 🇮🇹 **Tool progettato per l'italiano** — prompt, descrizioni e dialoghi sono tutti in italiano.

---

## ✨ Funzionalità

| Funzionalità | Descrizione |
|---|---|
| 🖼️ **Estrazione PDF** | Estrae ogni pagina come PNG (200 DPI) con fallback a bassa risoluzione |
| 🤖 **Analisi LLM locale** | Usa Ollama con modelli vision (gemma4:e4b, llama3.2-vision, ecc.) |
| 📦 **Batch processing** | Invia 3-4 pagine per chiamata API (default: 4) — 10x più veloce |
| 🏷️ **Contesto fumetto** | Specifica il titolo con `--title` per identificazione corretta dei personaggi |
| 🦇 **Niente allucinazioni** | I prompt istruiscono il modello a usare i VERI nomi dei personaggi (Batman, Joker, ecc.) |
| 🎬 **Sintesi video** | Opzionale: crea uno script YouTube unificato da TUTTE le pagine |
| 📊 **Output strutturato** | Salva analisi in JSON + TXT (per-pagina e script video) |
| 🎨 **Barra di progresso** | Rich UI con `rich` (colori, tabelle, barre di progresso) |

---

## 📋 Prerequisiti

1. **Python 3.10+**
2. **Ollama** in esecuzione localmente ([scarica da ollama.com](https://ollama.com))
3. **Un modello vision** scaricato in Ollama

### Modelli consigliati

```bash
# Google Gemma 4 E4B (consigliato - supporto vision nativo)
ollama pull gemma4:e4b

# Meta Llama 3.2 Vision
ollama pull llama3.2-vision

# LLaVA
ollama pull llava
```

### Dipendenze Python

```bash
pip install PyMuPDF Pillow requests rich
```

O in alternativa:

```bash
pip install -r requirements-cli.txt
```

### Avvia Ollama

Prima di usare lo script, assicurati che Ollama sia in esecuzione:

```bash
# Avvia il server Ollama (se non già attivo)
ollama serve

# Opzionale: tieni il modello in memoria per la prima risposta più veloce
ollama run gemma4:e4b
# (premi Ctrl+D per uscire mantenendo il modello in cache)
```

---

## 🚀 Utilizzo

### Base — analisi completa

```bash
python comic-video-maker.py "4fumetti-ita-batman-the-killing-joke-dc.pdf"
```

### Con titolo del fumetto (RACCOMANDATO!)

Specificando il titolo con `--title`, il modello SA cosa sta guardando e identifica correttamente i personaggi:

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Batman: The Killing Joke" \
  -o output
```

### Senza `--title` (auto-estrazione dal filename)

Se non passi `--title`, il titolo viene estratto automaticamente dal nome del file:

```
4fumetti-ita-batman-the-killing-joke-dc.pdf  →  "Batman The Killing Joke"
spider-man-2099-ita.pdf                       →  "Spider Man 2099"
```

### Batch processing (consigliato)

Analizza 4 pagine per chiamata Ollama — molto più veloce:

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Batman: The Killing Joke" \
  --batch-size 4 \
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

# Combinazione
python comic-video-maker.py "fumetto.pdf" --pages 1-5,10,15-20
```

### Dry-run (solo estrazione pagine, nessuna analisi)

```bash
python comic-video-maker.py "fumetto.pdf" --dry-run
```

### Modello personalizzato

```bash
python comic-video-maker.py "fumetto.pdf" \
  -m llama3.2-vision \
  --ollama-url http://localhost:11434
```

---

## ⚙️ Argomenti CLI

| Argomento | Default | Descrizione |
|---|---|---|
| `pdf` | *(obbligatorio)* | Percorso del file PDF del fumetto |
| `-o, --output` | `output` | Directory di output |
| `-m, --model` | `gemma4:e4b` | Modello Ollama da usare |
| `--ollama-url` | `http://localhost:11434` | URL del server Ollama |
| `--pages` | *(tutte)* | Pagine da elaborare (es. `1-10`, `1,3,5-7`) |
| `--batch-size` | `4` | Pagine per chiamata Ollama (default: 4) |
| `--dpi` | `200` | DPI per estrazione pagine |
| `--timeout` | `600` | Timeout per chiamata API (secondi) |
| `--temperature` | `0.3` | Temperature del modello |
| `--title` | *(auto)* | Titolo del fumetto (es. `"Batman: The Killing Joke"`) |
| `--no-synthesis` | *(off)* | Salta la sintesi finale dello script video |
| `--dry-run` | *(off)* | Solo estrai pagine, non chiamare Ollama |
| `--keep-images` | *(off)* | Mantieni le immagini dopo l'analisi |
| `--version` | — | Mostra versione |

---

## 🧪 Esempi completi

### 1. Analisi completa di Batman: The Killing Joke (52 pagine, batch 4)

```bash
python comic-video-maker.py "4fumetti-ita-batman-the-killing-joke-dc.pdf" \
  -o output_batman \
  --title "Batman: The Killing Joke" \
  --batch-size 4 \
  --keep-images
```

### 2. Solo analisi pagine 1-10, senza sintesi

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Watchmen" \
  --pages 1-10 \
  --batch-size 3 \
  --no-synthesis \
  -o output_10pg
```

### 3. Test veloce (prime 4 pagine)

```bash
python comic-video-maker.py "fumetto.pdf" \
  --title "Batman: The Killing Joke" \
  --pages 1-4 \
  --batch-size 2 \
  --no-synthesis \
  --keep-images \
  -o test_fast
```

---

## 📂 Output

Lo script genera 3 file nella directory di output:

| File | Contenuto |
|---|---|
| `*_analisi.json` | Dati strutturati completi (tutte le pagine + script video) |
| `*_script_pagine.txt` | Descrizione narrativa per OGNI pagina (leggibile) |
| `*_script_video.txt` | Script video YouTube unificato (solo con sintesi) |
| `pages/` | Immagini delle pagine (solo con `--keep-images`) |

### Esempio di output per-pagina

```
============================================================
PAGINA 1 — L'Anarchia del Riso
============================================================

🎬 DESCRIZIONE NARRATIVA:
Il tono è immediatamente cupo e opprimente. La scena ci immerge
in un vicolo urbano notturno, dove le ombre sembrano avere vita
propria, accarezzando i contorni di Batman. Il Joker si muove
come una forza gravitazionale negativa...

💬 DIALOGHI:
Joker: "E tu credi davvero di poter fermarmi? Solo un riso che continua..."

👥 PERSONAGGI: Batman, Joker
🔊 EFFETTO SONORO: WHOOSH!
⏱ DURATA: 18 secondi
```

---

## 🧠 Come funziona

```
PDF Fumetto
    │
    ▼
┌─────────────────────┐
│  Estrazione pagine   │  PyMuPDF (200 DPI)
│  (salvataggio come   │
│   PNG + resize)      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Batch processing    │  4 pagine per chiamata
│  (analisi con LLM    │  Ollama API /api/generate
│   visione)           │  Prompt in italiano
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Output strutturato  │  JSON + TXT
│  (descrizioni,       │
│   dialoghi, effetti) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Sintesi video (opt) │  Script YouTube unificato
│  (tutte le pagine    │  da 2000-4000 parole
│   in unico script)   │
└─────────────────────┘
```

### Perché usare `--title`?

Senza il titolo, il modello **inventa personaggi** — potrebbe chiamare Batman "Kaito" o "Kael", il Joker "Silas", e creare una storia fantasy generica.

Con `--title "Batman: The Killing Joke"`, il prompt dice esplicitamente al modello cosa sta guardando, e le descrizioni diventano **accurate** — con Batman, Joker, Barbara Gordon, Commissioner Gordon, ecc.

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
