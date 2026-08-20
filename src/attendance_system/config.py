"""Carga de configuración desde YAML y variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"


class ConfigError(Exception):
    """La configuración no se pudo cargar o es inválida."""


@dataclass(frozen=True)
class CameraSettings:
    index: int
    width: int
    height: int
    fps: int
    backend: str
    reconnect_attempts: int
    reconnect_delay_seconds: float
    mirror: bool
    auto_select: bool
    dark_mean_threshold: float
    warmup_frames: int


@dataclass(frozen=True)
class LoggingSettings:
    level: str
    directory: Path
    file: str


@dataclass(frozen=True)
class FaceSettings:
    detector: str
    model_path: Path
    score_threshold: float
    nms_threshold: float
    min_face_size: int
    draw_landmarks: bool
    auto_download: bool
    match_threshold: float
    match_interval_ms: int
    enroll_poses: tuple[str, ...]


@dataclass(frozen=True)
class HandsSettings:
    max_num_hands: int
    min_detection_confidence: float
    min_presence_confidence: float
    min_tracking_confidence: float
    model_path: Path
    auto_download: bool
    detect_interval_ms: int
    finger_extend_ratio: float
    thumb_extend_ratio: float
    number_stable_ms: int
    max_dx_faces: float
    max_dy_below_faces: float
    max_dy_above_faces: float
    min_palm_to_face: float
    min_up_fingers: int
    min_hand_of_largest: float
    min_foreground_face: float


@dataclass(frozen=True)
class ChallengeSettings:
    sequence_length: int
    timeout_seconds: float
    cooldown_seconds: float
    min_number: int
    max_number: int


@dataclass(frozen=True)
class DatabaseSettings:
    path: Path
    photos_dir: Path
    inbox_dir: Path


@dataclass(frozen=True)
class KioskSettings:
    host: str
    port: int
    jpeg_quality: int


@dataclass(frozen=True)
class AppConfig:
    demo_mode: bool
    camera: CameraSettings
    logging: LoggingSettings
    face: FaceSettings
    hands: HandsSettings
    challenge: ChallengeSettings
    database: DatabaseSettings
    kiosk: KioskSettings
    config_path: Path


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _as_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _enroll_poses(raw: Any) -> tuple[str, ...]:
    default = ("Frente", "Izquierda", "Derecha")
    if raw is None:
        return default
    if isinstance(raw, str):
        parts = [item.strip() for item in raw.split(",") if item.strip()]
        return tuple(parts) if parts else default
    if isinstance(raw, list):
        parts = [str(item).strip() for item in raw if str(item).strip()]
        return tuple(parts) if parts else default
    return default


def find_config_path(explicit: str | Path | None = None) -> Path:
    if explicit:
        path = Path(explicit)
    else:
        env_path = os.getenv("ATTENDANCE_CONFIG")
        path = Path(env_path) if env_path else DEFAULT_CONFIG_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"No se encontró el archivo de configuración: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML inválido en {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"El archivo {path} debe contener un mapeo YAML.")
    return data


def load_config(explicit_path: str | Path | None = None) -> AppConfig:
    path = find_config_path(explicit_path)
    raw = load_yaml(path)

    camera_raw = raw.get("camera") or {}
    logging_raw = raw.get("logging") or {}
    face_raw = raw.get("face") or {}
    database_raw = raw.get("database") or {}
    kiosk_raw = raw.get("kiosk") or {}

    camera = CameraSettings(
        index=_as_int(os.getenv("CAMERA_INDEX", camera_raw.get("index")), 0),
        width=_as_int(os.getenv("CAMERA_WIDTH", camera_raw.get("width")), 1280),
        height=_as_int(os.getenv("CAMERA_HEIGHT", camera_raw.get("height")), 720),
        fps=_as_int(os.getenv("CAMERA_FPS", camera_raw.get("fps")), 30),
        backend=str(os.getenv("CAMERA_BACKEND", camera_raw.get("backend", "msmf"))).lower(),
        reconnect_attempts=_as_int(camera_raw.get("reconnect_attempts"), 3),
        reconnect_delay_seconds=_as_float(camera_raw.get("reconnect_delay_seconds"), 1.0),
        mirror=_as_bool(os.getenv("CAMERA_MIRROR", camera_raw.get("mirror")), True),
        auto_select=_as_bool(os.getenv("CAMERA_AUTO_SELECT", camera_raw.get("auto_select")), True),
        dark_mean_threshold=_as_float(camera_raw.get("dark_mean_threshold"), 45.0),
        warmup_frames=_as_int(camera_raw.get("warmup_frames"), 12),
    )
    if camera.width <= 0 or camera.height <= 0:
        raise ConfigError("La resolución de cámara debe ser positiva.")
    if camera.fps <= 0:
        raise ConfigError("CAMERA FPS debe ser mayor que 0.")
    if camera.backend not in {"dshow", "msmf", "any"}:
        raise ConfigError("camera.backend debe ser 'dshow', 'msmf' o 'any'.")

    log_dir = Path(logging_raw.get("directory", "logs"))
    if not log_dir.is_absolute():
        log_dir = PROJECT_ROOT / log_dir

    logging = LoggingSettings(
        level=str(os.getenv("LOG_LEVEL", logging_raw.get("level", "INFO"))).upper(),
        directory=log_dir,
        file=str(logging_raw.get("file", "attendance.log")),
    )

    demo_mode = _as_bool(os.getenv("DEMO_MODE", raw.get("demo_mode")), True)

    model_path = Path(os.getenv("FACE_MODEL_PATH", face_raw.get("model_path", "models/face_detection_yunet_2023mar.onnx")))
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path

    face = FaceSettings(
        detector=str(face_raw.get("detector", "yunet")).lower(),
        model_path=model_path,
        score_threshold=_as_float(
            os.getenv("FACE_SCORE_THRESHOLD", face_raw.get("score_threshold")),
            0.7,
        ),
        nms_threshold=_as_float(face_raw.get("nms_threshold"), 0.3),
        min_face_size=_as_int(os.getenv("FACE_MIN_SIZE", face_raw.get("min_face_size")), 40),
        draw_landmarks=_as_bool(face_raw.get("draw_landmarks"), True),
        auto_download=_as_bool(face_raw.get("auto_download"), True),
        match_threshold=_as_float(
            os.getenv("FACE_MATCH_THRESHOLD", face_raw.get("match_threshold")),
            0.45,
        ),
        match_interval_ms=_as_int(
            os.getenv("FACE_MATCH_INTERVAL_MS", face_raw.get("match_interval_ms")),
            120,
        ),
        enroll_poses=_enroll_poses(face_raw.get("enroll_poses")),
    )
    if not 0 <= face.score_threshold <= 1:
        raise ConfigError("face.score_threshold debe estar entre 0 y 1.")
    if not 0 <= face.match_threshold <= 1:
        raise ConfigError("face.match_threshold debe estar entre 0 y 1.")
    if face.match_interval_ms < 0:
        raise ConfigError("face.match_interval_ms no puede ser negativo.")
    if face.min_face_size <= 0:
        raise ConfigError("face.min_face_size debe ser positivo.")
    if not face.enroll_poses:
        raise ConfigError("face.enroll_poses no puede estar vacío.")

    hands_raw = raw.get("hands") or {}
    hands_model_path = Path(
        os.getenv("HANDS_MODEL_PATH", hands_raw.get("model_path", "models/hand_landmarker.task"))
    )
    if not hands_model_path.is_absolute():
        hands_model_path = PROJECT_ROOT / hands_model_path
    hands = HandsSettings(
        max_num_hands=_as_int(os.getenv("HANDS_MAX_NUM", hands_raw.get("max_num_hands")), 4),
        min_detection_confidence=_as_float(
            os.getenv("HANDS_MIN_DETECTION", hands_raw.get("min_detection_confidence")),
            0.5,
        ),
        min_presence_confidence=_as_float(
            hands_raw.get("min_presence_confidence"),
            0.5,
        ),
        min_tracking_confidence=_as_float(
            hands_raw.get("min_tracking_confidence"),
            0.5,
        ),
        model_path=hands_model_path,
        auto_download=_as_bool(hands_raw.get("auto_download"), True),
        detect_interval_ms=_as_int(
            os.getenv("HANDS_DETECT_INTERVAL_MS", hands_raw.get("detect_interval_ms")),
            0,
        ),
        finger_extend_ratio=_as_float(hands_raw.get("finger_extend_ratio"), 1.08),
        thumb_extend_ratio=_as_float(hands_raw.get("thumb_extend_ratio"), 1.12),
        number_stable_ms=_as_int(
            os.getenv("HANDS_NUMBER_STABLE_MS", hands_raw.get("number_stable_ms")),
            400,
        ),
        max_dx_faces=_as_float(hands_raw.get("max_dx_faces"), 1.65),
        max_dy_below_faces=_as_float(hands_raw.get("max_dy_below_faces"), 2.3),
        max_dy_above_faces=_as_float(hands_raw.get("max_dy_above_faces"), 0.85),
        min_palm_to_face=_as_float(hands_raw.get("min_palm_to_face"), 0.38),
        min_up_fingers=_as_int(hands_raw.get("min_up_fingers"), 2),
        min_hand_of_largest=_as_float(hands_raw.get("min_hand_of_largest"), 0.58),
        min_foreground_face=_as_float(hands_raw.get("min_foreground_face"), 0.9),
    )
    if hands.max_num_hands <= 0:
        raise ConfigError("hands.max_num_hands debe ser positivo.")
    if not 0 <= hands.min_detection_confidence <= 1:
        raise ConfigError("hands.min_detection_confidence debe estar entre 0 y 1.")
    if not 0 <= hands.min_presence_confidence <= 1:
        raise ConfigError("hands.min_presence_confidence debe estar entre 0 y 1.")
    if not 0 <= hands.min_tracking_confidence <= 1:
        raise ConfigError("hands.min_tracking_confidence debe estar entre 0 y 1.")
    if hands.detect_interval_ms < 0:
        raise ConfigError("hands.detect_interval_ms no puede ser negativo.")
    if hands.finger_extend_ratio <= 1:
        raise ConfigError("hands.finger_extend_ratio debe ser mayor que 1.")
    if hands.thumb_extend_ratio <= 1:
        raise ConfigError("hands.thumb_extend_ratio debe ser mayor que 1.")
    if hands.number_stable_ms < 0:
        raise ConfigError("hands.number_stable_ms no puede ser negativo.")
    if hands.max_dx_faces <= 0:
        raise ConfigError("hands.max_dx_faces debe ser positivo.")
    if hands.max_dy_below_faces <= 0:
        raise ConfigError("hands.max_dy_below_faces debe ser positivo.")
    if hands.max_dy_above_faces <= 0:
        raise ConfigError("hands.max_dy_above_faces debe ser positivo.")
    if not 0 < hands.min_palm_to_face < 1:
        raise ConfigError("hands.min_palm_to_face debe estar entre 0 y 1.")
    if hands.min_up_fingers < 1:
        raise ConfigError("hands.min_up_fingers debe ser al menos 1.")
    if not 0 < hands.min_hand_of_largest <= 1:
        raise ConfigError("hands.min_hand_of_largest debe estar entre 0 y 1.")
    if hands.min_foreground_face <= 0:
        raise ConfigError("hands.min_foreground_face debe ser positivo.")

    challenge_raw = raw.get("challenge") or {}
    challenge = ChallengeSettings(
        sequence_length=_as_int(challenge_raw.get("sequence_length"), 3),
        timeout_seconds=_as_float(
            os.getenv("CHALLENGE_TIMEOUT", challenge_raw.get("timeout_seconds")),
            12.0,
        ),
        cooldown_seconds=_as_float(
            os.getenv("CHALLENGE_COOLDOWN", challenge_raw.get("cooldown_seconds")),
            8.0,
        ),
        min_number=_as_int(challenge_raw.get("min_number"), 1),
        max_number=_as_int(challenge_raw.get("max_number"), 10),
    )
    if challenge.sequence_length < 2:
        raise ConfigError("challenge.sequence_length debe ser al menos 2.")
    if challenge.timeout_seconds <= 0:
        raise ConfigError("challenge.timeout_seconds debe ser positivo.")
    if challenge.cooldown_seconds < 0:
        raise ConfigError("challenge.cooldown_seconds no puede ser negativo.")
    if challenge.min_number < 1 or challenge.max_number > 10:
        raise ConfigError("challenge.min_number/max_number deben estar entre 1 y 10.")
    if challenge.min_number >= challenge.max_number:
        raise ConfigError("challenge.min_number debe ser menor que max_number.")

    db_path = Path(os.getenv("DATABASE_PATH", database_raw.get("path", "data/attendance.db")))
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    photos_dir = Path(database_raw.get("photos_dir", "data/photos"))
    if not photos_dir.is_absolute():
        photos_dir = PROJECT_ROOT / photos_dir
    inbox_dir = Path(os.getenv("ENROLL_INBOX", database_raw.get("inbox_dir", "data/enroll_inbox")))
    if not inbox_dir.is_absolute():
        inbox_dir = PROJECT_ROOT / inbox_dir

    kiosk = KioskSettings(
        host=str(os.getenv("KIOSK_HOST", kiosk_raw.get("host", "127.0.0.1"))),
        port=_as_int(os.getenv("KIOSK_PORT", kiosk_raw.get("port")), 8080),
        jpeg_quality=_as_int(kiosk_raw.get("jpeg_quality"), 80),
    )
    if kiosk.port <= 0 or kiosk.port > 65535:
        raise ConfigError("kiosk.port debe estar entre 1 y 65535.")
    if not 1 <= kiosk.jpeg_quality <= 100:
        raise ConfigError("kiosk.jpeg_quality debe estar entre 1 y 100.")

    return AppConfig(
        demo_mode=demo_mode,
        camera=camera,
        logging=logging,
        face=face,
        hands=hands,
        challenge=challenge,
        database=DatabaseSettings(path=db_path, photos_dir=photos_dir, inbox_dir=inbox_dir),
        kiosk=kiosk,
        config_path=path,
    )
