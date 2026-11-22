// Graba pitch/index.html cuadro por cuadro con Chrome sin ventana y lo une con ffmpeg.
//
//   node pitch/grabar.mjs                    -> pitch/agroprecio_pitch.mp4 (3:00) y pitch/agroprecio_cierre.mp4
//   node pitch/grabar.mjs --fotos 3,20,45    -> una imagen PNG por cada segundo indicado, en pitch/fotos/
//
// Variables: CHROME (ruta de Chrome), FFMPEG (ruta de ffmpeg), FPS (30 por defecto).
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FFMPEG = process.env.FFMPEG || "ffmpeg";
const FPS = Number(process.env.FPS || 30);
const PORT = 9377;
const stills = process.argv.includes("--fotos") ? process.argv[process.argv.indexOf("--fotos") + 1].split(",").map(Number) : null;

const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "pitch-"))}`,
  "--window-size=1920,1080", "--hide-scrollbars", "--force-device-scale-factor=1", "--no-first-run", "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error("Chrome no respondió");
}

const ws = new WebSocket(await target());
await new Promise((r) => (ws.onopen = r));
let id = 0;
const waiting = new Map();
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); }
};
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const n = ++id;
  waiting.set(n, (msg) => (msg.error ? reject(new Error(method + ": " + msg.error.message)) : resolve(msg.result)));
  ws.send(JSON.stringify({ id: n, method, params }));
});
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result.value;

await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: pathToFileURL(join(here, "index.html")).href + "?rec" });
for (let i = 0; i < 100 && !(await evaluate("window.ready === true")); i++) await sleep(100);
// Espera a que las fotos estén decodificadas para que ningún cuadro salga en blanco
await evaluate("Promise.all([...document.images].map((i) => i.decode().catch(() => {}))).then(() => true)");

async function frame(t, format) {
  await evaluate(`seek(${t})`);
  const shot = await send("Page.captureScreenshot", format === "png" ? { format: "png" } : { format: "jpeg", quality: 92 });
  return Buffer.from(shot.data, "base64");
}

async function video(from, to, file) {
  const ff = spawn(FFMPEG, ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", file], { stdio: ["pipe", "inherit", "inherit"] });
  const total = Math.round((to - from) * FPS);
  for (let n = 0; n < total; n++) {
    const jpg = await frame(from + n / FPS, "jpeg");
    if (!ff.stdin.write(jpg)) await new Promise((r) => ff.stdin.once("drain", r));
    if (n % (FPS * 10) === 0) console.log(`${file.split("/").pop()}: ${Math.round(n / FPS)} s de ${to - from}`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("close", r));
  console.log("Listo:", file);
}

try {
  if (stills) {
    mkdirSync(join(here, "fotos"), { recursive: true });
    for (const t of stills) writeFileSync(join(here, "fotos", `t${String(t).padStart(3, "0")}.png`), await frame(t, "png"));
    console.log("Listo:", stills.length, "imágenes en pitch/fotos");
  } else {
    await video(0, 180, join(here, "agroprecio_pitch.mp4"));
    await video(180, 195, join(here, "agroprecio_cierre.mp4"));
  }
} finally {
  ws.close();
  chrome.kill();
}
