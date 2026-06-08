import { Router } from "express";
import { runPythonBridge } from "../services/python-bridge";
import * as fs from "fs";
import * as os from "os";
import path from "path";

const router = Router();

function stripDataUrl(data: string): string {
  if (!data) return "";
  if (data.includes(";base64,")) {
    return data.split(";base64,")[1];
  }
  return data;
}

function buildLocalPanelSummary(combinedText: string, pageNumber: number, panelNumber: number) {
  const text = combinedText.trim();
  if (!text) {
    return {
      narrativeCaption: "",
      youtubeDescription: `Vignetta locale ${panelNumber} della pagina ${pageNumber}. Nessun testo OCR leggibile rilevato, quindi la lettura si concentra sulla composizione visiva.`,
    };
  }

  const preview = text.length > 240 ? `${text.slice(0, 240).trim()}...` : text;
  return {
    narrativeCaption: text,
    youtubeDescription: `Vignetta locale ${panelNumber} della pagina ${pageNumber}. Testo OCR rilevato: ${preview}`,
  };
}

router.post("/api/extract-panels", async (req, res) => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "comic-"));
  try {
    const { file, pageNumber, totalPages } = req.body;
    if (!file || !file.data) {
      res.status(400).json({ error: "No comic file uploaded for panel extraction." });
      return;
    }

    const mimeType = file.mimeType || file.type || "image/jpeg";
    const rawBase64 = stripDataUrl(file.data);
    const ext = mimeType === "image/png" ? "png" : "jpg";
    const tmpPath = path.join(tmpDir, `page.${ext}`);

    fs.writeFileSync(tmpPath, Buffer.from(rawBase64, "base64"));

    const ocrResult = await runPythonBridge(tmpPath);
    const panels = Array.isArray(ocrResult.panels) ? ocrResult.panels : [];

    const localPanels = panels.map((panel: any) => {
      const panelNumber = Number(panel.panel_index ?? panel.panelNumber ?? 0) + 1;
      const summary = buildLocalPanelSummary(panel.combined_text || "", pageNumber || 1, panelNumber);

      return {
        panelNumber,
        pageNumber: pageNumber || 1,
        characters: [],
        narrativeCaption: summary.narrativeCaption,
        youtubeDescription: summary.youtubeDescription,
      };
    });

    if (localPanels.length === 0) {
      localPanels.push({
        panelNumber: 1,
        pageNumber: pageNumber || 1,
        characters: [],
        narrativeCaption: "",
        youtubeDescription: `Pagina ${pageNumber || 1}: nessun pannello rilevato dal bridge OCR locale.`,
      });
    }

    res.json({
      title: "Local Comic Extraction",
      pageCount: totalPages || 1,
      summary: "Estrazione locale completata con OCR e rilevamento pannelli. Nessun servizio online coinvolto.",
      panels: localPanels,
    });
  } catch (err: any) {
    console.error("Error extracting panels:", err);
    res.status(500).json({ error: err.message || "Failed to process the comic panel extractor pipeline." });
  } finally {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {}
  }
});

export default router;
