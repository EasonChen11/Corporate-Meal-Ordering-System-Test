"""require_approved_vendor: enforces role + header + approval status."""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.core.errors import install_error_handler
from backend.core.vendor_identity import (
    get_vendor_profile_repository,
    require_approved_vendor,
)
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord


def _make_app(repo: VendorProfileRepository) -> TestClient:
    app = FastAPI()
    install_error_handler(app)

    @app.get("/probe")
    def probe(vendor_id: int = Depends(require_approved_vendor)) -> dict:
        return {"vendor_id": vendor_id}

    app.dependency_overrides[get_vendor_profile_repository] = lambda: repo
    return TestClient(app)


def _seed_repo(*, status: str = "approved") -> VendorProfileRepository:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=42, name="Alice", status=status))
    return repo


def test_returns_vendor_id_for_approved_vendor() -> None:
    client = _make_app(_seed_repo())
    response = client.get("/probe", headers={"x-user-role": "vendor_manager", "x-vendor-id": "42"})
    assert response.status_code == 200
    assert response.json() == {"vendor_id": 42}


def test_wrong_role_403() -> None:
    client = _make_app(_seed_repo())
    response = client.get("/probe", headers={"x-user-role": "employee", "x-vendor-id": "42"})
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_missing_vendor_id_header_400() -> None:
    client = _make_app(_seed_repo())
    response = client.get("/probe", headers={"x-user-role": "vendor_manager"})
    assert response.status_code == 400


def test_non_int_vendor_id_400() -> None:
    client = _make_app(_seed_repo())
    response = client.get("/probe", headers={"x-user-role": "vendor_manager", "x-vendor-id": "abc"})
    assert response.status_code == 400


def test_unknown_vendor_id_404() -> None:
    client = _make_app(_seed_repo())
    response = client.get("/probe", headers={"x-user-role": "vendor_manager", "x-vendor-id": "999"})
    assert response.status_code == 404


def test_unapproved_vendor_403_with_specific_code() -> None:
    client = _make_app(_seed_repo(status="pending"))
    response = client.get("/probe", headers={"x-user-role": "vendor_manager", "x-vendor-id": "42"})
    assert response.status_code == 403
    assert response.json()["code"] == "vendor_not_approved"
