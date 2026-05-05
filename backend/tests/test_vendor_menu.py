"""/vendor/me/menu — CRUD with daily_quota and cross-vendor scoping."""
import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.vendor_categories import (
    get_menu_category_repository,
    get_menu_item_repository_for_category,
)
from backend.routes.vendor_menu import (
    get_menu_item_repository,
    get_photo_storage,
)
from backend.storage.photo_storage import PhotoStorage


def _setup(tmp_path: Path) -> tuple[TestClient, MenuItemRepository, MenuCategoryRepository]:
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(VendorRecord(id=1, name="Alice", status="approved"))
    vendor_repo.seed(VendorRecord(id=2, name="Bob", status="approved"))

    cat_repo = MenuCategoryRepository()
    item_repo = MenuItemRepository()
    storage = PhotoStorage(root=tmp_path)

    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_category_repository] = lambda: cat_repo
    app.dependency_overrides[get_menu_item_repository_for_category] = lambda: item_repo
    app.dependency_overrides[get_menu_item_repository] = lambda: item_repo
    app.dependency_overrides[get_photo_storage] = lambda: storage
    return TestClient(app), item_repo, cat_repo


def _h(vid: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vid)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_create_menu_item_and_get(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    resp = client.post(
        "/vendor/me/menu",
        headers=_h(),
        json={"name": "Rice Bowl", "price_cents": 120, "daily_quota": 50},
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    got = client.get(f"/vendor/me/menu/{item_id}", headers=_h()).json()
    assert got["name"] == "Rice Bowl"
    assert got["daily_quota"] == 50


def test_daily_quota_round_trip_null_and_zero(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    null_item = client.post("/vendor/me/menu", headers=_h(), json={"name": "A", "price_cents": 10}).json()
    assert null_item["daily_quota"] is None
    zero_item = client.post("/vendor/me/menu", headers=_h(), json={"name": "B", "price_cents": 10, "daily_quota": 0}).json()
    assert zero_item["daily_quota"] == 0


def test_negative_daily_quota_rejected_422(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    resp = client.post("/vendor/me/menu", headers=_h(), json={"name": "A", "price_cents": 10, "daily_quota": -1})
    assert resp.status_code == 422


def test_list_filters_by_category(tmp_path: Path) -> None:
    client, item_repo, cat_repo = _setup(tmp_path)
    cat = cat_repo.create(vendor_id=1, name="Hot")
    item_repo.create(vendor_id=1, category_id=cat.id, name="Soup", price_cents=10)
    item_repo.create(vendor_id=1, category_id=None, name="Misc", price_cents=10)
    listed = client.get(f"/vendor/me/menu?category_id={cat.id}", headers=_h()).json()
    assert [i["name"] for i in listed] == ["Soup"]


def test_cross_vendor_get_returns_404(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)
    resp = client.get(f"/vendor/me/menu/{item.id}", headers=_h(2))
    assert resp.status_code == 404


def test_patch_partial_update(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10, daily_quota=50)
    resp = client.patch(f"/vendor/me/menu/{item.id}", headers=_h(), json={"daily_quota": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["daily_quota"] == 0
    assert body["name"] == "A"


def test_delete_item(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)
    assert client.delete(f"/vendor/me/menu/{item.id}", headers=_h()).status_code == 204
    assert client.get(f"/vendor/me/menu/{item.id}", headers=_h()).status_code == 404


def test_create_with_unknown_category_id_422(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    resp = client.post("/vendor/me/menu", headers=_h(), json={"name": "A", "price_cents": 10, "category_id": 999})
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


def test_unapproved_vendor_blocked(tmp_path: Path) -> None:
    client, _, _ = _setup(tmp_path)
    pending_repo = VendorProfileRepository()
    pending_repo.seed(VendorRecord(id=3, name="Pending", status="pending"))
    app.dependency_overrides[get_vendor_profile_repository] = lambda: pending_repo
    resp = client.get("/vendor/me/menu", headers={"x-user-role": "vendor_manager", "x-vendor-id": "3"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "vendor_not_approved"


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color="blue").save(buf, format="PNG")
    return buf.getvalue()


def test_put_photo_happy_path(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)

    resp = client.put(
        f"/vendor/me/menu/{item.id}/photo",
        headers=_h(),
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json() == {"photo_path": f"vendors/1/menu/{item.id}.jpg"}
    assert (tmp_path / f"vendors/1/menu/{item.id}.jpg").exists()
    assert item_repo.get(vendor_id=1, item_id=item.id).photo_path == f"vendors/1/menu/{item.id}.jpg"


def test_put_photo_rejects_non_image(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)
    resp = client.put(
        f"/vendor/me/menu/{item.id}/photo",
        headers=_h(),
        files={"file": ("evil.txt", b"not an image", "image/jpeg")},
    )
    assert resp.status_code == 415
    assert resp.json()["code"] == "invalid_image_type"


def test_put_photo_rejects_oversize(tmp_path: Path) -> None:
    # 用很小的 max_bytes 重新注入 storage
    tiny_storage = PhotoStorage(root=tmp_path, max_bytes=10)
    client, item_repo, _ = _setup(tmp_path)
    app.dependency_overrides[get_photo_storage] = lambda: tiny_storage
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)
    resp = client.put(
        f"/vendor/me/menu/{item.id}/photo",
        headers=_h(),
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "image_too_large"


def test_delete_photo_clears_path_and_file(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)
    client.put(
        f"/vendor/me/menu/{item.id}/photo",
        headers=_h(),
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )

    resp = client.delete(f"/vendor/me/menu/{item.id}/photo", headers=_h())
    assert resp.status_code == 204
    assert not (tmp_path / f"vendors/1/menu/{item.id}.jpg").exists()
    assert item_repo.get(vendor_id=1, item_id=item.id).photo_path is None


def test_put_photo_cross_vendor_404(tmp_path: Path) -> None:
    client, item_repo, _ = _setup(tmp_path)
    item = item_repo.create(vendor_id=1, name="A", price_cents=10)
    resp = client.put(
        f"/vendor/me/menu/{item.id}/photo",
        headers=_h(2),
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 404
