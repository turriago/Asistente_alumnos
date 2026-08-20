# Arquitectura

Prototipo académico local. Un PC procesa. Una pantalla muestra. La cámara del teléfono se añadirá después; hoy se usa la webcam del PC.

## Principios

- Un solo proceso. Sin Kubernetes, sin nube, sin microservicios.
- Separación por módulos (`camera`, `face`, `hands`, `attendance`, ...).
- Máquina de estados para no mezclar identificación, desafío y registro.
- Biometría en RAM. En disco, embeddings (cuando existan), no un archivo de fotos.
- Configuración en YAML / variables de entorno.

## Componentes actuales (Fase 8)

```
cámara + YuNet + SFace + MediaPipe Hands
        │
        ▼
   KioskEngine (hilo) + ChallengeManager
        │
        ├─ MJPEG  /stream.mjpeg  (rostro + manos + número pedido)
        └─ JSON   /api/status    (identidad + reto 1/3, 2/3, 3/3)
                │
                ▼
         FastAPI 127.0.0.1:8080
                │
                ▼
         HTML kiosco (navegador)
```

Hay recuento de dedos 1–10 y un reto de **3 números aleatorios seguidos** (hay que bajar las manos entre cada uno). No se registra asistencia todavía.

## Componentes previstos

```
Teléfono (Fase 12, opcional)          Webcam PC (Fases 1-11)
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
                 FastAPI local
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     camera          face           hands
                       │              │
                       └──────┬───────┘
                              ▼
                    AttendanceSession
                    (máquina de estados)
                              ▼
                         SQLite
                              ▼
                      UI kiosco HTML
```

## Máquina de estados (Fase 8)

`IDLE → IDENTIFIED → CHALLENGE (3 números) → SUCCESS | FAILED → HOLD → IDLE`

No hay `ATTENDANCE_REGISTERED` todavía.

## Estructura de carpetas

```
src/attendance_system/   código
config/                  YAML
tests/                   pytest
docs/                    documentación
data/sample/             datos ficticios
scripts/                 atajos de ejecución
models/                  pesos locales (gitignored)
```

Los paquetes `attendance` y `security` se crearán en su fase.

## Límites de esta fase

El kiosco muestra vídeo, identidad y un reto de 3 números aleatorios con las manos. No registra asistencia. No se suben fotos ni la base SQLite a Git.
