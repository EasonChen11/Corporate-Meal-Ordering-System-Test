"""/vendor/me/categories — CRUD with cross-vendor scoping and 409 on non-empty delete."""
from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.vendor_categories import (
    get_menu_category_repository,
    get_menu_item_repository_for_category,
)


def _setup() -> tuple[TestClient, MenuCategoryRepository, MenuItemRepository]:
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(VendorRecord(id=1, name="Alice", status="approved"))
    vendor_repo.seed(VendorRecord(id=2, name="Bob", status="approved"))

    cat_repo = MenuCategoryRepository()
    item_repo = MenuItemRepository()

    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_category_repository] = lambda: cat_repo
    app.dependency_overrides[get_menu_item_repository_for_category] = lambda: item_repo
    return TestClient(app), cat_repo, item_repo


def _h(vid: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vid)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_create_and_list() -> None:
    client, _, _ = _setup()
    resp = client.post("/vendor/me/categories", headers=_h(), json={"name": "Hot"})
    assert resp.status_code == 201
    new_id = resp.json()["id"]

    listing = client.get("/vendor/me/categories", headers=_h()).json()
    assert [c["id"] for c in listing] == [new_id]


def test_cross_vendor_get_returns_404() -> None:
    client, _, _ = _setup()
    created = client.post("/vendor/me/categories", headers=_h(1), json={"name": "Hot"}).json()
    resp = client.patch(f"/vendor/me/categories/{created['id']}", headers=_h(2), json={"name": "Stolen"})
    assert resp.status_code == 404


def test_delete_empty_category_204() -> None:
    client, _, _ = _setup()
    cat = client.post("/vendor/me/categories", headers=_h(), json={"name": "Hot"}).json()
    resp = client.delete(f"/vendor/me/categories/{cat['id']}", headers=_h())
    assert resp.status_code == 204


def test_delete_non_empty_category_returns_409() -> None:
    client, cat_repo, item_repo = _setup()
    cat = cat_repo.create(vendor_id=1, name="Hot")
    # Manually inject an item to simulate one existing in the category
    item_repo.create(vendor_id=1, category_id=cat.id, name="Soup", price_cents=100)

    resp = client.delete(f"/vendor/me/categories/{cat.id}", headers=_h())
    assert resp.status_code == 409
    assert resp.json()["code"] == "category_not_empty"


def test_create_rejects_blank_name_422() -> None:
    client, _, _ = _setup()
    resp = client.post("/vendor/me/categories", headers=_h(), json={"name": "   "})
    assert resp.status_code == 422
