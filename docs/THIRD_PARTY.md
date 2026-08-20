# Terceros

No se copió código de Facenox (AGPL), ni de computervisioneng, ni de BIKRAMADITTYA.

Este archivo se actualiza cada vez que se añade una dependencia o un modelo.

## OpenCV

| Campo | Valor |
|---|---|
| Proyecto | OpenCV |
| URL | https://github.com/opencv/opencv |
| Autor | OpenCV team |
| Licencia | Apache-2.0 |
| Componentes utilizados | `cv2.VideoCapture`, dibujo de texto, ventana de visualización |
| Motivo | Acceso a webcam en Windows y overlay de FPS/resolución |
| Cambios realizados | Ninguno. Uso de la API pública vía `opencv-python` |

## NumPy

| Campo | Valor |
|---|---|
| Proyecto | NumPy |
| URL | https://github.com/numpy/numpy |
| Licencia | BSD-3-Clause |
| Componentes utilizados | arrays de imagen |
| Motivo | Representar frames |
| Cambios realizados | Ninguno |

## PyYAML

| Campo | Valor |
|---|---|
| Proyecto | PyYAML |
| URL | https://github.com/yaml/pyyaml |
| Licencia | MIT |
| Componentes utilizados | carga de `config/default.yaml` |
| Motivo | Configuración sin hardcodear |
| Cambios realizados | Ninguno |

## YuNet (OpenCV Zoo)

| Campo | Valor |
|---|---|
| Proyecto | Face Detection YuNet |
| URL | https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet |
| Autor | Shiqi Yu / OpenCV Zoo |
| Licencia | MIT |
| Componentes utilizados | `face_detection_yunet_2023mar.onnx` vía `cv2.FaceDetectorYN` |
| Motivo | Detector facial ligero en CPU, Windows, sin InsightFace todavía |
| Cambios realizados | Ninguno. Se descarga el ONNX oficial a `models/` (gitignored) |

## SQLAlchemy

| Campo | Valor |
|---|---|
| Proyecto | SQLAlchemy |
| URL | https://github.com/sqlalchemy/sqlalchemy |
| Licencia | MIT |
| Componentes utilizados | ORM + SQLite |
| Motivo | Estudiantes y embeddings locales, esquema portable a PostgreSQL |
| Cambios realizados | Ninguno |

## InsightFace (evaluado, no instalado)

| Campo | Valor |
|---|---|
| Proyecto | InsightFace |
| URL | https://github.com/deepinsight/insightface |
| Licencia | Código MIT. Modelos buffalo_*: investigación no comercial |
| Componentes utilizados | Ninguno en runtime |
| Motivo de no uso | `insightface 0.7.3` exige Microsoft Visual C++ 14+ para compilar en Windows/Python 3.12 |
| Alternativa | OpenCV SFace (abajo) |

## OpenCV SFace

| Campo | Valor |
|---|---|
| Proyecto | SFace (OpenCV Zoo) |
| URL | https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface |
| Licencia | Apache-2.0 |
| Componentes utilizados | `face_recognition_sface_2021dec.onnx` vía `cv2.FaceRecognizerSF` |
| Motivo | Embeddings locales en CPU, instalación sin compilador C++ |
| Cambios realizados | Ninguno. ONNX en `models/` (gitignored) |

## Pillow

| Campo | Valor |
|---|---|
| Proyecto | Pillow |
| URL | https://github.com/python-pillow/Pillow |
| Licencia | HPND (histórico MIT-like) |
| Componentes utilizados | `ImageFont` + `ImageDraw` para tildes en overlay |
| Motivo | `cv2.putText` (Hershey) no dibuja é/á/ó; mostraba `P??rez` |
| Cambios realizados | Ninguno. Fuente del sistema (Segoe UI / Arial en Windows) |

## FastAPI / Uvicorn

| Campo | Valor |
|---|---|
| Proyecto | FastAPI, Uvicorn |
| URL | https://github.com/fastapi/fastapi |
| Licencia | MIT |
| Componentes utilizados | HTTP local, MJPEG, JSON de estado |
| Motivo | Kiosco HTML en el navegador, un solo proceso |
| Cambios realizados | Ninguno |

## MediaPipe Hands

| Campo | Valor |
|---|---|
| Proyecto | MediaPipe (Google AI Edge) |
| URL | https://github.com/google-ai-edge/mediapipe |
| Licencia | Apache-2.0 |
| Componentes utilizados | Tasks `HandLandmarker` + `hand_landmarker.task` |
| Motivo | Esqueleto de 21 puntos por mano en CPU, Windows, Python 3.12 |
| Cambios realizados | Ninguno. Modelo oficial en `models/` (gitignored) |

## Ideas conceptuales (sin código)

| Proyecto | Licencia | Qué se tomó | Qué no se tomó |
|---|---|---|---|
| [facenox/facenox](https://github.com/facenox/facenox) | AGPL-3.0 | Local-first, embeddings, docs de privacidad | Ningún archivo |
| [computervisioneng/face-attendance-system](https://github.com/computervisioneng/face-attendance-system) | MIT | Manejo de error de cámara / liveness como idea futura | `dlib`, Tkinter, pickle |
| [BIKRAMADITTYA/face-recognition-attendance-system](https://github.com/BIKRAMADITTYA/face-recognition-attendance-system) | Sin licencia | Nada de código | Todo el código |
