import {
  cardUrl,
  colombiaToday,
  fetchRoster,
  fetchSession,
  fetchSessions,
  formatColombiaClock,
  formatColombiaDate,
  formatColombiaTime,
  isDayArchived,
} from "./attendance.js";
import { daySheets, dayWorkbook, downloadWorkbook, shareWorkbook, universityWorkbook } from "./excel.js";
import { logoutProfessor, requireProfessor } from "./auth.js";
import { isQrRunning } from "./qr-session.js";

if (!requireProfessor()) throw new Error("login");

const DEFAULT_CODE = "aula1";
const input = document.getElementById("class-code");
const sessionSelect = document.getElementById("session-date");
const refreshBtn = document.getElementById("refresh");
const livePill = document.getElementById("live-pill");
const sessionMeta = document.getElementById("session-meta");
const statusEl = document.getElementById("status");
const statsEl = document.getElementById("stats");
const summaryEl = document.getElementById("summary");
const presentList = document.getElementById("present-list");
const missingList = document.getElementById("missing-list");
const presentEmpty = document.getElementById("present-empty");
const missingEmpty = document.getElementById("missing-empty");
const downloadDayBtn = document.getElementById("download-day");
const shareDayBtn = document.getElementById("share-day");
const downloadUniversityBtn = document.getElementById("download-university");
const previewBtn = document.getElementById("preview-day");
const previewPanel = document.getElementById("excel-preview");
const previewBody = document.getElementById("excel-preview-body");
const previewDownload = document.getElementById("preview-download");
const previewClose = document.getElementById("preview-close");
const zoom = document.getElementById("photo-zoom");
const zoomImg = document.getElementById("photo-zoom-img");
const zoomName = document.getElementById("photo-zoom-name");
const zoomClose = document.getElementById("photo-zoom-close");
const clockEl = document.getElementById("colombia-clock");
const qrLinks = document.querySelectorAll(".qr-nav");
const archiveBanner = document.getElementById("archive-banner");
const presentHeading = document.getElementById("present-heading");
const missingHeading = document.getElementById("missing-heading");

input.value = localStorage.getItem("classCode") || DEFAULT_CODE;

let currentSession = null;
let currentPresent = [];
let currentMissing = [];
let currentStudents = [];
let dayArchived = false;

function classCode() {
  return (input.value || DEFAULT_CODE).trim() || DEFAULT_CODE;
}

function sourceLabel(source) {
  if (source === "kiosk") return "kiosco";
  if (source === "web") return "celular";
  return source || "";
}

function renderPerson(student, extra) {
  const row = document.createElement("article");
  row.className = "person-row";
  const url = cardUrl(student);
  if (url) {
    const img = document.createElement("img");
    img.className = "person-photo zoomable";
    img.alt = student.full_name || "";
    img.src = url;
    img.title = "Toca para ver más grande";
    img.addEventListener("click", () => openZoom(url, student.full_name || ""));
    row.append(img);
  } else {
    const fallback = document.createElement("div");
    fallback.className = "person-photo fallback";
    fallback.textContent = (student.full_name || "?").slice(0, 1).toUpperCase();
    row.append(fallback);
  }
  const body = document.createElement("div");
  const name = document.createElement("p");
  name.className = "person-name";
  name.textContent = student.full_name || "Sin nombre";
  const meta = document.createElement("p");
  meta.className = "person-meta";
  meta.textContent = [student.student_id || student.id, extra].filter(Boolean).join(" · ");
  body.append(name, meta);
  row.append(body);
  return row;
}

function openZoom(url, name) {
  zoomImg.src = url;
  zoomName.textContent = name;
  zoom.classList.remove("hidden");
}

function closeZoom() {
  zoom.classList.add("hidden");
  zoomImg.src = "";
}

function renderPreview() {
  if (!currentSession) return;
  const sheets = daySheets(currentSession, currentPresent, currentMissing);
  previewBody.replaceChildren();
  for (const [title, rows] of sheets) {
    const heading = document.createElement("h3");
    heading.textContent = title;
    const table = document.createElement("table");
    table.className = "preview-table";
    rows.forEach((row, index) => {
      const tr = document.createElement("tr");
      for (const cell of row) {
        const el = document.createElement(index === 0 ? "th" : "td");
        el.textContent = cell;
        tr.append(el);
      }
      table.append(tr);
    });
    previewBody.append(heading, table);
  }
  previewPanel.classList.remove("hidden");
  previewPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function fillSessionSelect(sessions, selectedDate) {
  const today = colombiaToday();
  sessionSelect.replaceChildren();
  if (!sessions.length) {
    const option = document.createElement("option");
    option.value = today;
    option.textContent = formatColombiaDate(today) + " · sin QR aún";
    sessionSelect.append(option);
    return;
  }
  for (const session of sessions) {
    const option = document.createElement("option");
    option.value = session.session_date;
    option.textContent =
      formatColombiaDate(session.session_date) +
      " · " +
      formatColombiaTime(session.started_at) +
      (isDayArchived(session.session_date) ? " · archivado" : "");
    sessionSelect.append(option);
  }
  const wanted = selectedDate || today;
  sessionSelect.value = sessions.some((item) => item.session_date === wanted)
    ? wanted
    : sessions[0].session_date;
}

async function load() {
  const code = classCode();
  localStorage.setItem("classCode", code);
  livePill.textContent = "Actualizando";
  livePill.className = "pill";
  try {
    const sessions = await fetchSessions(code);
    fillSessionSelect(sessions, sessionSelect.value || colombiaToday());
    const day = sessionSelect.value || colombiaToday();
    currentSession = sessions.find((item) => item.session_date === day) || (await fetchSession(code, day));
    const roster = await fetchRoster(code, currentSession);
    currentPresent = roster.present;
    currentMissing = roster.missing;
    currentStudents = roster.students;
    dayArchived = Boolean(roster.archived);
    const livePresent = dayArchived ? 0 : currentPresent.length;
    const liveMissing = dayArchived ? 0 : currentMissing.length;
    const total = currentPresent.length + currentMissing.length;
    document.getElementById("count-present").textContent = String(livePresent);
    document.getElementById("count-missing").textContent = String(liveMissing);
    document.getElementById("count-total").textContent = String(currentStudents.length || total);
    statsEl.hidden = !roster.open;
    summaryEl.hidden = !roster.open;
    presentList.replaceChildren();
    missingList.replaceChildren();

    if (!currentSession) {
      downloadDayBtn.disabled = true;
      shareDayBtn.disabled = true;
      previewBtn.disabled = true;
      archiveBanner.classList.add("hidden");
      sessionMeta.textContent = "Hoy todavía no se activó el QR. Ábrelo para registrar fecha y hora de esta clase.";
      summaryEl.hidden = true;
      presentEmpty.hidden = false;
      missingEmpty.hidden = true;
      presentEmpty.textContent = "Activa el QR para abrir el listado de hoy.";
      statusEl.textContent = "Clase " + code + " · una vez por semana.";
      livePill.textContent = "Sin clase";
      livePill.className = "pill";
      return;
    }

    sessionMeta.textContent =
      formatColombiaDate(currentSession.session_date) +
      " · QR activado a las " +
      formatColombiaTime(currentSession.started_at);
    presentHeading.textContent = dayArchived ? "Archivo · presentes" : "Presentes";
    missingHeading.textContent = dayArchived ? "Archivo · no asistieron" : "No asistieron";
    if (dayArchived) {
      archiveBanner.classList.remove("hidden");
      archiveBanner.textContent =
        "En curso: 0 presentes. Día archivado a las 12:00 p. m. hora Colombia · " +
        currentPresent.length +
        " fueron y " +
        currentMissing.length +
        " faltaron.";
      summaryEl.textContent = "El listado de abajo es el archivo de la mañana. Ya no entra nadie más hoy.";
      livePill.textContent = "Archivado";
      livePill.className = "pill";
    } else {
      archiveBanner.classList.add("hidden");
      if (total) {
        summaryEl.textContent =
          `${currentPresent.length} de ${total} fueron. Faltaron ${currentMissing.length}.`;
      } else {
        summaryEl.textContent = "La clase está abierta. Aún nadie ha pasado la prueba.";
      }
      livePill.textContent = "En vivo";
      livePill.className = "pill ok";
    }
    presentEmpty.hidden = currentPresent.length > 0;
    missingEmpty.hidden = currentMissing.length > 0;
    if (!total) {
      presentEmpty.textContent = "Aún nadie ha pasado la prueba.";
      missingEmpty.hidden = true;
    } else {
      presentEmpty.textContent = "Aún nadie ha pasado la prueba.";
      missingEmpty.textContent = "Nadie faltó.";
    }
    for (const student of currentPresent) {
      const extra = [formatColombiaTime(student.passed_at), sourceLabel(student.source)]
        .filter(Boolean)
        .join(" · ");
      presentList.append(renderPerson(student, extra));
    }
    for (const student of currentMissing) {
      const extra = [student.program, student.group_name].filter(Boolean).join(" · ");
      missingList.append(renderPerson(student, extra));
    }
    downloadDayBtn.disabled = false;
    shareDayBtn.disabled = false;
    previewBtn.disabled = false;
    statusEl.textContent = dayArchived
      ? "Clase " + code + " · archivada a las 12:00 p. m. hora Colombia."
      : "Clase " + code + " · se actualiza sola cada 3 segundos.";
    if (!previewPanel.classList.contains("hidden")) renderPreview();
  } catch (err) {
    livePill.textContent = "Sin conexión";
    livePill.className = "pill bad";
    sessionMeta.textContent = "";
    statusEl.textContent = err && err.message ? err.message : "No se pudo cargar el listado.";
  }
}

function safeDownload(factory) {
  try {
    downloadWorkbook(factory());
    statusEl.textContent = "Excel descargado.";
  } catch (err) {
    statusEl.textContent = "No se pudo descargar el Excel. Recarga la página e inténtalo otra vez.";
    console.error(err);
  }
}

downloadDayBtn.addEventListener("click", () => {
  if (!currentSession) return;
  safeDownload(() => dayWorkbook(currentSession, currentPresent, currentMissing));
});

shareDayBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  try {
    const file = dayWorkbook(currentSession, currentPresent, currentMissing);
    const shared = await shareWorkbook(file, "Asistencia " + currentSession.session_date);
    if (!shared) statusEl.textContent = "Este aparato no comparte archivos. Se descargó el Excel.";
  } catch (err) {
    statusEl.textContent = "No se pudo compartir el Excel. Recarga la página e inténtalo otra vez.";
    console.error(err);
  }
});

downloadUniversityBtn.addEventListener("click", () => {
  safeDownload(() => universityWorkbook(currentStudents));
});

previewBtn.addEventListener("click", renderPreview);
previewDownload.addEventListener("click", () => {
  if (!currentSession) return;
  safeDownload(() => dayWorkbook(currentSession, currentPresent, currentMissing));
});
previewClose.addEventListener("click", () => previewPanel.classList.add("hidden"));
zoomClose.addEventListener("click", closeZoom);
zoom.addEventListener("click", (event) => {
  if (event.target === zoom) closeZoom();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeZoom();
});

input.addEventListener("change", () => {
  sessionSelect.replaceChildren();
  load();
});
sessionSelect.addEventListener("change", load);
refreshBtn.addEventListener("click", load);
function refreshQrLink() {
  const label = isQrRunning() ? "Volver al QR en curso" : "Activar QR";
  qrLinks.forEach((el) => {
    el.textContent = label;
  });
}

function tickClock() {
  if (clockEl) clockEl.textContent = "Hora Colombia: " + formatColombiaClock();
  refreshQrLink();
  const closed = currentSession && isDayArchived(currentSession.session_date);
  if (closed && !dayArchived) load();
}
tickClock();
load();
setInterval(load, 3000);
setInterval(tickClock, 1000);
document.getElementById("logout")?.addEventListener("click", () => logoutProfessor());
