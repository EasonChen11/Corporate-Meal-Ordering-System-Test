"""In-memory MenuItemRepository。

Vendor-scoped 菜單項目儲存。所有 query 必須以 vendor_id scope。
DB 接好後換成 SQL 實作；介面不變。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import count
from typing import Any

from backend.schemas.vendor_self import MenuItem


@dataclass
class _ItemRecord:
    id: int
    vendor_id: int
    category_id: int | None
    name: str
    description: str | None
    price_cents: int
    available: bool
    daily_quota: int | None
    photo_path: str | None
    created_at: datetime
    updated_at: datetime


def _to_schema(rec: _ItemRecord) -> MenuItem:
    return MenuItem(
        id=rec.id,
        vendor_id=rec.vendor_id,
        category_id=rec.category_id,
        name=rec.name,
        description=rec.description,
        price_cents=rec.price_cents,
        available=rec.available,
        daily_quota=rec.daily_quota,
        photo_path=rec.photo_path,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


class MenuItemRepository:
    def __init__(self) -> None:
        self._rows: dict[int, _ItemRecord] = {}
        self._id_seq = count(1)

    def create(
        self,
        *,
        vendor_id: int,
        name: str,
        price_cents: int,
        description: str | None = None,
        category_id: int | None = None,
        available: bool = True,
        daily_quota: int | None = None,
    ) -> MenuItem:
        now = datetime.now(timezone.utc)
        rec = _ItemRecord(
            id=next(self._id_seq),
            vendor_id=vendor_id,
            category_id=category_id,
            name=name,
            description=description,
            price_cents=price_cents,
            available=available,
            daily_quota=daily_quota,
            photo_path=None,
            created_at=now,
            updated_at=now,
        )
        self._rows[rec.id] = rec
        return _to_schema(rec)

    def list(
        self,
        *,
        vendor_id: int,
        category_id: int | None = None,
        available: bool | None = None,
    ) -> list[MenuItem]:
        rows = [r for r in self._rows.values() if r.vendor_id == vendor_id]
        if category_id is not None:
            rows = [r for r in rows if r.category_id == category_id]
        if available is not None:
            rows = [r for r in rows if r.available == available]
        rows.sort(key=lambda r: r.id)
        return [_to_schema(r) for r in rows]

    def get(self, *, vendor_id: int, item_id: int) -> MenuItem | None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        return _to_schema(rec)

    def update(
        self, *, vendor_id: int, item_id: int, fields: dict[str, Any]
    ) -> MenuItem | None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        # `daily_quota=0` 是合法值 (暫停供應)，不能用 truthy 過濾；
        # `category_id=None` 也是合法 (取消分類)。所以不能 drop None — 用 sentinel：
        # 這裡 fields 只包含 client 真有送的鍵 (caller 已 exclude_unset)，故安全直接套用。
        merged = replace(rec, **fields, updated_at=datetime.now(timezone.utc))
        self._rows[item_id] = merged
        return _to_schema(merged)

    def delete(self, *, vendor_id: int, item_id: int) -> bool:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return False
        del self._rows[item_id]
        return True

    def set_photo_path(self, *, vendor_id: int, item_id: int, photo_path: str) -> None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return
        self._rows[item_id] = replace(rec, photo_path=photo_path, updated_at=datetime.now(timezone.utc))

    def clear_photo_path(self, *, vendor_id: int, item_id: int) -> None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return
        self._rows[item_id] = replace(rec, photo_path=None, updated_at=datetime.now(timezone.utc))

    def has_items_in_category(self, *, vendor_id: int, category_id: int) -> bool:
        return any(
            r.vendor_id == vendor_id and r.category_id == category_id
            for r in self._rows.values()
        )
