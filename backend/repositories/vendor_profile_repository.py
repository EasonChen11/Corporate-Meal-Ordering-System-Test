"""In-memory VendorProfileRepository.

實作為 process-local dict，僅供 skeleton / 測試 / 本機 demo 使用。
DB 接好後將此檔換成真正的 SQL 實作；route / service 介面不需更動。

`assign_facility` 在實際系統中由委員會模組寫入；這裡保留是給測試/seed 用。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from backend.schemas.vendor_self import Facility


@dataclass
class VendorRecord:
    id: int
    name: str
    status: str
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class VendorProfileRepository:
    def __init__(self) -> None:
        self._vendors: dict[int, VendorRecord] = {}
        # vendor_id -> list of Facility
        self._facilities: dict[int, list[Facility]] = {}

    # --- seed / write side (admin / committee in real life) ---

    def seed(self, record: VendorRecord) -> None:
        """測試 / 本機種子資料用。"""
        self._vendors[record.id] = record
        self._facilities.setdefault(record.id, [])

    def assign_facility(self, vendor_id: int, *, facility_id: int, code: str, name: str) -> None:
        """委員會模組 stub：把廠區指派給商家。"""
        self._facilities.setdefault(vendor_id, [])
        self._facilities[vendor_id].append(Facility(id=facility_id, code=code, name=name))

    # --- read / vendor-self side ---

    def get(self, vendor_id: int) -> VendorRecord | None:
        return self._vendors.get(vendor_id)

    def update(self, vendor_id: int, fields: dict[str, Any]) -> VendorRecord | None:
        existing = self._vendors.get(vendor_id)
        if existing is None:
            return None
        # 只覆寫 fields 裡實際出現的鍵 (caller 應傳 model_dump(exclude_unset=True))。
        merged = replace(existing, **fields)
        self._vendors[vendor_id] = merged
        return merged

    def list_facilities(self, vendor_id: int) -> list[Facility]:
        return list(self._facilities.get(vendor_id, []))
