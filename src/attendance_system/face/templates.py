"""Empaquetado de uno o varios embeddings por estudiante. Compatible con el BLOB antiguo."""

from __future__ import annotations

import struct

import numpy as np

from attendance_system.face.embedder import l2_normalize

MAGIC = b"EMB2"


def pack_embeddings(vectors: list[np.ndarray]) -> tuple[bytes, int]:
    if not vectors:
        raise ValueError("Hace falta al menos un embedding.")
    mats = [l2_normalize(item) for item in vectors]
    dim = int(mats[0].size)
    for item in mats:
        if item.size != dim:
            raise ValueError("Todos los embeddings deben tener la misma dimensión.")
    header = MAGIC + struct.pack("<HH", len(mats), dim)
    body = np.stack(mats).astype(np.float32, copy=False).tobytes()
    return header + body, dim


def unpack_embeddings(blob: bytes, dim: int | None) -> list[np.ndarray]:
    if blob.startswith(MAGIC):
        count, stored_dim = struct.unpack_from("<HH", blob, 4)
        data = np.frombuffer(blob[8:], dtype=np.float32)
        expected = int(count) * int(stored_dim)
        if data.size != expected:
            raise ValueError("BLOB de embeddings incompleto.")
        return [row.copy() for row in data.reshape(int(count), int(stored_dim))]
    if dim is None or dim <= 0:
        raise ValueError("Embedding legado sin dimensión.")
    vector = np.frombuffer(blob, dtype=np.float32)
    if vector.size != dim:
        raise ValueError("Embedding legado con tamaño inesperado.")
    return [vector.copy()]
