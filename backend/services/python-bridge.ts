import path from "path";
import { CONFIG } from "../config";

const BRIDGE_BASE_URL = CONFIG.BRIDGE_URL || `http://127.0.0.1:${CONFIG.BRIDGE_PORT}`;

export async function runPythonBridge(imagePath: string, timeoutMs = CONFIG.BRIDGE_TIMEOUT_MS): Promise<any> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BRIDGE_BASE_URL}/ocr`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_path: path.resolve(imagePath) }),
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Bridge OCR HTTP ${res.status}: ${text}`);
    }

    const result = await res.json();
    if (result.error) {
      throw new Error(result.error);
    }
    return result;
  } catch (err: any) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new Error(`Bridge OCR timed out after ${timeoutMs}ms`);
    }
    throw err;
  }
}
