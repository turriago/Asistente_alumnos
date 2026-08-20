"""Sirve la carpeta web y dice la IP de la red para el QR del celular."""

from __future__ import annotations

import json
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8787


def lan_ips() -> list[str]:
    found: list[str] = []
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        if ip and not ip.startswith("127."):
            found.append(ip)
    except OSError:
        pass
    hostname = socket.gethostname()
    try:
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = item[4][0]
            if ip not in found and not ip.startswith("127."):
                found.append(ip)
    except OSError:
        pass
    return found


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/lan.json":
            payload = json.dumps({"ips": lan_ips(), "port": PORT}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format % args))


def main() -> None:
    ips = lan_ips()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"En este PC:    http://127.0.0.1:{PORT}/listado.html")
    print(f"QR de clase:   http://127.0.0.1:{PORT}/profe.html")
    for ip in ips:
        print(f"En el celular: http://{ip}:{PORT}/profe.html")
        print("  (misma WiFi; si no entra, permite Python en el firewall de Windows)")
    print("Netlify sigue siendo lo más estable para iPhone.")
    server.serve_forever()


if __name__ == "__main__":
    main()
