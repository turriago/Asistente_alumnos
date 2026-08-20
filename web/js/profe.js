import { logoutProfessor, requireProfessor } from "./auth.js";
import QRCode from "https://cdn.jsdelivr.net/npm/qrcode@1.5.4/+esm";
import { currentToken, remainingMs, studentUrl, windowIndex } from "./token.js";
import {
  colombiaToday,
  ensureSession,
  formatColombiaClock,
  formatColombiaDate,
  formatColombiaTime,
  isDayArchived,
  noonMs,
} from "./attendance.js";

if (!requireProfessor()) throw new Error("login");

const input = document.getElementById("class-code");
const publicBase = document.getElementById("public-base");
const minutesInput = document.getElementById("qr-minutes");
const canvas = document.getElementById("qr");
const ttl = document.getElementById("ttl");
const link = document.getElementById("link");
const warn = document.getElementById("warn");
const sessionMeta = document.getElementById("session-meta");
const statePill = document.getElementById("state-pill");
const activateBtn = document.getElementById("activate-qr");
const qrLive = document.getElementById("qr-live");
const qrBox = document.getElementById("qr-box");
const countdownEl = document.getElementById("qr-countdown");
const activatedAtEl = document.getElementById("activated-at");
const expiredNote = document.getElementById("expired-note");
const clockEl = document.getElementById("colombia-clock");
const DEFAULT_CODE = "aula1";

input.value = localStorage.getItem("classCode") || DEFAULT_CODE;
publicBase.value = localStorage.getItem("publicBase") || "";
minutesInput.value = localStorage.getItem("qrMinutes") || "20";
if (publicBase.value.startsWith("http://") && !/127\.0\.0\.1|localhost/i.test(publicBase.value)) {
  publicBase.value = "";
  localStorage.removeItem("publicBase");
}

let lastWindow = -1;
let lastCode = "";
let lastBase = "";
let lanBase = "";
let session = null;
let active = false;
let expiresAt = 0;
let activatedAt = null;

function isLoopback(host) {
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]";
}

function pageBase() {
  return new URL(".", window.location.href).href;
}

function studentBase() {
  const typed = publicBase.value.trim();
  if (typed) return typed.endsWith("/") ? typed : `${typed}/`;
  if (lanBase) return lanBase;
  return pageBase();
}

function minutes() {
  const value = Number(minutesInput.value);
  if (!Number.isFinite(value) || value < 1) return 20;
  return Math.min(180, Math.round(value));
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function remainLabel(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return `${h}:${pad(m)}:${pad(s)}`;
  return `${m}:${pad(s)}`;
}

function showTimes() {
  if (activatedAt) {
    activatedAtEl.textContent =
      "Activado exactamente a las " + formatColombiaTime(activatedAt.toISOString());
  }
  if (session) {
    sessionMeta.textContent =
      formatColombiaDate(session.session_date) +
      " · clase abierta a las " +
      formatColombiaTime(session.started_at);
  }
}

function deactivate(reason) {
  active = false;
  qrBox.classList.add("expired");
  expiredNote.classList.remove("hidden");
  expiredNote.textContent = reason || "El tiempo se acabó. El QR ya no sirve. Actívalo otra vez si quieres más minutos.";
  countdownEl.textContent = "Tiempo agotado · 0:00";
  statePill.textContent = "QR cerrado";
  statePill.className = "pill bad";
  activateBtn.disabled = false;
  activateBtn.textContent = "Activar QR otra vez";
  link.textContent = "El QR ya no admite nuevos estudiantes.";
}

async function activateToday() {
  const code = (input.value || DEFAULT_CODE).trim() || DEFAULT_CODE;
  try {
    session = await ensureSession(code);
    showTimes();
    return true;
  } catch {
    session = null;
    statePill.textContent = "Sin sesión";
    statePill.className = "pill bad";
    sessionMeta.textContent = "No se pudo activar la clase de hoy.";
    return false;
  }
}

async function detectLan() {
  if (!isLoopback(window.location.hostname)) return;
  try {
    const response = await fetch("lan.json", { cache: "no-store" });
    if (!response.ok) return;
    warn.classList.remove("hidden");
    warn.textContent =
      "El celular ya puede abrir la página por WiFi, pero la cámara del teléfono NO funciona en http. Sube la carpeta web a Netlify (https) y pega esa URL abajo. En el PC sí funciona porque 127.0.0.1 cuenta como seguro.";
    if (!publicBase.value) publicBase.placeholder = "https://tu-sitio.netlify.app/";
  } catch {
    warn.classList.remove("hidden");
    warn.textContent =
      "El celular no puede abrir 127.0.0.1. Escribe abajo la URL de Netlify, o la IP de este PC en la WiFi.";
  }
}

async function render() {
  if (clockEl) clockEl.textContent = "Hora Colombia: " + formatColombiaClock();
  if (!active) return;
  if (isDayArchived(session && session.session_date)) {
    deactivate("Ya son las 12:00 p. m. hora Colombia. El día se archivó y los presentes del en curso volvieron a 0.");
    return;
  }
  if (expiresAt && Date.now() >= expiresAt) {
    deactivate();
    return;
  }
  const code = (input.value || DEFAULT_CODE).trim() || DEFAULT_CODE;
  localStorage.setItem("classCode", code);
  localStorage.setItem("publicBase", publicBase.value.trim());
  localStorage.setItem("qrMinutes", String(minutes()));
  countdownEl.textContent = "El QR se apaga en " + remainLabel(expiresAt - Date.now());
  if (!session || session.class_code !== code) {
    const ok = await activateToday();
    if (!ok) return;
  }
  const w = windowIndex();
  const base = studentBase();
  ttl.textContent = String(Math.ceil(remainingMs() / 1000));
  if (w === lastWindow && code === lastCode && base === lastBase) return;
  lastWindow = w;
  lastCode = code;
  lastBase = base;
  const token = await currentToken(code);
  const url = studentUrl(base, code, token, session && session.session_date, expiresAt);
  await QRCode.toCanvas(canvas, url, { width: 320, margin: 1 });
  link.textContent = url;
}

activateBtn.addEventListener("click", async () => {
  activateBtn.disabled = true;
  activateBtn.textContent = "Activando…";
  if (isDayArchived(colombiaToday())) {
    activateBtn.disabled = false;
    activateBtn.textContent = "Activar QR";
    statePill.textContent = "Día archivado";
    statePill.className = "pill bad";
    sessionMeta.textContent = "Ya pasaron las 12:00 p. m. hora Colombia. La asistencia de la mañana quedó archivada.";
    return;
  }
  const ok = await activateToday();
  if (!ok) {
    activateBtn.disabled = false;
    activateBtn.textContent = "Activar QR";
    return;
  }
  activatedAt = new Date();
  expiresAt = Math.min(Date.now() + minutes() * 60 * 1000, noonMs(colombiaToday()));
  active = true;
  qrLive.classList.remove("hidden");
  qrBox.classList.remove("expired");
  expiredNote.classList.add("hidden");
  statePill.textContent = "QR activo";
  statePill.className = "pill ok";
  activateBtn.textContent = "QR activo";
  showTimes();
  lastWindow = -1;
  await render();
});

minutesInput.addEventListener("change", () => {
  localStorage.setItem("qrMinutes", String(minutes()));
});
input.addEventListener("input", () => {
  lastWindow = -1;
  session = null;
  if (active) render();
});
publicBase.addEventListener("input", () => {
  lastWindow = -1;
  if (active) render();
});

await detectLan();
setInterval(render, 250);
document.getElementById("logout")?.addEventListener("click", () => logoutProfessor());
