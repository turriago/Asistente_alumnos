# Solución de problemas

## Cámara no disponible

Mensaje:

> ⚠️ Cámara no disponible.

Causas frecuentes en Windows:

1. Teams, Zoom, Camera, Discord u OBS tienen la webcam.
2. El índice no es 0. Cambia `CAMERA_INDEX` a 1 o 2.
3. Permisos de privacidad: Configuración de Windows → Privacidad → Cámara → permitir aplicaciones de escritorio.
4. El backend DirectShow falla en ese dispositivo. En `config/default.yaml` prueba `backend: msmf` o `backend: any`.
5. Cámara USB suelta o desconectada.

Los tests de pytest **no** abren la webcam. Si pytest pasa y la demo falla, el problema es el dispositivo, no el código de lógica.

## La ventana está negra / no se ve tu cara

En muchos portátiles Windows el **índice 0 es la cámara IR de Windows Hello**, no la webcam RGB. OpenCV la abre, mide FPS, y la imagen sale casi negra.

Qué hacer:

1. Cierra la demo (Q) y vuelve a abrirla: ahora busca sola una cámara más clara.
2. Si sigue negro, pulsa **N** para pasar a la siguiente cámara (también 0, 1, 2, 3, 4).
3. Quita la tapa física de la lente.
4. Configuración de Windows → Privacidad → Cámara: permite apps de escritorio.
5. Cierra Teams/Zoom **y la app Cámara de Windows**. Si Cámara sigue abierta, Python recibe un frame negro.

Abajo de la ventana hay una barra **LIVE**. Si se mueve el brillo, hay vídeo aunque se vea oscuro.

## FPS muy bajo

En la Fase 1 el overlay es barato. Un FPS bajo suele ser la webcam o un CPU ocupado. Más adelante, cara + manos bajarán el FPS: se medirá entonces.

## `python` no se reconoce

Usa `py -3.12` o instala Python y marca “Add to PATH”.

## MediaPipe / manos

Si no aparecen las líneas de las manos:

1. Acerca las palmas a la cámara, con luz frontal, sin taparlas.
2. Cierra la app Cámara de Windows.
3. La primera vez hace falta internet para bajar `models/hand_landmarker.task`.
4. Si el FPS baja mucho, sube `hands.detect_interval_ms` a `80` en `config/default.yaml`.
5. Si falla el import de MediaPipe en Windows: `pip install msvc-runtime` dentro del `.venv`.

El número 1–10 se lee solo de **tus** manos: palmas cerca de la cara, dedos hacia arriba. Las manos de gente que pasa salen en gris (“fondo”) y no cuentan.

El kiosco pide **3 números aleatorios** seguidos. Baja las manos entre cada uno. Una foto fija no puede cambiar el gesto.

## InsightFace no se usa

En este Windows, `pip install insightface` falló porque hace falta Microsoft Visual C++ 14+. El enrolamiento usa **OpenCV SFace**, que no compila C++ extra.

## El modelo YuNet o SFace no descarga

- Revisa internet.
- Ejecuta `python scripts/download_models.py`.
- YuNet: `models/face_detection_yunet_2023mar.onnx`
- SFace: `models/face_recognition_sface_2021dec.onnx`

## Enrolamiento: “necesito un solo rostro”

- Un solo estudiante frente a la cámara, de frente, con luz.
- Cierra la app Cámara de Windows.
- Pulsa **E** solo cuando el overlay diga LISTO PARA ENROLAR.

## Dice NO IDENTIFICADO aunque soy yo

- Más luz frontal, de frente a la cámara, un solo rostro.
- Re-enrola si cambió mucho la luz: `python -m attendance_system.students.enroll --id 20260001`
- Baja `FACE_MATCH_THRESHOLD` a `0.36` en `.env` o `config/default.yaml`.
- Pulsa **R** si enrolaste con la demo de reconocimiento ya abierta.

## El nombre sale como P??rez

Eso era `cv2.putText`, que no dibuja tildes. Ya se usa una fuente del sistema. Cierra la demo y ábrela de nuevo:

```powershell
python -m attendance_system.face.recognize
```

## No detecta el rostro

- Más luz frontal.
- Acércate: `min_face_size` ignora caras muy pequeñas.
- Baja `face.score_threshold` a `0.6` en `config/default.yaml` si hace falta.
- De lado extremo el detector puede fallar: es esperado en esta fase.

## El kiosco no abre o el vídeo está negro

- Cierra la demo de OpenCV y la app Cámara de Windows.
- Entra a `http://127.0.0.1:8080/` (no uses la IP de la red a menos que cambies `KIOSK_HOST`).
- Si el puerto 8080 está ocupado, cambia `KIOSK_PORT`.
- El recuadro “Siguiente paso” muestra el número leído. Aún no hay desafío: eso es Fase 8.

## OneDrive bloquea archivos

El proyecto está en OneDrive. Si SQLite se corrompe o se queda “en uso”, mueve `data/` fuera de la sincronización.
