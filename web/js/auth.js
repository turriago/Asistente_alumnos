import { clearQrLive } from "./qr-session.js";

const SESSION_KEY = "profe-session";

export function isProfessor() {
  try {
    return sessionStorage.getItem(SESSION_KEY) === "kelly";
  } catch {
    return false;
  }
}

export function loginProfessor(user, password) {
  const name = String(user || "").trim().toLowerCase();
  const pass = String(password || "");
  if (name !== "kelly" || pass !== "0000") return false;
  try {
    sessionStorage.setItem(SESSION_KEY, "kelly");
  } catch {
    return false;
  }
  return true;
}

export function logoutProfessor() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* modo privado */
  }
  clearQrLive();
  location.replace("login.html");
}

export function requireProfessor() {
  if (isProfessor()) return true;
  const page = location.pathname.split("/").pop() || "listado.html";
  location.replace("login.html?next=" + encodeURIComponent(page + location.search));
  return false;
}
