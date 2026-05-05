"""/vendor/me/menu — 菜單項目 CRUD + 照片 sub-resource。

Photo endpoints (PUT / DELETE /menu/{id}/photo) 在 Task 12 加入。
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response

from backend.core.vendor_identity import require_approved_vendor
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.routes.vendor_categories import get_menu_category_repository
from backend.schemas.vendor_self import MenuItem, MenuItemCreate, MenuItemUpdate, PhotoUploadResponse
from backend.services.vendor_menu_service import VendorMenuService
from backend.storage.photo_storage import PhotoStorage

router = APIRouter(prefix="/vendor/me/menu", tags=["vendor-self"])


# Photo storage 預設 root：production 由 docker volume mount。
_default_storage_root = Path("/app/uploads")
_storage = PhotoStorage(root=_default_storage_root)


def get_menu_item_repository() -> MenuItemRepository:
    """共用 vendor_categories 那邊的同一份 in-memory repo singleton。

    若兩條 route 各自 `MenuItemRepository()`，categories 的 409 檢查
    (has_items_in_category) 會看不到 menu route 建立的 item。
    """
    from backend.routes.vendor_categories import get_menu_item_repository_for_category

    return get_menu_item_repository_for_category()


def get_photo_storage() -> PhotoStorage:
    return _storage


def get_vendor_menu_service(
    item_repo: Annotated[MenuItemRepository, Depends(get_menu_item_repository)],
    cat_repo: Annotated[MenuCategoryRepository, Depends(get_menu_category_repository)],
    storage: Annotated[PhotoStorage, Depends(get_photo_storage)],
) -> VendorMenuService:
    return VendorMenuService(item_repo, cat_repo, storage)


@router.get("", response_model=list[MenuItem])
def list_menu(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
    category_id: Annotated[int | None, Query()] = None,
    available: Annotated[bool | None, Query()] = None,
) -> list[MenuItem]:
    """列出商家菜單；可用 category_id / available 篩選。"""
    return service.list(vendor_id, category_id=category_id, available=available)


@router.post("", response_model=MenuItem, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreate,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
) -> MenuItem:
    """新增菜單項目。daily_quota: None=不限, 0=暫停供應。"""
    return service.create(vendor_id, payload)


@router.get("/{item_id}", response_model=MenuItem)
def get_menu_item(
    item_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
) -> MenuItem:
    return service.get(vendor_id, item_id)


@router.patch("/{item_id}", response_model=MenuItem)
def patch_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
) -> MenuItem:
    """局部更新菜單項目。"""
    return service.update(vendor_id, item_id, payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
) -> Response:
    """刪除菜單項目；連帶刪除照片檔。"""
    service.delete(vendor_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{item_id}/photo", response_model=PhotoUploadResponse)
async def put_menu_photo(
    item_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
    file: UploadFile = File(...),
) -> PhotoUploadResponse:
    """上傳/覆蓋菜單項目照片 (multipart `file`)。

    Storage 層會強制重新編碼成 JPEG、限制 5MB、最長邊 1600px。
    PUT 語意 — idempotent，多次呼叫覆蓋既有照片。
    """
    data = await file.read()
    path = service.replace_photo(vendor_id=vendor_id, item_id=item_id, data=data)
    return PhotoUploadResponse(photo_path=path)


@router.delete("/{item_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_photo(
    item_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorMenuService, Depends(get_vendor_menu_service)],
) -> Response:
    """刪除菜單項目照片 (檔案 + DB 路徑都清空)；不存在不算錯。"""
    service.delete_photo(vendor_id=vendor_id, item_id=item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
