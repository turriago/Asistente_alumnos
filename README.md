# Sistema inteligente de asistencia universitaria

Prototipo académico de **verificación de identidad y prueba de vivacidad** para tomar asistencia presencial en un salón.

No es un producto comercial. No afirma ser imposible de engañar.

## 1. Problema

Hoy la profesora lee una lista y cada estudiante dice "presente". El objetivo es demostrar un flujo automático:

1. La cámara ve el rostro.
2. El sistema identifica al estudiante registrado.
3. Se genera un desafío aleatorio con las manos (número 1–10).
4. Si identidad + gesto + vivacidad coinciden, se registra la asistencia.

**Estado actual: Fase 8.** El kiosco pide **3 números aleatorios seguidos** con las manos (vivacidad simple: una foto no puede cambiar el gesto). Todavía **no** registra asistencia.

## 2. Qué hace hoy

- Abre la webcam del PC con OpenCV.
- Detecta rostros con YuNet.
- Registra estudiantes de prueba (CSV ficticio → SQLite).
- Enrolamiento: un rostro → embedding **SFace** + miniatura 128×128.
- Reconocimiento en vivo: cosine vs galería. Si no llega al umbral → **NO IDENTIFICADO**.
- Kiosco en el navegador (`http://127.0.0.1:8080/`): cámara, ficha y reto de 3 números con las manos.

## 3. Arquitectura

Un solo proceso local en el PC de la profesora. Sin nube y sin microservicios.

Detalle: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 4. Tecnologías (plan aprobado)

| Pieza | Tecnología | Fase |
|---|---|---|
| Cámara | OpenCV | 1 |
| Detección facial | YuNet | 2 |
| Enrolamiento / embedding | OpenCV SFace | 3 |
| Reconocimiento en vivo | OpenCV SFace | 4 |
| Base de datos | SQLite | 3 |
| Liveness | MiniFASNet ONNX | 4–9 |
| Manos | MediaPipe Hands | 6–**8 (actual)** |
| Backend / UI | FastAPI + HTML kiosco | 5 |
| Export | pandas + OpenPyXL | 10–11 |

## 5. Instalación

Requisito: **Python 3.11 o 3.12** en Windows. No uses 3.13+ (MediaPipe fallará más adelante).

Pasos: [docs/INSTALLATION.md](docs/INSTALLATION.md).

## 6. Configuración

Valores en `config/default.yaml` y, si quieres, en `.env` (copia `.env.example`).

Los más importantes ahora:

- `CAMERA_INDEX` — prueba 0, 1 o 2
- `CAMERA_WIDTH` / `CAMERA_HEIGHT`
- `CAMERA_FPS`
- `DEMO_MODE`
- `FACE_SCORE_THRESHOLD` — confianza mínima de la caja (0–1)
- `FACE_MATCH_THRESHOLD` — similitud coseno mínima para decir el nombre (0–1)
- `KIOSK_HOST` / `KIOSK_PORT` — kiosco local (por defecto 127.0.0.1:8080)
- `HANDS_MAX_NUM` — manos simultáneas (por defecto 2)

## 7. Registrar estudiantes

Sin lista oficial: ya existen `data/enroll_inbox/persona_01` … `persona_10`. En cada una escribe el nombre en `nombre.txt` y deja 3 fotos.

```powershell
python -m attendance_system.students.enroll_files
```

El ID será temporal (`TMP-0001`). Detalle: `data/enroll_inbox/README.md`.

Con webcam (lista de demo):

```powershell
python scripts/create_demo_data.py
python -m attendance_system.students.enroll --id 20260001
```

## 8. Cómo ejecutar

Detección (Fase 2):

```powershell
python -m attendance_system.face.demo
```

Enrolamiento (Fase 3):

```powershell
python -m attendance_system.students.enroll --id 20260001
```

Reconocimiento (Fase 4):

```powershell
python -m attendance_system.face.recognize
```

Kiosco (Fase 8, reto de 3 números):

```powershell
python -m attendance_system.kiosk.app
```

Abre `http://127.0.0.1:8080/`. Una mano = 1–5. Las dos = 6–10. No registra asistencia.

Solo manos (ventana OpenCV):

```powershell
python -m attendance_system.hands.demo
```

## 9. Modo demo

`DEMO_MODE=true` usa estudiantes ficticios. `scripts/create_demo_data.py` carga `data/sample/students.sample.csv`. La base `data/attendance.db` y `data/photos/` no se suben a Git.

## 10. Cómo utilizar la cámara

1. Cierra Teams, Zoom u otra app que esté usando la webcam.
2. Ejecuta la demo.
3. Si ves `⚠️ Cámara no disponible`, cambia `CAMERA_INDEX`.
4. Guía de fallos: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## 11. Exportar asistencia

Pendiente (Fase 11).

## 12. Limitaciones actuales

- Solo webcam del PC.
- Detecta rostros y, si hay un enrolado, intenta identificarlo.
- Dibuja el esqueleto de las manos y lee el número 1–10 (dedos). No hay desafío ni asistencia.
- Un umbral alto da más “NO IDENTIFICADO”; uno bajo puede confundir personas.
- Los modelos InsightFace `buffalo_*` no se usaron: no compilaban en Windows 3.12 sin MSVC. El embedder es SFace (OpenCV Zoo).
- Miniaturas 128×128 en `data/photos/` (gitignored). El frame original se descarta.
- El kiosco no genera un desafío aleatorio ni guarda asistencia.

## 13. Privacidad

Este proyecto tratará datos biométricos. Lee [docs/PRIVACY.md](docs/PRIVACY.md).

No subas fotos reales, embeddings ni bases de datos a GitHub.

## 14. Licencias

Código propio: MIT. Terceros: [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md).

## 15. Futuras mejoras

Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md).

La siguiente fase, cuando la apruebes, es el desafío aleatorio (Fase 8).
