from __future__ import annotations

import numpy as np
import pytest

from attendance_system.face.templates import pack_embeddings, unpack_embeddings


def test_pack_roundtrip_and_legacy_blob() -> None:
    first = np.array([3.0, 4.0], dtype=np.float32)
    second = np.array([0.0, 2.0], dtype=np.float32)
    blob, dim = pack_embeddings([first, second])
    assert dim == 2
    restored = unpack_embeddings(blob, dim)
    assert len(restored) == 2
    np.testing.assert_allclose(np.linalg.norm(restored[0]), 1.0, atol=1e-5)

    legacy = (first / np.linalg.norm(first)).astype(np.float32).tobytes()
    one = unpack_embeddings(legacy, 2)
    assert len(one) == 1
    np.testing.assert_allclose(np.linalg.norm(one[0]), 1.0, atol=1e-5)


def test_pack_rejects_empty() -> None:
    with pytest.raises(ValueError):
        pack_embeddings([])
