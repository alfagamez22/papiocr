"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path_1 = __importDefault(require("path"));
const backend_1 = require("./backend");
const isDev = process.env.NODE_ENV !== "production";
let mainWindow = null;
function createWindow() {
    mainWindow = new electron_1.BrowserWindow({
        width: 1280,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        title: "papiocr",
        show: true,
        backgroundColor: "#1a1a1a",
        webPreferences: {
            preload: path_1.default.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    mainWindow.webContents.on("did-fail-load", (_e, code, desc) => {
        console.error(`[electron] Page failed to load: ${code} ${desc}`);
        mainWindow?.webContents.reload();
    });
    if (isDev) {
        mainWindow.loadURL("http://localhost:3000");
    }
    else {
        mainWindow.loadFile(path_1.default.join(__dirname, "..", "out", "index.html"));
    }
    // Start backend in the background — window stays responsive
    (0, backend_1.startBackend)().catch((err) => {
        console.error(`[electron] Backend failed: ${err.message}`);
    });
}
electron_1.app.whenReady().then(createWindow);
electron_1.app.on("window-all-closed", () => {
    (0, backend_1.stopBackend)();
    if (process.platform !== "darwin")
        electron_1.app.quit();
});
electron_1.app.on("before-quit", () => {
    (0, backend_1.stopBackend)();
});
