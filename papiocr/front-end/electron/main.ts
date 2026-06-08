import { app, BrowserWindow } from "electron";
import path from "path";
import { startBackend, stopBackend } from "./backend";

const isDev = process.env.NODE_ENV !== "production";

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "papiocr",
    show: true,
    backgroundColor: "#1a1a1a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
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
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "out", "index.html"));
  }

  // Start backend in the background — window stays responsive
  startBackend().catch((err) => {
    console.error(`[electron] Backend failed: ${err.message}`);
  });
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopBackend();
});
