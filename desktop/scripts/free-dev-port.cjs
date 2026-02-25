const { execSync } = require("node:child_process");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getPidsOnPortWindows(port) {
  let output = "";
  try {
    output = execSync(`netstat -ano -p tcp | findstr :${port}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
  } catch {
    return [];
  }

  const pids = new Set();
  for (const line of output.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    // Example: TCP  127.0.0.1:5173  0.0.0.0:0  LISTENING  1234
    const parts = trimmed.split(/\s+/);
    if (parts.length < 5) continue;
    const localAddr = parts[1] || "";
    const state = parts[3] || "";
    const pid = parts[4] || "";
    if (!localAddr.endsWith(`:${port}`)) continue;
    if (state.toUpperCase() !== "LISTENING") continue;
    if (!/^\d+$/.test(pid)) continue;
    pids.add(Number(pid));
  }
  return Array.from(pids);
}

function killPidWindows(pid) {
  try {
    execSync(`taskkill /PID ${pid} /F`, { stdio: ["ignore", "ignore", "ignore"] });
    return true;
  } catch {
    return false;
  }
}

async function main() {
  const port = Number(process.argv[2] || 5173);
  if (!Number.isFinite(port) || port <= 0) {
    console.error("[dev:prepare] Invalid port");
    process.exit(1);
  }

  if (process.platform !== "win32") {
    // No-op outside Windows for now.
    process.exit(0);
  }

  const pids = getPidsOnPortWindows(port).filter((pid) => pid !== process.pid);
  if (pids.length === 0) {
    process.exit(0);
  }

  console.log(`[dev:prepare] Port ${port} is busy. Killing PID(s): ${pids.join(", ")}`);
  let killedAny = false;
  for (const pid of pids) {
    const ok = killPidWindows(pid);
    if (ok) killedAny = true;
  }

  await sleep(350);
  const remaining = getPidsOnPortWindows(port);
  if (remaining.length > 0) {
    console.error(`[dev:prepare] Port ${port} is still busy: ${remaining.join(", ")}`);
    process.exit(1);
  }

  if (killedAny) {
    console.log(`[dev:prepare] Port ${port} is now free.`);
  }
}

main().catch((err) => {
  console.error("[dev:prepare] Unexpected error:", err);
  process.exit(1);
});
