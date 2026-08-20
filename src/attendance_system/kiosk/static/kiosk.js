const pill = document.getElementById("state-pill");
const headline = document.getElementById("headline");
const nameEl = document.getElementById("name");
const sidEl = document.getElementById("sid");
const programEl = document.getElementById("program");
const gestureEl = document.getElementById("gesture");
const nextEl = document.getElementById("next-step");
const metaEl = document.getElementById("meta");
const photo = document.getElementById("photo");
const fallback = document.getElementById("photo-fallback");
const demoBadge = document.getElementById("demo-badge");
const startBtn = document.getElementById("start-test");
const resetBtn = document.getElementById("reset-test");
const successBanner = document.getElementById("success-banner");
let lastPhotoKey = "";

const LABELS = {
  waiting: "Esperando",
  identified: "Identificado",
  unknown: "No identificado",
  multiple: "Varios rostros",
  dark: "Imagen oscura",
  no_gallery: "Sin galería",
  camera_error: "Cámara",
  challenge: "Reto",
  challenge_ok: "Prueba OK",
  challenge_fail: "Reto fallido",
  hold: "Listo",
  cooldown: "Espera",
};

function showPhoto(url, name) {
  if (!url) {
    lastPhotoKey = "";
    photo.removeAttribute("src");
    photo.classList.add("hidden");
    fallback.classList.remove("hidden");
    fallback.textContent = name ? name.trim().charAt(0).toUpperCase() : "?";
    return;
  }
  if (lastPhotoKey === url && photo.getAttribute("src")) {
    photo.classList.remove("hidden");
    fallback.classList.add("hidden");
    return;
  }
  lastPhotoKey = url;
  photo.onload = () => {
    photo.classList.remove("hidden");
    fallback.classList.add("hidden");
  };
  photo.onerror = () => {
    lastPhotoKey = "";
    photo.removeAttribute("src");
    photo.classList.add("hidden");
    fallback.classList.remove("hidden");
    fallback.textContent = name ? name.trim().charAt(0).toUpperCase() : "?";
  };
  photo.src = url;
}

async function postAction(path) {
  const response = await fetch(path, { method: "POST" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || "No se pudo completar la acción.";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  try {
    await postAction("/api/challenge/start");
  } catch (err) {
    nextEl.textContent = String(err.message || err);
    startBtn.disabled = false;
  }
});

resetBtn.addEventListener("click", async () => {
  resetBtn.disabled = true;
  try {
    await postAction("/api/challenge/reset");
  } catch (err) {
    nextEl.textContent = String(err.message || err);
  } finally {
    resetBtn.disabled = false;
  }
});

async function tick() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error("status " + response.status);
    const data = await response.json();
    const state = data.state || "waiting";
    const success = state === "challenge_ok" || data.scanner_paused;
    pill.className = "pill " + state;
    pill.textContent = LABELS[state] || state;
    headline.textContent = success ? "Su prueba fue exitosa." : (data.headline || "");
    nameEl.textContent = data.full_name || "—";
    sidEl.textContent = data.student_id ? "ID: " + data.student_id : "ID: —";
    const program = data.program && !String(data.program).startsWith("Pendiente") ? data.program : "";
    const group = data.group_name && data.group_name !== "N/A" ? data.group_name : "";
    const extra = [program, group].filter(Boolean).join(" · ");
    programEl.textContent = extra;
    programEl.classList.toggle("hidden", !extra);
    const inChallenge = state === "challenge";
    const shown = inChallenge && data.challenge_target != null
      ? data.challenge_target
      : (inChallenge ? data.gesture_number : null);
    gestureEl.textContent = shown != null ? String(shown) : "—";
    nextEl.textContent = data.next_step || "";
    successBanner.classList.toggle("hidden", !success);
    startBtn.disabled = !data.can_start_test;
    resetBtn.classList.toggle("hidden", !success);
    const challengeBits = [];
    if (data.challenge_step && data.challenge_total) {
      challengeBits.push("Reto " + data.challenge_step + "/" + data.challenge_total);
    }
    if (data.remaining_seconds != null && data.state === "challenge") {
      challengeBits.push(Math.ceil(data.remaining_seconds) + "s");
    }
    metaEl.textContent =
      "Rostros: " + data.faces +
      " · Manos: " + (data.hands ?? 0) +
      (data.gesture_number != null ? " · Leído: " + data.gesture_number : "") +
      (challengeBits.length ? " · " + challengeBits.join(" · ") : "") +
      " · Galería: " + data.gallery_size +
      " · FPS: " + data.fps +
      (data.score != null ? " · Similitud: " + data.score : "") +
      " · Umbral: " + data.threshold +
      (data.scanner_paused ? " · Escáner detenido" : "");
    demoBadge.classList.toggle("hidden", !data.demo_mode);
    showPhoto(data.photo_url, data.full_name);
  } catch (err) {
    headline.textContent = "Sin conexión con el kiosco";
    metaEl.textContent = String(err);
  }
}

tick();
setInterval(tick, 400);
