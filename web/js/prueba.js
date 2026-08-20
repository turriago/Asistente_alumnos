import { tokenIsValid } from "./token.js";
import { NumberSmoother, readNumber } from "./fingers.js";
import { Challenge } from "./challenge.js";
import { createTrackers } from "./vision.js";

const pill = document.getElementById("pill");
const headline = document.getElementById("headline");
const next = document.getElementById("next");
const numberEl = document.getElementById("number");
const startBtn = document.getElementById("start");
const camBtn = document.getElementById("cam-btn");
const againBtn = document.getElementById("again");
const success = document.getElementById("success");
const video = document.getElementById("cam");
const overlay = document.getElementById("overlay");
const placeholder = document.getElementById("cam-placeholder");
const ctx = overlay.getContext("2d", { alpha: true });

const params = new URLSearchParams(location.search);
const classCode = params.get("c") || "";
const token = params.get("t") || "";
const demo = params.get("demo") === "1";
const challenge = new Challenge();
const smoother = new NumberSmoother(400);

let facesTracker = null;
let handsTracker = null;
let lastVideoTime = -1;
let hasFace = false;
let running = true;

function setPill(text, kind) {
  pill.textContent = text;
  pill.className = "pill" + (kind ? " " + kind : "");
}

async function ensureToken() {
  if (demo) {
    setPill("Demo");
    next.textContent = "Modo prueba en este aparato. En clase se entra solo con el QR.";
    return true;
  }
  if (!classCode || !token) {
    setPill("Sin QR", "bad");
    headline.textContent = "Falta el código de la clase";
    next.textContent = "Pide a la profesora que te muestre el QR de esta sesión.";
    return false;
  }
  const ok = await tokenIsValid(classCode, token);
  if (!ok) {
    setPill("QR vencido", "bad");
    headline.textContent = "Este QR ya no sirve";
    next.textContent = "El código cambia cada 25 segundos. Vuelve a escanear el de la pizarra.";
    return false;
  }
  return true;
}

async function openCamera() {
  video.setAttribute("playsinline", "true");
  video.setAttribute("autoplay", "true");
  video.muted = true;
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: "user" },
  });
  video.srcObject = stream;
  await new Promise((resolve, reject) => {
    video.onloadedmetadata = () => resolve();
    video.onerror = () => reject(new Error("video"));
    setTimeout(() => resolve(), 2000);
  });
  await video.play();
  placeholder.classList.add("hidden");
}

function drawBoxes(detections, hands) {
  overlay.width = video.videoWidth;
  overlay.height = video.videoHeight;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.strokeStyle = "#3ee0a4";
  ctx.lineWidth = 4;
  for (const det of detections) {
    const box = det.boundingBox;
    if (!box) continue;
    ctx.strokeRect(box.originX, box.originY, box.width, box.height);
  }
  ctx.fillStyle = "#f0c14a";
  for (const hand of hands) {
    for (const p of hand) {
      ctx.beginPath();
      ctx.arc(p.x * overlay.width, p.y * overlay.height, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function tick() {
  if (!running || video.readyState < 2) {
    requestAnimationFrame(tick);
    return;
  }
  const now = performance.now();
  if (video.currentTime === lastVideoTime) {
    requestAnimationFrame(tick);
    return;
  }
  lastVideoTime = video.currentTime;
  const faceResult = facesTracker.detectForVideo(video, now);
  const handResult = handsTracker.detectForVideo(video, now);
  const detections = faceResult.detections || [];
  hasFace = detections.length > 0;
  const landmarks = (handResult.landmarks || []).slice(0, 2);
  drawBoxes(detections, landmarks);
  const reading = readNumber(landmarks, video.videoWidth, video.videoHeight);
  const gesture = smoother.update(reading.number, now);
  const view = challenge.observe(now, gesture);

  if (view.state === "success") {
    running = false;
    video.pause();
    setPill("Prueba OK", "ok");
    headline.textContent = "Su prueba fue exitosa.";
    next.textContent = view.message;
    numberEl.textContent = "✓";
    success.classList.remove("hidden");
    startBtn.disabled = true;
    againBtn.classList.remove("hidden");
    return;
  }
  if (view.state === "failed") {
    setPill("Falló", "bad");
    headline.textContent = "Reto fallido";
    next.textContent = view.message;
    startBtn.disabled = true;
    againBtn.classList.remove("hidden");
  } else if (view.state === "challenge") {
    setPill("Reto");
    headline.textContent = view.target != null ? `Muestra ${view.target}` : "Baja las manos";
    next.textContent = view.message;
    numberEl.textContent = view.target != null ? String(view.target) : String(gesture ?? "—");
    startBtn.disabled = true;
  } else {
    setPill(hasFace ? "Rostro listo" : "Esperando", hasFace ? "ok" : "");
    headline.textContent = hasFace ? "Rostro detectado" : "Pon la cara frente a la cámara";
    next.textContent = hasFace
      ? "Pulsa Iniciar prueba para los 3 números aleatorios."
      : "Ilumina tu cara. No hace falta acercarte al kiosco de la profesora.";
    numberEl.textContent = gesture != null ? String(gesture) : "—";
    startBtn.disabled = !hasFace;
  }
  requestAnimationFrame(tick);
}

startBtn.addEventListener("click", () => {
  if (!hasFace) return;
  challenge.start(performance.now());
  smoother.reset();
  againBtn.classList.add("hidden");
});

camBtn.addEventListener("click", () => {
  startCamera();
});

againBtn.addEventListener("click", () => {
  challenge.reset();
  smoother.reset();
  success.classList.add("hidden");
  startBtn.disabled = !hasFace;
  againBtn.classList.add("hidden");
  if (video.paused) video.play();
  running = true;
  lastVideoTime = -1;
  requestAnimationFrame(tick);
});

async function startCamera() {
  if (!window.isSecureContext) {
    setPill("Sin https", "bad");
    headline.textContent = "El celular bloquea la cámara";
    next.textContent =
      "Brave y Chrome en el teléfono no abren la cámara si la web no es https. Sube la carpeta web a Netlify y escanea ese QR.";
    return;
  }
  const valid = await ensureToken();
  if (!valid) return;
  camBtn.disabled = true;
  try {
    next.textContent = "Cargando cámara y modelos…";
    await openCamera();
    const trackers = await createTrackers();
    facesTracker = trackers.faces;
    handsTracker = trackers.hands;
    camBtn.classList.add("hidden");
    placeholder.classList.add("hidden");
    setPill("Listo", "ok");
    requestAnimationFrame(tick);
  } catch (err) {
    camBtn.disabled = false;
    setPill("Cámara", "bad");
    headline.textContent = "No se pudo abrir la cámara";
    next.textContent = "Pulsa Permitir cámara y acepta el permiso. Si la barra dice No seguro, hace falta https.";
    console.error(err);
  }
}

async function main() {
  if (!window.isSecureContext) return;
  const valid = await ensureToken();
  if (!valid) return;
  setPill("Listo");
  next.textContent = "Pulsa Permitir cámara. El navegador lo pide al tocar el botón.";
}

main();
