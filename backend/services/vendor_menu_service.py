"""菜單項目 CRUD + 照片資源管理。

照片實際 IO 委派給 PhotoStorage；本 service 只負責：
  - 驗證 category_id 屬於同商家 (避免跨商家透過 FK 偷塞)
  - 422 / 404 等錯誤包裝
  - 寫照片成功後 set_photo_path 回 repo；刪 item 時連帶刪檔。
"""
from __future__ import annotations

from backend.core.errors import CodedHTTPException
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.schemas.vendor_self import MenuItem, MenuItemCreate, MenuItemUpdate
from backend.storage.photo_storage import PhotoStorage


class VendorMenuService:
    def __init__(
        self,
        menu_item_repository: MenuItemRepository,
        category_repository: MenuCategoryRepository,
        photo_storage: PhotoStorage,
    ) -> None:
        self.menu_item_repository = menu_item_repository
        self.category_repository = category_repository
        self.photo_storage = photo_storage

    # --- query ---

    def list(
        self, vendor_id: int, *, category_id: int | None = None, available: bool | None = None
    ) -> list[MenuItem]:
        return self.menu_item_repository.list(
            vendor_id=vendor_id, category_id=category_id, available=available
        )

    def get(self, vendor_id: int, item_id: int) -> MenuItem:
        item = self.menu_item_repository.get(vendor_id=vendor_id, item_id=item_id)
        if item is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="menu item not found")
        return item

    # --- mutate ---

    def create(self, vendor_id: int, payload: MenuItemCreate) -> MenuItem:
        if payload.category_id is not None:
            self._assert_category_belongs_to(vendor_id, payload.category_id)
        return self.menu_item_repository.create(
            vendor_id=vendor_id,
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            category_id=payload.category_id,
            available=payload.available,
            daily_quota=payload.daily_quota,
        )

    def update(self, vendor_id: int, item_id: int, payload: MenuItemUpdate) -> MenuItem:
        # 確保 item 屬於 caller (避免讓 update 變成跨商家寫入)
        self.get(vendor_id, item_id)
        fields = payload.model_dump(exclude_unset=True)
        if "category_id" in fields and fields["category_id"] is not None:
            self._assert_category_belongs_to(vendor_id, fields["category_id"])
        updated = self.menu_item_repository.update(
            vendor_id=vendor_id, item_id=item_id, fields=fields
        )
        # update 已先 get 過，updated 不應為 None。
        assert updated is not None
        return updated

    def delete(self, vendor_id: int, item_id: int) -> None:
        # 連帶刪除檔案 (best-effort)；先刪檔再刪 row 避免 row 沒了但檔還在。
        self.get(vendor_id, item_id)
        self.photo_storage.delete_menu_photo(vendor_id=vendor_id, item_id=item_id)
        self.menu_item_repository.delete(vendor_id=vendor_id, item_id=item_id)

    # --- photo sub-resource (used by Task 12) ---

    def replace_photo(self, vendor_id: int, item_id: int, data: bytes) -> str:
        self.get(vendor_id, item_id)  # ensure ownership before touching disk
        path = self.photo_storage.store_menu_photo(
            vendor_id=vendor_id, item_id=item_id, data=data
        )
        self.menu_item_repository.set_photo_path(
            vendor_id=vendor_id, item_id=item_id, photo_path=path
        )
        return path

    def delete_photo(self, vendor_id: int, item_id: int) -> None:
        self.get(vendor_id, item_id)
        self.photo_storage.delete_menu_photo(vendor_id=vendor_id, item_id=item_id)
        self.menu_item_repository.clear_photo_path(vendor_id=vendor_id, item_id=item_id)

    # --- helpers ---

    def _assert_category_belongs_to(self, vendor_id: int, category_id: int) -> None:
        if self.category_repository.get(vendor_id=vendor_id, category_id=category_id) is None:
            raise CodedHTTPException(
                status_code=422,
                code="validation_error",
                detail="category_id does not belong to this vendor",
            )
