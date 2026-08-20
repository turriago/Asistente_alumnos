import QRCode from "https://cdn.jsdelivr.net/npm/qrcode@1.5.4/+esm";
import { currentToken, remainingMs, studentUrl, windowIndex } from "./token.js";
import { ensureSession, formatColombiaDate, formatColombiaTime } from "./attendance.js";

const input = document.getElementById("class-code");
const publicBase = document.getElementById("public-base");
const canvas = document.getElementById("qr");
const ttl = document.getElementById("ttl");
const link = document.getElementById("link");
const warn = document.getElementById("warn");
const sessionMeta = document.getElementById("session-meta");
const statePill = document.getElementById("state-pill");
const activateBtn = document.getElementById("activate-qr");
const qrLive = document.getElementById("qr-live");
const DEFAULT_CODE = "aula1";

input.value = localStorage.getItem("classCode") || DEFAULT_CODE;
publicBase.value = localStorage.getItem("publicBase") || "";
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

function showSession() {
  if (!session) {
    sessionMeta.textContent = "No se pudo guardar la fecha de hoy. Revisa la conexión.";
    return;
  }
  sessionMeta.textContent =
    formatColombiaDate(session.session_date) +
    " · QR activado a las " +
    formatColombiaTime(session.started_at);
}

async function activateToday() {
  const code = (input.value || DEFAULT_CODE).trim() || DEFAULT_CODE;
  try {
    session = await ensureSession(code);
    statePill.textContent = "QR activo";
    statePill.className = "pill ok";
    showSession();
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
  if (!active) return;
  const code = (input.value || DEFAULT_CODE).trim() || DEFAULT_CODE;
  localStorage.setItem("classCode", code);
  localStorage.setItem("publicBase", publicBase.value.trim());
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
  const url = studentUrl(base, code, token, session && session.session_date);
  await QRCode.toCanvas(canvas, url, { width: 320, margin: 1 });
  link.textContent = url;
}

activateBtn.addEventListener("click", async () => {
  activateBtn.disabled = true;
  activateBtn.textContent = "Activando…";
  const ok = await activateToday();
  if (!ok) {
    activateBtn.disabled = false;
    activateBtn.textContent = "Activar QR";
    return;
  }
  active = true;
  qrLive.classList.remove("hidden");
  activateBtn.textContent = "QR activo";
  lastWindow = -1;
  await render();
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
