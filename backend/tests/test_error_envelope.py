"""Verify the flat {detail, code} error envelope contract."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.errors import CodedHTTPException, install_error_handler


def _make_app() -> FastAPI:
    app = FastAPI()
    install_error_handler(app)

    @app.get("/boom")
    def boom() -> None:
        raise CodedHTTPException(status_code=403, code="vendor_not_approved", detail="vendor not approved")

    return app


def test_coded_exception_renders_flat_envelope() -> None:
    client = TestClient(_make_app())
    response = client.get("/boom")
    assert response.status_code == 403
    assert response.json() == {"detail": "vendor not approved", "code": "vendor_not_approved"}
