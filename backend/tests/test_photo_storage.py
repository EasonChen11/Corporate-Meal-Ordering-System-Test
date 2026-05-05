"""PhotoStorage: validate, re-encode, atomic write, idempotent delete."""
import io
from pathlib import Path

import pytest
from PIL import Image

from backend.core.errors import CodedHTTPException
from backend.storage.photo_storage import PhotoStorage


def _png_bytes(width: int = 100, height: int = 100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_store_writes_jpeg_and_returns_relative_path(tmp_path: Path) -> None:
    storage = PhotoStorage(root=tmp_path)
    rel = storage.store_menu_photo(vendor_id=1, item_id=2, data=_png_bytes())
    assert rel == "vendors/1/menu/2.jpg"
    on_disk = tmp_path / rel
    assert on_disk.exists()
    with Image.open(on_disk) as img:
        assert img.format == "JPEG"


def test_store_resizes_oversized_image(tmp_path: Path) -> None:
    storage = PhotoStorage(root=tmp_path, max_edge_px=100)
    storage.store_menu_photo(vendor_id=1, item_id=1, data=_png_bytes(width=1000, height=500))
    with Image.open(tmp_path / "vendors/1/menu/1.jpg") as img:
        assert max(img.size) == 100


def test_store_rejects_oversize_bytes(tmp_path: Path) -> None:
    storage = PhotoStorage(root=tmp_path, max_bytes=1024)
    with pytest.raises(CodedHTTPException) as exc:
        storage.store_menu_photo(vendor_id=1, item_id=1, data=_png_bytes(width=500, height=500))
    assert exc.value.status_code == 413
    assert exc.value.code == "image_too_large"


def test_store_rejects_non_image_bytes(tmp_path: Path) -> None:
    storage = PhotoStorage(root=tmp_path)
    with pytest.raises(CodedHTTPException) as exc:
        storage.store_menu_photo(vendor_id=1, item_id=1, data=b"this is not an image")
    assert exc.value.status_code == 415
    assert exc.value.code == "invalid_image_type"


def test_delete_existing_file(tmp_path: Path) -> None:
    storage = PhotoStorage(root=tmp_path)
    storage.store_menu_photo(vendor_id=1, item_id=1, data=_png_bytes())
    storage.delete_menu_photo(vendor_id=1, item_id=1)
    assert not (tmp_path / "vendors/1/menu/1.jpg").exists()


def test_delete_missing_file_is_idempotent(tmp_path: Path) -> None:
    storage = PhotoStorage(root=tmp_path)
    storage.delete_menu_photo(vendor_id=1, item_id=999)
