import dotenv from "dotenv";
dotenv.config();

/**
 * Centralized configuration — single source of truth for environment variables.
 *
 * Both TypeScript and Python sides read from the same .env keys.
 * Values loaded here are inherited by child Python processes.
 */

export const CONFIG = {
  // Ollama (shared with Python)
  OLLAMA_URL: process.env.OLLAMA_URL || "http://localhost:11434",
  OLLAMA_MODEL: process.env.OLLAMA_MODEL || "qwen2.5vl:7b",
  OLLAMA_TIMEOUT_SECONDS: parseInt(process.env.OLLAMA_TIMEOUT_SECONDS || "300", 10),

  // Bridge micro-service
  BRIDGE_PORT: parseInt(process.env.BRIDGE_PORT || "8081", 10),
  BRIDGE_URL: process.env.BRIDGE_URL || "",
  BRIDGE_TIMEOUT_MS: parseInt(process.env.BRIDGE_TIMEOUT_MS || "90000", 10),

  // Server
  NODE_ENV: process.env.NODE_ENV || "development",
  PORT: parseInt(process.env.PORT || "3000", 10),

  // Rate limiting
  RATE_WINDOW_MS: parseInt(process.env.RATE_WINDOW_MS || "60000", 10),
  RATE_MAX: parseInt(process.env.RATE_MAX || "30", 10),
} as const;
