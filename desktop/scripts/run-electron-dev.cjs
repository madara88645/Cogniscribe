const { spawn } = require("node:child_process");

const electronBinary = require("electron");
const env = { ...process.env };

delete env.ELECTRON_RUN_AS_NODE;
env.ELECTRON_START_URL = "http://localhost:5173";

const child = spawn(electronBinary, ["."], {
  stdio: "inherit",
  env,
  shell: false,
});

child.on("error", (err) => {
  console.error("Failed to launch Electron:", err);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
