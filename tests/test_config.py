from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from attendance_system.config import CameraSettings, ConfigError, load_config


def write_config(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_load_config_from_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = write_config(
        tmp_path / "default.yaml",
        {
            "demo_mode": False,
            "camera": {
                "index": 2,
                "width": 640,
                "height": 480,
                "fps": 15,
                "backend": "any",
                "reconnect_attempts": 1,
                "reconnect_delay_seconds": 0.2,
            },
            "logging": {"level": "DEBUG", "directory": str(tmp_path / "logs"), "file": "test.log"},
        },
    )
    monkeypatch.delenv("CAMERA_INDEX", raising=False)
    monkeypatch.delenv("CAMERA_WIDTH", raising=False)
    monkeypatch.delenv("CAMERA_HEIGHT", raising=False)
    monkeypatch.delenv("CAMERA_FPS", raising=False)
    monkeypatch.delenv("CAMERA_BACKEND", raising=False)
    monkeypatch.delenv("CAMERA_MIRROR", raising=False)
    monkeypatch.delenv("CAMERA_AUTO_SELECT", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("FACE_SCORE_THRESHOLD", raising=False)
    monkeypatch.delenv("FACE_MATCH_THRESHOLD", raising=False)

    config = load_config(config_file)

    assert config.demo_mode is False
    assert config.camera == CameraSettings(
        index=2,
        width=640,
        height=480,
        fps=15,
        backend="any",
        reconnect_attempts=1,
        reconnect_delay_seconds=0.2,
        mirror=True,
        auto_select=True,
        dark_mean_threshold=45.0,
        warmup_frames=12,
    )
    assert config.logging.level == "DEBUG"
    assert config.logging.directory == tmp_path / "logs"
    assert config.face.detector == "yunet"
    assert 0 < config.face.score_threshold <= 1
    assert 0 < config.face.match_threshold <= 1
    assert config.hands.max_num_hands == 4
    assert config.hands.detect_interval_ms == 0
    assert config.hands.number_stable_ms == 400
    assert config.challenge.sequence_length == 3


def test_env_overrides_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = write_config(
        tmp_path / "default.yaml",
        {
            "demo_mode": False,
            "camera": {"index": 0, "width": 1280, "height": 720, "fps": 30, "backend": "dshow"},
            "logging": {"directory": str(tmp_path / "logs")},
        },
    )
    monkeypatch.setenv("CAMERA_INDEX", "1")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    monkeypatch.setenv("FACE_MATCH_THRESHOLD", "0.51")

    config = load_config(config_file)

    assert config.camera.index == 1
    assert config.demo_mode is True
    assert config.logging.level == "WARNING"
    assert config.face.match_threshold == pytest.approx(0.51)


def test_invalid_backend_raises(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path / "bad.yaml",
        {
            "camera": {"index": 0, "width": 640, "height": 480, "fps": 30, "backend": "cuda"},
            "logging": {"directory": str(tmp_path / "logs")},
        },
    )
    with pytest.raises(ConfigError, match="backend"):
        load_config(config_file)


def test_invalid_face_threshold_raises(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path / "bad_face.yaml",
        {
            "camera": {"index": 0, "width": 640, "height": 480, "fps": 30, "backend": "dshow"},
            "logging": {"directory": str(tmp_path / "logs")},
            "face": {"score_threshold": 1.5},
        },
    )
    with pytest.raises(ConfigError, match="score_threshold"):
        load_config(config_file)


def test_invalid_match_threshold_raises(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path / "bad_match.yaml",
        {
            "camera": {"index": 0, "width": 640, "height": 480, "fps": 30, "backend": "dshow"},
            "logging": {"directory": str(tmp_path / "logs")},
            "face": {"match_threshold": 1.4},
        },
    )
    with pytest.raises(ConfigError, match="match_threshold"):
        load_config(config_file)


def test_invalid_hands_confidence_raises(tmp_path: Path) -> None:
    config_file = write_config(
        tmp_path / "bad_hands.yaml",
        {
            "camera": {"index": 0, "width": 640, "height": 480, "fps": 30, "backend": "dshow"},
            "logging": {"directory": str(tmp_path / "logs")},
            "hands": {"min_detection_confidence": 1.4},
        },
    )
    with pytest.raises(ConfigError, match="min_detection_confidence"):
        load_config(config_file)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No se encontró"):
        load_config(tmp_path / "missing.yaml")
