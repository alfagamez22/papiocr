"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.startBackend = startBackend;
exports.stopBackend = stopBackend;
const child_process_1 = require("child_process");
const path_1 = __importDefault(require("path"));
const http_1 = __importDefault(require("http"));
let proc = null;
// __dirname is electron-dist/ when compiled; go two levels up to papiocr/
const ROOT = path_1.default.resolve(__dirname, "..", "..");
const BACKEND_DIR = path_1.default.join(ROOT, "back-end");
const VENV_PYTHON = path_1.default.join(ROOT, ".venv", "Scripts", "python.exe");
const PORT = 8000;
const HEALTH_URL = `http://127.0.0.1:${PORT}/api/health`;
function waitForReady(maxRetries = 60, interval = 500) {
    return new Promise((resolve, reject) => {
        let tries = 0;
        const check = () => {
            http_1.default.get(HEALTH_URL, (res) => {
                if (res.statusCode === 200)
                    resolve();
                else
                    retry();
            }).on("error", retry);
        };
        const retry = () => {
            tries++;
            if (tries >= maxRetries)
                reject(new Error("Backend failed to start"));
            else
                setTimeout(check, interval);
        };
        check();
    });
}
async function startBackend() {
    if (proc)
        return;
    proc = (0, child_process_1.spawn)(VENV_PYTHON, ["-m", "uvicorn", "src.api:app", "--host", "127.0.0.1", "--port", String(PORT)], {
        cwd: BACKEND_DIR,
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
    });
    proc.stdout?.on("data", (d) => {
        try {
            process.stdout.write(`[backend] ${d}`);
        }
        catch { /* EPIPE: parent closed */ }
    });
    proc.stderr?.on("data", (d) => {
        try {
            process.stderr.write(`[backend] ${d}`);
        }
        catch { /* EPIPE: parent closed */ }
    });
    // Prevent unhandled EPIPE on the parent process streams themselves
    process.stdout.on("error", () => { });
    process.stderr.on("error", () => { });
    proc.on("exit", (code) => {
        try {
            console.log(`Backend exited with code ${code}`);
        }
        catch { /* EPIPE */ }
        proc = null;
    });
    await waitForReady();
}
function stopBackend() {
    if (proc) {
        proc.kill("SIGTERM");
        proc = null;
    }
}
