import { app, BrowserWindow, Menu, Tray, globalShortcut, ipcMain, nativeImage } from "electron";
import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import path from "node:path";
import readline from "node:readline";


type JsonObject = Record<string, any>;

type BackendEvent = {
  event: string;
  data: JsonObject;
  ts?: number;
};

type AppConfig = {
  hotkey?: string;
  exit_hotkey?: string;
  ui?: {
    window?: {
      width?: number;
      height?: number;
      always_on_top?: boolean;
    };
  };
  [key: string]: any;
};

class BackendBridge extends EventEmitter {
  private proc: ChildProcessWithoutNullStreams | null = null;
  private pending = new Map<number, { resolve: (value: any) => void; reject: (err: Error) => void; timeout: NodeJS.Timeout }>();
  private nextId = 1;
  private stopped = false;

  constructor(private readonly backendRoot: string) {
    super();
  }

  async start(): Promise<void> {
    await this.spawnProcess();
  }

  stop(): void {
    this.stopped = true;
    for (const req of this.pending.values()) {
      clearTimeout(req.timeout);
      req.reject(new Error("Backend stopped"));
    }
    this.pending.clear();

    if (this.proc) {
      try {
        this.proc.stdin.write(`${JSON.stringify({ id: 0, method: "shutdown" })}\n`);
      } catch {
        // no-op
      }
      this.proc.kill();
      this.proc = null;
    }
  }

  async request(method: string, params: JsonObject = {}, timeoutMs = 15000): Promise<any> {
    if (!this.proc || !this.proc.stdin.writable) {
      throw new Error("Backend is not running");
    }
    const id = this.nextId++;
    const payload = { id, method, params };

    return await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Backend request timeout: ${method}`));
      }, timeoutMs);

      this.pending.set(id, { resolve, reject, timeout });
      this.proc?.stdin.write(`${JSON.stringify(payload)}\n`);
    });
  }

  private async spawnProcess(): Promise<void> {
    const pythonCmd = process.env.VOICE_PASTE_PYTHON || "python";
    const backendScript = path.join(this.backendRoot, "backend_service.py");

    this.proc = spawn(pythonCmd, [backendScript], {
      cwd: this.backendRoot,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    const stdoutReader = readline.createInterface({ input: this.proc.stdout });
    stdoutReader.on("line", (line) => this.handleStdoutLine(line));

    this.proc.stderr.on("data", (chunk) => {
      this.emit("event", {
        event: "runtime_error",
        data: { message: String(chunk).trim() },
      } satisfies BackendEvent);
    });

    this.proc.on("exit", (code) => {
      this.emit("event", {
        event: "runtime_error",
        data: { message: `Backend exited with code ${code}` },
      } satisfies BackendEvent);

      if (!this.stopped) {
        setTimeout(() => {
          void this.spawnProcess().catch((err) => {
            this.emit("event", {
              event: "runtime_error",
              data: { message: `Backend restart failed: ${String(err)}` },
            } satisfies BackendEvent);
          });
        }, 1200);
      }
    });

    const pingTimeout = Number(process.env.VP_BACKEND_PING_TIMEOUT_MS || 60000);
    await this.request("ping", {}, Number.isFinite(pingTimeout) ? pingTimeout : 60000);
  }

  private handleStdoutLine(line: string): void {
    let payload: any;
    try {
      payload = JSON.parse(line);
    } catch {
      return;
    }

    if (payload?.type === "response") {
      const req = this.pending.get(payload.id);
      if (!req) return;
      clearTimeout(req.timeout);
      this.pending.delete(payload.id);
      if (payload.ok) {
        req.resolve(payload.result);
      } else {
        req.reject(new Error(payload?.error?.message || "Backend error"));
      }
      return;
    }

    if (payload?.type === "event") {
      this.emit("event", payload as BackendEvent);
    }
  }
}

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let backend: BackendBridge;
let configCache: AppConfig | null = null;
let currentStatus = "loading";
let isQuitting = false;

if (typeof app?.on !== "function") {
  // Happens when Electron runs in node mode (RUN_AS_NODE leakage).
  console.error("Electron node mode detected. Check ELECTRON_RUN_AS_NODE.");
  process.exit(1);
}

function getRoots() {
  const devProjectRoot = path.resolve(__dirname, "..", "..");
  const backendRoot = app.isPackaged ? process.resourcesPath : devProjectRoot;
  return { devProjectRoot, backendRoot };
}

function createWindow(config: AppConfig | null): BrowserWindow {
  const width = config?.ui?.window?.width ?? 420;
  const height = config?.ui?.window?.height ?? 620;
  const alwaysOnTop = config?.ui?.window?.always_on_top ?? true;

  const win = new BrowserWindow({
    width,
    height,
    minWidth: 380,
    minHeight: 560,
    show: false,
    frame: true,
    autoHideMenuBar: true,
    title: "Voice Paste Studio",
    alwaysOnTop,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  const startUrl = process.env.ELECTRON_START_URL;
  if (startUrl) {
    void win.loadURL(startUrl);
  } else {
    const indexPath = path.join(__dirname, "..", "renderer", "dist", "index.html");
    void win.loadFile(indexPath);
  }

  win.once("ready-to-show", () => win.show());
  win.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      win.hide();
    }
  });

  return win;
}

function createTrayIcon(): Tray {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="14" fill="#9a6b2f"/><rect x="27" y="15" width="10" height="30" rx="5" fill="white"/><rect x="22" y="45" width="20" height="6" rx="3" fill="white"/></svg>`;
  const dataUrl = `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
  const icon = nativeImage.createFromDataURL(dataUrl);
  return new Tray(icon);
}

async function toggleListening(): Promise<void> {
  if (currentStatus === "listening") {
    await backend.request("stop_listening");
  } else {
    await backend.request("start_listening");
  }
}

function updateTrayMenu() {
  if (!tray) return;
  const listening = currentStatus === "listening";
  const template = [
    { label: "Show", click: () => mainWindow?.show() },
    {
      label: listening ? "Stop Listening" : "Start Listening",
      click: () => {
        void toggleListening();
      },
    },
    { type: "separator" as const },
    {
      label: "Quit",
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ];

  tray.setToolTip(`Voice Paste Studio - ${currentStatus}`);
  tray.setContextMenu(Menu.buildFromTemplate(template));
}

async function registerHotkeys(config: AppConfig | null): Promise<void> {
  globalShortcut.unregisterAll();
  const hotkey = config?.hotkey || "ctrl+shift+space";
  const exitHotkey = config?.exit_hotkey || "ctrl+shift+q";

  globalShortcut.register(hotkey, () => {
    void toggleListening();
  });
  globalShortcut.register(exitHotkey, () => {
    isQuitting = true;
    app.quit();
  });
}

function setupIpcHandlers() {
  ipcMain.handle("voicepaste:startListening", () => backend.request("start_listening"));
  ipcMain.handle("voicepaste:stopListening", () => backend.request("stop_listening"));
  ipcMain.handle("voicepaste:getConfig", async () => {
    configCache = await backend.request("get_config");
    return configCache;
  });
  ipcMain.handle("voicepaste:updateConfig", async (_event, patch: JsonObject) => {
    configCache = await backend.request("update_config", patch);
    await registerHotkeys(configCache);
    if (mainWindow && typeof configCache?.ui?.window?.always_on_top === "boolean") {
      mainWindow.setAlwaysOnTop(configCache.ui.window.always_on_top);
    }
    return configCache;
  });
}

async function bootstrap() {
  await app.whenReady();

  const roots = getRoots();
  backend = new BackendBridge(roots.backendRoot);
  await backend.start();

  configCache = await backend.request("get_config");
  mainWindow = createWindow(configCache);

  tray = createTrayIcon();
  tray.on("double-click", () => mainWindow?.show());
  updateTrayMenu();

  setupIpcHandlers();
  await registerHotkeys(configCache);

  backend.on("event", (payload: BackendEvent) => {
    if (payload.event === "status_changed" && payload.data?.status) {
      currentStatus = String(payload.data.status);
      updateTrayMenu();
    }
    mainWindow?.webContents.send("voicepaste:event", payload);
  });

  app.on("activate", () => {
    if (!mainWindow) {
      mainWindow = createWindow(configCache);
      updateTrayMenu();
    }
    mainWindow.show();
  });
}

app.on("window-all-closed", () => {
  // Keep app in tray.
});

app.on("will-quit", () => {
  isQuitting = true;
  globalShortcut.unregisterAll();
  backend?.stop();
});

void bootstrap().catch((err) => {
  // eslint-disable-next-line no-console
  console.error("Bootstrap error", err);
  app.quit();
});
