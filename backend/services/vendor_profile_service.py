"""商家自身資料的讀寫邏輯 (Profile)。

Route 不直接打 repository — 透過此 service 集中處理：
  - 將 repository record 轉成對外 schema (VendorProfile)
  - 處理 PATCH 的部分更新語意
  - 附加唯讀的 served_facilities 廠區清單
"""
from __future__ import annotations

from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.schemas.vendor_self import VendorProfile, VendorProfileUpdate


class VendorProfileService:
    def __init__(self, repository: VendorProfileRepository) -> None:
        self.repository = repository

    def get(self, vendor_id: int) -> VendorProfile:
        record = self.repository.get(vendor_id)
        # vendor_id 已由 require_approved_vendor 驗證存在；理論上不會 None。
        assert record is not None
        return VendorProfile(
            id=record.id,
            name=record.name,
            status=record.status,
            address=record.address,
            business_hours=record.business_hours,
            contact_phone=record.contact_phone,
            contact_email=record.contact_email,
            served_facilities=self.repository.list_facilities(vendor_id),
        )

    def update(self, vendor_id: int, payload: VendorProfileUpdate) -> VendorProfile:
        # exclude_unset：只有 client 真的送的欄位才會被更新。
        updates = payload.model_dump(exclude_unset=True)
        self.repository.update(vendor_id, updates)
        return self.get(vendor_id)
