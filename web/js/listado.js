import {
  cardUrl,
  colombiaToday,
  fetchRoster,
  fetchSession,
  fetchSessions,
  formatColombiaDate,
  formatColombiaTime,
} from "./attendance.js";
import { dayWorkbook, downloadWorkbook, shareWorkbook, universityWorkbook } from "./excel.js";

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

input.value = localStorage.getItem("classCode") || DEFAULT_CODE;

let currentSession = null;
let currentPresent = [];
let currentMissing = [];
let currentStudents = [];

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
    img.className = "person-photo";
    img.alt = "";
    img.src = url;
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
      formatColombiaDate(session.session_date) + " · " + formatColombiaTime(session.started_at);
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
    const total = currentPresent.length + currentMissing.length;
    document.getElementById("count-present").textContent = String(currentPresent.length);
    document.getElementById("count-missing").textContent = String(currentMissing.length);
    document.getElementById("count-total").textContent = String(total);
    statsEl.hidden = !roster.open || total === 0;
    summaryEl.hidden = !roster.open;
    presentList.replaceChildren();
    missingList.replaceChildren();

    if (!currentSession) {
      downloadDayBtn.disabled = true;
      shareDayBtn.disabled = true;
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
    if (total) {
      summaryEl.textContent =
        `${currentPresent.length} de ${total} fueron. Faltaron ${currentMissing.length}.`;
    } else {
      summaryEl.textContent = "La clase está abierta. Aún nadie ha pasado la prueba.";
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
    statusEl.textContent = "Clase " + code + " · se actualiza sola cada 3 segundos.";
    livePill.textContent = "En vivo";
    livePill.className = "pill ok";
  } catch (err) {
    livePill.textContent = "Sin conexión";
    livePill.className = "pill bad";
    sessionMeta.textContent = "";
    statusEl.textContent = err && err.message ? err.message : "No se pudo cargar el listado.";
  }
}

downloadDayBtn.addEventListener("click", () => {
  if (!currentSession) return;
  downloadWorkbook(dayWorkbook(currentSession, currentPresent, currentMissing));
});

shareDayBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const file = dayWorkbook(currentSession, currentPresent, currentMissing);
  try {
    const shared = await shareWorkbook(file, "Asistencia " + currentSession.session_date);
    if (!shared) statusEl.textContent = "Este aparato no comparte archivos. Se descargó el Excel.";
  } catch {
    downloadWorkbook(file);
  }
});

downloadUniversityBtn.addEventListener("click", () => {
  downloadWorkbook(universityWorkbook(currentStudents));
});

input.addEventListener("change", () => {
  sessionSelect.replaceChildren();
  load();
});
sessionSelect.addEventListener("change", load);
refreshBtn.addEventListener("click", load);
load();
setInterval(load, 3000);
