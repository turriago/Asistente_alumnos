# Instalación (Windows)

## Requisitos

- Windows 10/11.
- **Python 3.11 o 3.12**. Evita 3.13 y 3.14: MediaPipe no es fiable ahí.
- Una webcam (integrada o USB).
- No hace falta GPU. La primera ejecución de la Fase 2 necesita internet para bajar YuNet (~230 KB), salvo que ya esté en `models/`.

Comprueba la versión:

```powershell
python --version
```

## Entorno virtual

Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Si PowerShell bloquea scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Instalación alternativa solo con requirements:

```powershell
pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
```

## Configuración local

```powershell
copy .env.example .env
```

Edita `.env` si tu webcam no es el índice 0.

## Ejecutar enrolamiento (Fase 3)

Cierra la app Cámara de Windows. Luego:

```powershell
pip install -e ".[dev]"
python scripts/create_demo_data.py
python -m attendance_system.students.enroll --id 20260001
```

La primera vez se descarga SFace (~37 MB, OpenCV Zoo). Frente a la cámara, pulsa **E** tres veces (frente, izquierda, derecha).

## Ejecutar reconocimiento (Fase 4)

Cierra la app Cámara de Windows. Con al menos un rostro enrolado:

```powershell
python -m attendance_system.face.recognize
```

Si dice `NO IDENTIFICADO` siendo tú, baja `FACE_MATCH_THRESHOLD` (por ejemplo `0.36`).

## Ejecutar el kiosco (Fase 8)

Cierra la app Cámara de Windows y la demo de OpenCV si sigue abierta (la webcam no se comparte bien). Luego:

```powershell
python -m attendance_system.kiosk.app
```

Se abre `http://127.0.0.1:8080/`. Una mano = 1–5; las dos = 6–10. Ctrl+C en la terminal para salir.

La primera vez se descarga `hand_landmarker.task` (~7 MB) a `models/`.

Demo solo de manos (ventana OpenCV):

```powershell
python -m attendance_system.hands.demo
```

## Ejecutar la demo de detección (Fase 2)

```powershell
python scripts/download_models.py
python -m attendance_system.face.demo
```

Verás cajas alrededor de los rostros. No aparecen nombres. Sal con **Q** o **Escape**.

La demo solo de cámara sigue disponible:

```powershell
python -m attendance_system.camera.demo
```

## Tests

```powershell
pytest
```

Los tests no necesitan webcam: la cámara se simula.

## Si la cámara no abre

1. Cierra Teams, Zoom, Camera de Windows, Discord.
2. Prueba `CAMERA_INDEX=1` o `2`.
3. En `config/default.yaml` prueba `backend: msmf` o `backend: any`.
4. Mira [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
