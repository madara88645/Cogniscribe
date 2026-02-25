const { execSync, execFileSync, spawn } = require("node:child_process");
const net = require("node:net");
const path = require("node:path");

const ROOT = process.cwd();

function runNodeScript(scriptRelative, args = []) {
  const scriptPath = path.join(ROOT, "scripts", scriptRelative);
  execFileSync(process.execPath, [scriptPath, ...args], {
    cwd: ROOT,
    stdio: "inherit",
    env: process.env,
  });
}

function spawnNpm(scriptName) {
  return spawn(`npm run ${scriptName}`, {
    cwd: ROOT,
    stdio: "inherit",
    env: process.env,
    shell: true,
  });
}

function waitForPort(port, timeoutMs) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    const tryConnect = () => {
      const socket = new net.Socket();
      socket.setTimeout(1200);

      socket.once("connect", () => {
        socket.destroy();
        resolve(true);
      });

      const onFail = () => {
        socket.destroy();
        if (Date.now() - start >= timeoutMs) {
          reject(new Error(`Timed out waiting for port ${port}`));
          return;
        }
        setTimeout(tryConnect, 300);
      };

      socket.once("error", onFail);
      socket.once("timeout", onFail);
      socket.connect(port, "127.0.0.1");
    };

    tryConnect();
  });
}

(async () => {
  let renderer = null;
  let electronLauncher = null;

  const shutdown = (code = 0) => {
    if (electronLauncher && !electronLauncher.killed) {
      electronLauncher.kill();
    }
    if (renderer && !renderer.killed) {
      renderer.kill();
    }
    process.exit(code);
  };

  process.on("SIGINT", () => shutdown(0));
  process.on("SIGTERM", () => shutdown(0));

  try {
    console.log("[dev] Preparing port 5173...");
    runNodeScript("free-dev-port.cjs", ["5173"]);

    console.log("[dev] Starting renderer...");
    renderer = spawnNpm("dev:renderer");
    renderer.on("exit", (code, signal) => {
      if (code !== 0) {
        console.error(`[dev] renderer exited (code=${code}, signal=${signal || "-"})`);
        shutdown(code || 1);
      }
    });

    await waitForPort(5173, 30000);
    console.log("[dev] Renderer is ready on 5173.");

    console.log("[dev] Building Electron main/preload...");
    execSync("npm run build:electron", { cwd: ROOT, stdio: "inherit", env: process.env });

    console.log("[dev] Launching Electron...");
    electronLauncher = spawn(process.execPath, [path.join(ROOT, "scripts", "run-electron-dev.cjs")], {
      cwd: ROOT,
      stdio: "inherit",
      env: process.env,
      shell: false,
    });

    electronLauncher.on("exit", (code, signal) => {
      if (code !== 0) {
        console.error(`[dev] electron launcher exited (code=${code}, signal=${signal || "-"})`);
        shutdown(code || 1);
      }
      shutdown(0);
    });
  } catch (err) {
    console.error("[dev] startup failed:", err && err.message ? err.message : err);
    shutdown(1);
  }
})();
