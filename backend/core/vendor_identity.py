"""商家身份驗證 dependency。

集中以下三段檢查，避免每條 route 重複：
  1. 角色必須是 vendor_manager。
  2. 必須帶 `x-vendor-id` header 且可轉 int。
  3. 該 vendor 必須存在且 status=='approved'。

未來真正接 JWT 時只需改本檔；route 介面 (`Depends(require_approved_vendor)` 拿到 vendor_id) 不變。
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

from backend.core.errors import CodedHTTPException
from backend.repositories.vendor_profile_repository import VendorProfileRepository

# Module-singleton：production 模式下 process 內共用同一份 in-memory state。
# 測試以 app.dependency_overrides[get_vendor_profile_repository] 注入新實例。
_REPO_SINGLETON = VendorProfileRepository()


def get_vendor_profile_repository() -> VendorProfileRepository:
    """DI 切換點：測試覆寫此 callable 即可換成 fake/seeded repo。"""
    return _REPO_SINGLETON


def require_approved_vendor(
    repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
    x_user_role: Annotated[str | None, Header()] = None,
    x_vendor_id: Annotated[str | None, Header()] = None,
) -> int:
    if x_user_role != "vendor_manager":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="vendor role required")

    if x_vendor_id is None:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-vendor-id header missing")
    try:
        vendor_id = int(x_vendor_id)
    except ValueError as exc:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-vendor-id must be integer") from exc

    record = repo.get(vendor_id)
    if record is None:
        # 不洩漏存在性 vs 未授權差別 — 一律 404。
        raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
    if record.status != "approved":
        raise CodedHTTPException(status_code=403, code="vendor_not_approved", detail="vendor not approved")

    return vendor_id
