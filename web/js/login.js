import { isProfessor, loginProfessor } from "./auth.js";

const params = new URLSearchParams(location.search);
const requested = params.get("next") || "profe.html";
const next = /^[a-z0-9._-]+\.html(?:\?.*)?$/i.test(requested) ? requested : "profe.html";
const form = document.getElementById("login-form");
const error = document.getElementById("error");
const pill = document.getElementById("pill");

if (isProfessor()) {
  location.replace(next);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const user = document.getElementById("user").value;
  const password = document.getElementById("password").value;
  if (!loginProfessor(user, password)) {
    error.classList.remove("hidden");
    pill.textContent = "Denegado";
    pill.className = "pill bad";
    return;
  }
  location.replace(next);
});
