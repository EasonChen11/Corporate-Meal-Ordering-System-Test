"""/vendor/me/categories — 菜單分類 CRUD。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from backend.core.vendor_identity import require_approved_vendor
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.schemas.vendor_self import Category, CategoryCreate, CategoryUpdate
from backend.services.vendor_category_service import VendorCategoryService

router = APIRouter(prefix="/vendor/me/categories", tags=["vendor-self"])


# Module-singleton repos：跟 vendor_identity 一樣，process 內共用 in-memory state。
# 測試以 app.dependency_overrides 注入新實例。
_category_repo = MenuCategoryRepository()
_item_repo_for_category = MenuItemRepository()


def get_menu_category_repository() -> MenuCategoryRepository:
    return _category_repo


def get_menu_item_repository_for_category() -> MenuItemRepository:
    """名字加 _for_category 是為了讓 routes/vendor_menu.py 也能擁有自己的 override key
    (兩條 route 共用同一份 repo，但測試可分別注入)。"""
    return _item_repo_for_category


def get_vendor_category_service(
    cat_repo: Annotated[MenuCategoryRepository, Depends(get_menu_category_repository)],
    item_repo: Annotated[MenuItemRepository, Depends(get_menu_item_repository_for_category)],
) -> VendorCategoryService:
    return VendorCategoryService(cat_repo, item_repo)


@router.get("", response_model=list[Category])
def list_categories(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorCategoryService, Depends(get_vendor_category_service)],
) -> list[Category]:
    """列出目前商家的所有分類，依 sort_order 升冪。"""
    return service.list(vendor_id)


@router.post("", response_model=Category, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorCategoryService, Depends(get_vendor_category_service)],
) -> Category:
    """新增分類。"""
    return service.create(vendor_id, payload)


@router.patch("/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorCategoryService, Depends(get_vendor_category_service)],
) -> Category:
    """局部更新分類 (name / sort_order)。"""
    return service.update(vendor_id, category_id, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorCategoryService, Depends(get_vendor_category_service)],
) -> Response:
    """刪除分類；底下若還有 menu item 會回 409 category_not_empty。"""
    service.delete(vendor_id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
