"""/vendor/me/profile — 商家自身資料讀寫。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.core.vendor_identity import (
    get_vendor_profile_repository,
    require_approved_vendor,
)
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.schemas.vendor_self import VendorProfile, VendorProfileUpdate
from backend.services.vendor_profile_service import VendorProfileService

router = APIRouter(prefix="/vendor/me", tags=["vendor-self"])


def get_vendor_profile_service(
    repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
) -> VendorProfileService:
    """DI factory — tests override 以注入 fake repo 後得到 fresh service。"""
    return VendorProfileService(repo)


@router.get("/profile", response_model=VendorProfile)
def get_profile(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorProfileService, Depends(get_vendor_profile_service)],
) -> VendorProfile:
    """取得目前登入商家的資料 (含唯讀的 served_facilities 廠區清單)。"""
    return service.get(vendor_id)


@router.patch("/profile", response_model=VendorProfile)
def patch_profile(
    payload: VendorProfileUpdate,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorProfileService, Depends(get_vendor_profile_service)],
) -> VendorProfile:
    """局部更新商家資料；served_facilities 等唯讀欄位若出現在 body 會被忽略。"""
    return service.update(vendor_id, payload)
