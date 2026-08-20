"""FastAPI local: kiosco HTML + MJPEG. Solo localhost por defecto."""

from __future__ import annotations

import asyncio
import re
import sys
import threading
import time
import webbrowser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import NoReturn

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from attendance_system.config import load_config
from attendance_system.kiosk.engine import KioskEngine
from attendance_system.logging_setup import setup_logging

STATIC_DIR = Path(__file__).resolve().parent / "static"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def create_app(engine: KioskEngine | None = None) -> FastAPI:
    config = load_config()
    kiosk_engine = engine or KioskEngine(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if engine is None:
            kiosk_engine.start()
        yield
        if engine is None:
            kiosk_engine.stop()

    app = FastAPI(title="Kiosco de asistencia", lifespan=lifespan)
    app.state.engine = kiosk_engine
    app.state.config = config
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    @app.get("/api/status")
    def status() -> dict[str, object]:
        return kiosk_engine.latest_status().to_dict()

    @app.post("/api/challenge/start")
    def start_challenge() -> dict[str, object]:
        payload = kiosk_engine.start_challenge()
        if not payload.get("ok"):
            raise HTTPException(status_code=400, detail=str(payload.get("error") or "No se pudo iniciar."))
        return payload

    @app.post("/api/challenge/reset")
    def reset_challenge() -> dict[str, object]:
        return kiosk_engine.reset_scan()

    @app.get("/api/web-gallery")
    def web_gallery() -> dict[str, object]:
        from attendance_system.gallery_sync import build_web_gallery

        return build_web_gallery(config)

    @app.post("/api/web-gallery/publish")
    def publish_gallery() -> dict[str, object]:
        from attendance_system.gallery_sync import publish_web_gallery

        return publish_web_gallery(config)

    @app.get("/api/photo/{student_id}")
    def photo(student_id: str) -> Response:
        if not _SAFE_ID.match(student_id):
            raise HTTPException(status_code=400, detail="ID inválido.")
        path = (config.database.photos_dir / f"{student_id}.jpg").resolve()
        root = config.database.photos_dir.resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Sin miniatura.") from exc
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Sin miniatura.")
        return FileResponse(path, media_type="image/jpeg")

    @app.get("/stream.mjpeg")
    async def stream() -> StreamingResponse:
        async def frames() -> AsyncIterator[bytes]:
            while True:
                jpeg = kiosk_engine.latest_jpeg()
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                await asyncio.sleep(0.04)

        return StreamingResponse(
            frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    return app


def main() -> NoReturn:
    try:
        import uvicorn
    except ImportError:
        print("Falta uvicorn. Ejecuta: pip install -e \".[dev]\"", file=sys.stderr)
        raise SystemExit(1)

    config = load_config()
    setup_logging(config.logging)
    host = config.kiosk.host
    port = config.kiosk.port
    url = f"http://{host}:{port}/"
    print(f"Kiosco Fase 8: {url}")
    print("Cierra la app Cámara de Windows. Ctrl+C para salir.")
    print("Identifícate, pulsa Iniciar prueba y muestra 3 números aleatorios.")

    def _open_browser() -> None:
        time.sleep(1.4)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(
        "attendance_system.kiosk.app:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )
    raise SystemExit(0)


if __name__ == "__main__":
    main()
