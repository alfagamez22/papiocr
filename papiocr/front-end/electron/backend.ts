import { ChildProcess, spawn } from "child_process";
import path from "path";
import http from "http";

let proc: ChildProcess | null = null;

// __dirname is electron-dist/ when compiled; go two levels up to papiocr/
const ROOT = path.resolve(__dirname, "..", "..");
const BACKEND_DIR = path.join(ROOT, "back-end");
const VENV_PYTHON = path.join(ROOT, ".venv", "Scripts", "python.exe");
const PORT = 8000;
const HEALTH_URL = `http://127.0.0.1:${PORT}/api/health`;

function waitForReady(maxRetries = 60, interval = 500): Promise<void> {
  return new Promise((resolve, reject) => {
    let tries = 0;
    const check = () => {
      http.get(HEALTH_URL, (res) => {
        if (res.statusCode === 200) resolve();
        else retry();
      }).on("error", retry);
    };
    const retry = () => {
      tries++;
      if (tries >= maxRetries) reject(new Error("Backend failed to start"));
      else setTimeout(check, interval);
    };
    check();
  });
}

export async function startBackend(): Promise<void> {
  if (proc) return;

  proc = spawn(VENV_PYTHON, ["-m", "uvicorn", "src.api:app", "--host", "127.0.0.1", "--port", String(PORT)], {
    cwd: BACKEND_DIR,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  proc.stdout?.on("data", (d: Buffer) => {
    try { process.stdout.write(`[backend] ${d}`); } catch { /* EPIPE: parent closed */ }
  });
  proc.stderr?.on("data", (d: Buffer) => {
    try { process.stderr.write(`[backend] ${d}`); } catch { /* EPIPE: parent closed */ }
  });

  // Prevent unhandled EPIPE on the parent process streams themselves
  process.stdout.on("error", () => {});
  process.stderr.on("error", () => {});

  proc.on("exit", (code) => {
    try { console.log(`Backend exited with code ${code}`); } catch { /* EPIPE */ }
    proc = null;
  });

  await waitForReady();
}

export function stopBackend(): void {
  if (proc) {
    proc.kill("SIGTERM");
    proc = null;
  }
}
