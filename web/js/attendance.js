import { SUPABASE_ANON_KEY, SUPABASE_URL } from "./supabase-public.js";

const BOGOTA = "America/Bogota";

function restUrl(path, params) {
  const url = new URL(String(SUPABASE_URL || "").replace(/\/$/, "") + "/rest/v1/" + path);
  for (const [key, value] of Object.entries(params || {})) {
    url.searchParams.set(key, value);
  }
  return url;
}

function headers(prefer) {
  const key = String(SUPABASE_ANON_KEY || "");
  const out = { apikey: key, Authorization: "Bearer " + key };
  if (prefer) out.Prefer = prefer;
  return out;
}

export function colombiaToday(now = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: BOGOTA,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export function formatColombiaClock(now = new Date()) {
  return now.toLocaleTimeString("es-CO", {
    timeZone: BOGOTA,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatColombiaTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("es-CO", {
    timeZone: BOGOTA,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatColombiaDate(isoOrDay) {
  if (!isoOrDay) return "";
  const date = isoOrDay.length <= 10 ? new Date(isoOrDay + "T12:00:00-05:00") : new Date(isoOrDay);
  if (Number.isNaN(date.getTime())) return String(isoOrDay);
  return date.toLocaleDateString("es-CO", {
    timeZone: BOGOTA,
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function splitRoster(students, passes) {
  const byId = new Map();
  for (const row of passes || []) {
    byId.set(String(row.student_id || row.id || ""), row);
  }
  const present = [];
  const missing = [];
  for (const student of students || []) {
    const studentId = String(student.student_id || student.id || "");
    const stamp = byId.get(studentId);
    if (stamp) {
      present.push({ ...student, passed_at: stamp.passed_at, source: stamp.source });
    } else {
      missing.push(student);
    }
  }
  present.sort((a, b) => String(a.passed_at || "").localeCompare(String(b.passed_at || "")));
  missing.sort((a, b) =>
    String(a.full_name || a.name || "").localeCompare(String(b.full_name || b.name || ""), "es", {
      sensitivity: "base",
    }),
  );
  return { present, missing };
}

async function readJson(response, errorMessage) {
  if (!response.ok) throw new Error(errorMessage);
  return response.json();
}

export async function fetchSession(classCode, sessionDate) {
  const url = restUrl("class_sessions", {
    select: "id,class_code,session_date,started_at",
    class_code: "eq." + (classCode || "aula1"),
    session_date: "eq." + sessionDate,
    limit: "1",
  });
  const rows = await readJson(
    await fetch(url, { cache: "no-store", headers: headers() }),
    "No se pudo leer la sesión de clase.",
  );
  return rows && rows[0] ? rows[0] : null;
}

export async function ensureSession(classCode, sessionDate) {
  const code = classCode || "aula1";
  const day = sessionDate || colombiaToday();
  const existing = await fetchSession(code, day);
  if (existing) return existing;
  const response = await fetch(restUrl("class_sessions"), {
    method: "POST",
    cache: "no-store",
    headers: {
      ...headers("return=representation,resolution=ignore-duplicates"),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      class_code: code,
      session_date: day,
      started_at: new Date().toISOString(),
    }),
  });
  if (!response.ok) throw new Error("No se pudo activar la clase de hoy.");
  const created = await response.json();
  if (Array.isArray(created) && created[0]) return created[0];
  if (created && created.id) return created;
  return fetchSession(code, day);
}

export async function fetchSessions(classCode) {
  const url = restUrl("class_sessions", {
    select: "id,class_code,session_date,started_at",
    class_code: "eq." + (classCode || "aula1"),
    order: "session_date.desc",
  });
  const rows = await readJson(
    await fetch(url, { cache: "no-store", headers: headers() }),
    "No se pudieron leer las clases anteriores.",
  );
  return rows || [];
}

export async function recordPass({ id, name, classCode, source, sessionDate }) {
  const studentId = String(id || "").trim();
  if (!studentId || !SUPABASE_URL || !SUPABASE_ANON_KEY) return false;
  const day = sessionDate || colombiaToday();
  const session = await ensureSession(classCode || "aula1", day);
  if (!session) return false;
  const response = await fetch(restUrl("attendance"), {
    method: "POST",
    cache: "no-store",
    headers: {
      ...headers("resolution=ignore-duplicates,return=minimal"),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      class_code: session.class_code || classCode || "aula1",
      session_id: session.id,
      session_date: session.session_date,
      student_id: studentId,
      full_name: String(name || ""),
      source: source || "web",
    }),
  });
  return response.ok;
}

export async function fetchStudents() {
  const url = restUrl("students", {
    select: "student_id,full_name,program,group_name,student_media(kind,public_url,is_card)",
    order: "full_name.asc",
  });
  return readJson(
    await fetch(url, { cache: "no-store", headers: headers() }),
    "No se pudo leer la lista de estudiantes.",
  );
}

export async function fetchRoster(classCode, session) {
  const students = await fetchStudents();
  if (!session) return { present: [], missing: [], students: students || [], open: false };
  const passesUrl = restUrl("attendance", {
    session_id: "eq." + session.id,
    select: "student_id,full_name,source,passed_at",
    order: "passed_at.asc",
  });
  const passes = await readJson(
    await fetch(passesUrl, { cache: "no-store", headers: headers() }),
    "No se pudo leer la asistencia.",
  );
  const split = splitRoster(students || [], passes || []);
  return { ...split, students: students || [], open: true };
}

export function cardUrl(student) {
  const media = student.student_media || [];
  const images = media.filter((item) => item.kind === "card" || item.kind === "photo");
  const card = images.find((item) => item.is_card) || images[0];
  return card && card.public_url ? card.public_url : "";
}
