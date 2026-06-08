import express from "express";
import path from "path";
import dotenv from "dotenv";
import * as fs from "fs";
import * as os from "os";
import { spawn } from "child_process";
import apiRoutes from "./routes/api";
import { CONFIG } from "./config";

dotenv.config();

const app = express();
const PORT = CONFIG.PORT;

// --- Spawn persistent Python Bridge micro-service ---
const BRIDGE_PORT = CONFIG.BRIDGE_PORT;
let bridgeProc: ReturnType<typeof spawn> | null = null;
let bridgeRestartCount = 0;
const MAX_BRIDGE_RESTARTS = 5;

function startPythonBridge() {
  const pythonCmd = process.platform === "win32" ? "python" : "python3";
  const scriptPath = path.join(process.cwd(), "comic_video", "bridge_server.py");
  bridgeProc = spawn(pythonCmd, [scriptPath], {
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
    env: { ...process.env, BRIDGE_PORT: String(BRIDGE_PORT) },
  });
  bridgeProc.stdout?.on("data", (d) => console.log(`[BRIDGE] ${d.toString().trim()}`));
  bridgeProc.stderr?.on("data", (d) => console.error(`[BRIDGE-ERR] ${d.toString().trim()}`));
  bridgeProc.on("close", (code) => {
    console.warn(`[BRIDGE] Python bridge exited with code ${code}`);
    bridgeProc = null;
    if (bridgeRestartCount < MAX_BRIDGE_RESTARTS) {
      bridgeRestartCount++;
      const delay = Math.min(5000, 1000 * Math.pow(2, bridgeRestartCount - 1));
      console.log(`[BRIDGE] Restarting in ${delay}ms (attempt ${bridgeRestartCount}/${MAX_BRIDGE_RESTARTS})...`);
      setTimeout(startPythonBridge, delay);
    } else {
      console.error(`[BRIDGE] Max restarts (${MAX_BRIDGE_RESTARTS}) reached. Bridge will stay down.`);
    }
  });
  bridgeProc.on("error", (err) => {
    console.error(`[BRIDGE] Failed to start bridge: ${err.message}`);
  });
  console.log(`[BRIDGE] Starting Python OCR micro-service on port ${BRIDGE_PORT}...`);
}
startPythonBridge();

/** Poll /health until the bridge is ready (max 30s). */
async function waitForBridgeReady(): Promise<boolean> {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1000);
    try {
      const res = await fetch(`http://127.0.0.1:${BRIDGE_PORT}/health`, { signal: controller.signal });
      clearTimeout(timer);
      if (res.ok) return true;
    } catch {
      clearTimeout(timer);
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

process.on("exit", () => {
  if (bridgeProc && !bridgeProc.killed) bridgeProc.kill("SIGTERM");
});
process.on("SIGINT", () => {
  if (bridgeProc && !bridgeProc.killed) bridgeProc.kill("SIGTERM");
  process.exit(0);
});
process.on("SIGTERM", () => {
  if (bridgeProc && !bridgeProc.killed) bridgeProc.kill("SIGTERM");
  process.exit(0);
});

// Increase payload limit for uploading PDFs and base64 images
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ limit: "50mb", extended: true }));

// --- Simple in-memory rate limiter (30 req/min per IP) ---
const requestCounts = new Map<string, { count: number; resetTime: number }>();
const RATE_WINDOW_MS = CONFIG.RATE_WINDOW_MS;
const RATE_MAX = CONFIG.RATE_MAX;
app.use((req, res, next) => {
  const ip = req.ip || req.socket.remoteAddress || "unknown";
  const now = Date.now();
  const entry = requestCounts.get(ip);
  if (!entry || now > entry.resetTime) {
    requestCounts.set(ip, { count: 1, resetTime: now + RATE_WINDOW_MS });
    next();
    return;
  }
  if (entry.count >= RATE_MAX) {
    res.status(429).json({ error: "Too many requests. Please slow down." });
    return;
  }
  entry.count++;
  next();
});

// --- Periodic temp cleanup (runs every 10 min, removes dirs older than 1h) ---
function cleanupOldTempDirs() {
  const tmpBase = os.tmpdir();
  const now = Date.now();
  const ONE_HOUR = 60 * 60 * 1000;
  try {
    for (const entry of fs.readdirSync(tmpBase)) {
      if (entry.startsWith("comic-")) {
        const fullPath = path.join(tmpBase, entry);
        try {
          const stat = fs.statSync(fullPath);
          if (now - stat.mtime.getTime() > ONE_HOUR) {
            fs.rmSync(fullPath, { recursive: true, force: true });
          }
        } catch {}
      }
    }
  } catch {}
}
setInterval(cleanupOldTempDirs, 10 * 60 * 1000);

// Mount API routes
app.use(apiRoutes);
app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

async function startServer() {
  const bridgeReady = await waitForBridgeReady();
  if (!bridgeReady) {
    console.error("[BRIDGE] Could not reach Python bridge after 30s. Continuing without OCR support.");
  } else {
    console.log("[BRIDGE] Python OCR micro-service is ready.");
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[LOCAL API SERVER] Running on host 0.0.0.0 targeting Port ${PORT}`);
  });
}

startServer();
