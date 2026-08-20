# Desarrollo

## Fases

No se avanza de fase sin aprobación. La actual es **Fase 8 — ChallengeManager (3 números aleatorios)**.

## Entorno

Python 3.11 o 3.12. Dependencias en `pyproject.toml`. Tests con pytest.

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

## Dónde tocar código ahora

| Quieres cambiar | Archivo |
|---|---|
| Abrir/leer cámara | `src/attendance_system/camera/capture.py` |
| Detector y cajas | `src/attendance_system/face/` |
| Embeddings SFace | `src/attendance_system/face/embedder.py` |
| Matching cosine | `src/attendance_system/face/matcher.py` |
| Demo reconocimiento | `src/attendance_system/face/recognize.py` |
| Kiosco FastAPI | `src/attendance_system/kiosk/` |
| Manos MediaPipe | `src/attendance_system/hands/` |
| Estudiantes / SQLite | `src/attendance_system/students/` |
| Overlay / tildes | `src/attendance_system/drawing.py`, `text.py` |
| YAML / env | `src/attendance_system/config.py` |
| Logs | `src/attendance_system/logging_setup.py` |

## Convenciones

- Mensajes de usuario en español.
- Código y nombres de módulo en inglés.
- No hardcodear umbrales, índices ni rutas.
- No registrar embeddings ni recortes de rostro en logs.
- Una excepción de cámara no debe tumbar el proceso sin mensaje claro.

## Cómo probar la cámara a mano

```powershell
python -m attendance_system.kiosk.app
```

Comprueba:

- El navegador abre `http://127.0.0.1:8080/`.
- El vídeo se mueve.
- Tu cara enrolada muestra nombre, ID y programa.
- Al levantar las palmas aparece el esqueleto (puntos y líneas).
- El recuadro derecho muestra el **número** (1–10) si los dedos están claros.
- **No** pide un número secreto ni guarda asistencia.

## Commits

Cuando se pidan, serán por fase (`feat: add camera module`, etc.). No se hace un commit gigante de todo el sistema.
