import { tokenIsValid } from "./token.js";
import { NumberSmoother, readNumber } from "./fingers.js";
import { Challenge } from "./challenge.js";
import { createTrackers } from "./vision.js";
import { fetchGallery, prepareGallery } from "./gallery.js?v=11";
import { buildDescriptors, loadFaceApi, matchVideo } from "./recognize.js?v=11";
import { recordPass, colombiaToday, isDayArchived } from "./attendance.js";

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
const photo = document.getElementById("photo");
const fallback = document.getElementById("photo-fallback");
const nameEl = document.getElementById("name");
const sidEl = document.getElementById("sid");
const programEl = document.getElementById("program");
const card = document.getElementById("card");
const ctx = overlay.getContext("2d", { alpha: true });

const params = new URLSearchParams(location.search);
const classCode = params.get("c") || "";
const token = params.get("t") || "";
const sessionDate = params.get("d") || "";
const expiresAt = Number(params.get("exp") || "0") * 1000;
const demo = params.get("demo") === "1";
const challenge = new Challenge();
const smoother = new NumberSmoother(400);

let facesTracker = null;
let handsTracker = null;
let lastSnap = 0;
let lastVideoTime = -1;
let hasFace = false;
let running = true;
let gallery = [];
let matched = null;
let labeledFaces = [];
let recognizeTimer = 0;
let missedMatches = 0;
let trackersPromise = null;
let faceApiPromise = null;
let attendanceSent = false;

function doneKey() {
  return "asistencia-ok:" + (classCode || "demo") + ":" + (token || "demo") + ":" + (sessionDate || "");
}

function alreadyDone() {
  try {
    return sessionStorage.getItem(doneKey()) === "1";
  } catch {
    return false;
  }
}

function markDone() {
  try {
    sessionStorage.setItem(doneKey(), "1");
  } catch {
    /* modo privado */
  }
}

function stopCamera() {
  running = false;
  if (recognizeTimer) {
    clearInterval(recognizeTimer);
    recognizeTimer = 0;
  }
  const stream = video.srcObject;
  if (stream && typeof stream.getTracks === "function") {
    for (const track of stream.getTracks()) track.stop();
  }
  video.srcObject = null;
  video.pause();
  if (ctx && overlay.width) ctx.clearRect(0, 0, overlay.width, overlay.height);
}

function showThanks() {
  stopCamera();
  markDone();
  document.body.classList.add("thanks-lock");
  const thanks = document.getElementById("thanks");
  thanks.classList.remove("hidden");
  camBtn.classList.add("hidden");
  startBtn.classList.add("hidden");
  againBtn.classList.add("hidden");
}

function preloadModels() {
  if (!trackersPromise) trackersPromise = createTrackers();
  if (!faceApiPromise) faceApiPromise = loadFaceApi();
}

function showCard(hasPerson) {
  if (!hasPerson) {
    matched = null;
    photo.classList.add("hidden");
    fallback.classList.remove("hidden");
    fallback.textContent = "?";
    nameEl.textContent = "—";
    sidEl.textContent = "ID: —";
    programEl.textContent = "";
    card.classList.remove("identified");
    return;
  }
  if (matched) {
    nameEl.textContent = matched.name;
    sidEl.textContent = "ID: " + matched.id;
    programEl.textContent = [matched.program, matched.group].filter(Boolean).join(" · ");
    photo.src = matched.photo;
    photo.classList.remove("hidden");
    fallback.classList.add("hidden");
    card.classList.add("identified");
    return;
  }
  nameEl.textContent = gallery.length ? "No identificado" : "Estudiante";
  sidEl.textContent = gallery.length ? "ID: —" : "ID: sesión web";
  programEl.textContent = gallery.length ? "Las fotos locales aún no coinciden" : "Prueba desde el celular";
  card.classList.add("identified");
}

function snapFace(box) {
  const now = performance.now();
  if (now - lastSnap < 800 || !video.videoWidth) return;
  lastSnap = now;
  const snap = document.createElement("canvas");
  const size = 128;
  snap.width = size;
  snap.height = size;
  const sctx = snap.getContext("2d");
  let sx = 0;
  let sy = 0;
  let sw = video.videoWidth;
  let sh = video.videoHeight;
  if (box) {
    const pad = Math.max(box.width, box.height) * 0.25;
    sx = Math.max(0, box.originX - pad);
    sy = Math.max(0, box.originY - pad);
    sw = Math.min(video.videoWidth - sx, box.width + pad * 2);
    sh = Math.min(video.videoHeight - sy, box.height + pad * 2);
  }
  sctx.drawImage(video, sx, sy, sw, sh, 0, 0, size, size);
  photo.src = snap.toDataURL("image/jpeg", 0.85);
  photo.classList.remove("hidden");
  fallback.classList.add("hidden");
}

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
  if (expiresAt && Date.now() > expiresAt) {
    setPill("QR cerrado", "bad");
    headline.textContent = "El tiempo del QR ya se acabó";
    next.textContent = "La profesora cerró el código. Pide que active el QR otra vez.";
    return false;
  }
  if (isDayArchived(sessionDate || colombiaToday())) {
    setPill("Día archivado", "bad");
    headline.textContent = "Ya se archivó la clase de hoy";
    next.textContent = "Después de las 12:00 p. m. hora Colombia no entra más asistencia.";
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
  const tries = [
    { audio: false, video: { facingMode: "user" } },
    { audio: false, video: true },
    { audio: false, video: { width: 640, height: 480 } },
  ];
  let lastError = null;
  let stream = null;
  for (const constraints of tries) {
    try {
      stream = await navigator.mediaDevices.getUserMedia(constraints);
      break;
    } catch (err) {
      lastError = err;
    }
  }
  if (!stream) throw lastError || new Error("camara");
  video.srcObject = stream;
  await new Promise((resolve, reject) => {
    video.onloadedmetadata = () => resolve();
    video.onerror = () => reject(new Error("video"));
    setTimeout(() => resolve(), 2000);
  });
  await video.play();
  placeholder.classList.add("hidden");
}

function cameraHelp(err) {
  const name = err && err.name;
  if (name === "NotReadableError" || name === "TrackStartError") {
    return "La webcam está ocupada. Cierra el kiosco del PC (la ventana negra de python) y la app Cámara de Windows. Luego pulsa Permitir cámara otra vez.";
  }
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return "El navegador bloqueó la cámara. En la barra de dirección, permite la cámara para este sitio.";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "No se encontró ninguna cámara en este PC.";
  }
  return "Pulsa Permitir cámara y acepta el permiso. En el PC cierra el kiosco si sigue fallando.";
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
    if (!attendanceSent && matched && matched.id) {
      attendanceSent = true;
      recordPass({
        id: matched.id,
        name: matched.name,
        classCode: classCode || "aula1",
        sessionDate,
        source: "web",
      }).catch(() => {
        attendanceSent = false;
      });
    }
    showThanks();
    return;
  }
  if (view.state === "failed") {
    setPill("Reto fallido", "bad");
    headline.textContent = "Reto fallido";
    next.textContent = view.message;
    startBtn.disabled = true;
    againBtn.classList.remove("hidden");
  } else if (view.state === "challenge") {
    setPill("Reto");
    headline.textContent = view.target != null ? `Muestra ${view.target}` : "Baja las manos";
    next.textContent = view.message;
    numberEl.textContent = view.target != null ? String(view.target) : String(gesture ?? "—");
    numberEl.classList.remove("hidden");
    startBtn.disabled = true;
  } else {
    const identified = Boolean(hasFace && matched);
    const ready = gallery.length ? identified : hasFace;
    setPill(
      identified ? "Identificado" : (hasFace && gallery.length ? "No identificado" : (hasFace ? "Identificado" : "Esperando")),
      ready ? "ok" : (hasFace ? "bad" : "waiting"),
    );
    headline.textContent = ready
      ? "Estudiante detectado"
      : (hasFace ? "Estudiante no identificado" : "Esperando un rostro");
    next.textContent = ready
      ? "Pulsa Iniciar prueba para los 3 números aleatorios."
      : (hasFace
        ? "Mira de frente a la cámara."
        : "Pulsa Permitir cámara y ponte frente al teléfono.");
    numberEl.textContent = gesture != null ? String(gesture) : "—";
    startBtn.disabled = !ready;
    showCard(hasFace);
    numberEl.classList.toggle("hidden", gesture == null);
    if (hasFace && !matched) snapFace(detections[0] && detections[0].boundingBox);
  }
  requestAnimationFrame(tick);
}

startBtn.addEventListener("click", () => {
  if (alreadyDone() || document.body.classList.contains("thanks-lock")) return;
  if (!hasFace) return;
  if (gallery.length && !matched) return;
  challenge.start(performance.now());
  smoother.reset();
  againBtn.classList.add("hidden");
});

camBtn.addEventListener("click", () => {
  startCamera();
});

againBtn.addEventListener("click", () => {
  if (alreadyDone() || document.body.classList.contains("thanks-lock")) return;
  challenge.reset();
  smoother.reset();
  attendanceSent = false;
  success.classList.add("hidden");
  startBtn.disabled = !hasFace;
  againBtn.classList.add("hidden");
  showCard(hasFace);
  if (video.paused) video.play();
  running = true;
  lastVideoTime = -1;
  requestAnimationFrame(tick);
});

function startRecognizer() {
  if (recognizeTimer) clearInterval(recognizeTimer);
  recognizeTimer = window.setInterval(async () => {
    if (!running || !labeledFaces.length || video.readyState < 2) return;
    try {
      const hit = await matchVideo(video, labeledFaces);
      if (hit) {
        matched = hit;
        missedMatches = 0;
      } else if (!hasFace) {
        matched = null;
        missedMatches = 0;
      } else {
        missedMatches += 1;
        if (missedMatches >= 6) matched = null;
      }
    } catch {
      /* un frame falló */
    }
  }, 450);
}

async function startCamera() {
  if (alreadyDone()) {
    showThanks();
    return;
  }
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
    next.textContent = "Abriendo cámara…";
    await openCamera();
    camBtn.classList.add("hidden");
    placeholder.classList.add("hidden");
    setPill("Cámara", "ok");
    headline.textContent = "Cámara lista";
    next.textContent = "Cargando detección…";
    preloadModels();
    const trackers = await trackersPromise;
    facesTracker = trackers.faces;
    handsTracker = trackers.hands;
    requestAnimationFrame(tick);
    if (!gallery.length) {
      gallery = await prepareGallery(await fetchGallery(classCode || "aula1"));
    }
    next.textContent = "Cargando reconocimiento…";
    try {
      await faceApiPromise;
      labeledFaces = await buildDescriptors(gallery);
      startRecognizer();
    } catch (err) {
      console.error(err);
      labeledFaces = [];
    }
    setPill(gallery.length ? "Listo" : "Sin fotos", gallery.length ? "ok" : "waiting");
    headline.textContent = "Esperando un rostro";
    next.textContent = "Mira de frente a la cámara.";
  } catch (err) {
    camBtn.disabled = false;
    setPill("Cámara", "bad");
    headline.textContent = "No se pudo abrir la cámara";
    next.textContent = cameraHelp(err);
    console.error(err);
  }
}

async function main() {
  if (alreadyDone()) {
    showThanks();
    return;
  }
  if (!window.isSecureContext) return;
  const valid = await ensureToken();
  if (!valid) return;
  setPill("Listo");
  next.textContent = "Pulsa Permitir cámara. El navegador lo pide al tocar el botón.";
  const galleryCode = classCode || "aula1";
  gallery = await prepareGallery(await fetchGallery(galleryCode));
  preloadModels();
}

main();
