"""In-memory MenuCategoryRepository。

每筆都帶 vendor_id；所有 query 必須以 vendor_id scope，避免跨商家洩漏。
DB 接好後換成 SQL 實作；介面不變。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from itertools import count
from typing import Any

from backend.schemas.vendor_self import Category


@dataclass
class _CategoryRecord:
    id: int
    vendor_id: int
    name: str
    sort_order: int
    created_at: datetime


def _to_schema(rec: _CategoryRecord) -> Category:
    return Category(
        id=rec.id,
        vendor_id=rec.vendor_id,
        name=rec.name,
        sort_order=rec.sort_order,
        created_at=rec.created_at,
    )


class MenuCategoryRepository:
    def __init__(self) -> None:
        self._rows: dict[int, _CategoryRecord] = {}
        self._id_seq = count(1)

    def create(self, *, vendor_id: int, name: str, sort_order: int = 0) -> Category:
        new_id = next(self._id_seq)
        rec = _CategoryRecord(
            id=new_id,
            vendor_id=vendor_id,
            name=name,
            sort_order=sort_order,
            created_at=datetime.now(timezone.utc),
        )
        self._rows[new_id] = rec
        return _to_schema(rec)

    def list(self, *, vendor_id: int) -> list[Category]:
        rows = [r for r in self._rows.values() if r.vendor_id == vendor_id]
        rows.sort(key=lambda r: (r.sort_order, r.id))
        return [_to_schema(r) for r in rows]

    def get(self, *, vendor_id: int, category_id: int) -> Category | None:
        rec = self._rows.get(category_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        return _to_schema(rec)

    def update(self, *, vendor_id: int, category_id: int, fields: dict[str, Any]) -> Category | None:
        rec = self._rows.get(category_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        # 只覆寫 fields 裡有出現的鍵 (caller 應傳 model_dump(exclude_unset=True))。
        updated = replace(rec, **{k: v for k, v in fields.items() if v is not None})
        self._rows[category_id] = updated
        return _to_schema(updated)

    def delete(self, *, vendor_id: int, category_id: int) -> bool:
        rec = self._rows.get(category_id)
        if rec is None or rec.vendor_id != vendor_id:
            return False
        del self._rows[category_id]
        return True
