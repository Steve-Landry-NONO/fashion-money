from app.capture import router as capture_router
from app.capture.providers import MockDecompositionProvider
from app.capture.storage import MemoryImageStorage


def test_upload_stores_real_bytes_and_creates_look(client, monkeypatch):
    storage = MemoryImageStorage()
    monkeypatch.setattr(capture_router, "get_image_storage", lambda: storage)
    monkeypatch.setattr(
        capture_router,
        "get_decomposition_provider",
        lambda _storage=None: MockDecompositionProvider(),
    )

    response = client.post(
        "/captures/upload",
        files={"file": ("look.jpg", b"real-image-bytes", "image/jpeg")},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ready"
    assert len(storage.objects) == 1
    stored = next(iter(storage.objects.values()))
    assert stored.data == b"real-image-bytes"
    assert stored.content_type == "image/jpeg"


def test_upload_rejects_unsupported_media(client):
    response = client.post(
        "/captures/upload",
        files={"file": ("look.gif", b"gif", "image/gif")},
    )
    assert response.status_code == 415
