"""GET / PATCH /vendor/me/profile."""
from fastapi.testclient import TestClient

from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord


def _seed() -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved", address="Old"))
    repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")
    return repo


def _client(repo: VendorProfileRepository) -> TestClient:
    app.dependency_overrides[get_vendor_profile_repository] = lambda: repo
    return TestClient(app)


def _vendor_headers(vid: int = 1) -> dict[str, str]:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vid)}


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_get_profile_returns_vendor_with_facilities() -> None:
    response = _client(_seed()).get("/vendor/me/profile", headers=_vendor_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Alice Bento"
    assert body["status"] == "approved"
    assert body["served_facilities"] == [{"id": 10, "code": "F12A", "name": "Fab 12A"}]


def test_patch_updates_address_only() -> None:
    response = _client(_seed()).patch(
        "/vendor/me/profile",
        headers=_vendor_headers(),
        json={"address": "New address"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["address"] == "New address"
    assert body["name"] == "Alice Bento"


def test_patch_silently_ignores_served_facilities_in_body() -> None:
    response = _client(_seed()).patch(
        "/vendor/me/profile",
        headers=_vendor_headers(),
        json={"served_facilities": [{"id": 99, "code": "X", "name": "X"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert {f["code"] for f in body["served_facilities"]} == {"F12A"}


def test_unauthenticated_role_403() -> None:
    response = _client(_seed()).get(
        "/vendor/me/profile",
        headers={"x-user-role": "employee", "x-vendor-id": "1"},
    )
    assert response.status_code == 403
