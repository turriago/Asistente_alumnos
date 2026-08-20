const QR_LIVE_KEY = "qr-live";

export function loadQrLive() {
  try {
    const raw = sessionStorage.getItem(QR_LIVE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || !data.expiresAt || Date.now() >= Number(data.expiresAt)) {
      sessionStorage.removeItem(QR_LIVE_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export function saveQrLive(data) {
  try {
    sessionStorage.setItem(QR_LIVE_KEY, JSON.stringify(data));
  } catch {
    /* modo privado */
  }
}

export function clearQrLive() {
  try {
    sessionStorage.removeItem(QR_LIVE_KEY);
  } catch {
    /* modo privado */
  }
}

export function isQrRunning() {
  return Boolean(loadQrLive());
}
