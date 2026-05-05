"""菜單分類 (Category) 的 vendor-scoped CRUD 邏輯。

刪除前以 MenuItemRepository.has_items_in_category 檢查；
若分類底下還有 menu item，service 層回 409 (`category_not_empty`)，
不依賴 DB FK 規則 (FK 是 last-resort backstop)。
"""
from __future__ import annotations

from backend.core.errors import CodedHTTPException
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.schemas.vendor_self import Category, CategoryCreate, CategoryUpdate


class VendorCategoryService:
    def __init__(
        self,
        category_repository: MenuCategoryRepository,
        menu_item_repository: MenuItemRepository,
    ) -> None:
        self.category_repository = category_repository
        self.menu_item_repository = menu_item_repository

    def list(self, vendor_id: int) -> list[Category]:
        return self.category_repository.list(vendor_id=vendor_id)

    def create(self, vendor_id: int, payload: CategoryCreate) -> Category:
        return self.category_repository.create(
            vendor_id=vendor_id,
            name=payload.name,
            sort_order=payload.sort_order,
        )

    def update(self, vendor_id: int, category_id: int, payload: CategoryUpdate) -> Category:
        fields = payload.model_dump(exclude_unset=True)
        updated = self.category_repository.update(
            vendor_id=vendor_id, category_id=category_id, fields=fields
        )
        if updated is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="category not found")
        return updated

    def delete(self, vendor_id: int, category_id: int) -> None:
        # 取得確認分類存在 (跨商家也回 404 — 不洩漏存在性)
        existing = self.category_repository.get(vendor_id=vendor_id, category_id=category_id)
        if existing is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="category not found")
        # 阻擋刪除有 item 引用的分類
        if self.menu_item_repository.has_items_in_category(vendor_id=vendor_id, category_id=category_id):
            raise CodedHTTPException(
                status_code=409,
                code="category_not_empty",
                detail="category still has menu items",
            )
        self.category_repository.delete(vendor_id=vendor_id, category_id=category_id)
