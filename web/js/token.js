export const WINDOW_MS = 25000;
const SALT = "escaner-asistente-aula";

export function windowIndex(now = Date.now()) {
  return Math.floor(now / WINDOW_MS);
}

export function remainingMs(now = Date.now()) {
  return WINDOW_MS - (now % WINDOW_MS);
}

async function sha256Hex(text) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function makeToken(classCode, index) {
  const hex = await sha256Hex(`${SALT}|${String(classCode).trim().toLowerCase()}|${index}`);
  return hex.slice(0, 12);
}

export async function currentToken(classCode, now = Date.now()) {
  return makeToken(classCode, windowIndex(now));
}

export async function tokenIsValid(classCode, token, now = Date.now()) {
  if (!token || !classCode) return false;
  const w = windowIndex(now);
  const current = await makeToken(classCode, w);
  const previous = await makeToken(classCode, w - 1);
  return token === current || token === previous;
}

export function studentUrl(origin, classCode, token) {
  const base = origin.endsWith("/") ? origin : `${origin}/`;
  const url = new URL("prueba.html", base);
  url.searchParams.set("c", String(classCode).trim());
  url.searchParams.set("t", token);
  return url.href;
}
