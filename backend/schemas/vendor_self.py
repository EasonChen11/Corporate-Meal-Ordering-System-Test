"""Vendor 自助管理 API 的 Pydantic 模型。

集中放置 request / response schema，方便 route + service + test 共用。
若日後此檔超過 ~200 行可依資源拆分（profile / category / menu）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


# 所有 user-input 字串型欄位共用：去頭尾空白 + 至少 1 字元（避免純空白）。
NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Facility(BaseModel):
    """廠區 (committee 模組維護，vendor 端唯讀)。"""

    id: int
    code: str
    name: str


# -------- Profile --------


class VendorProfile(BaseModel):
    """商家自身資料 (含唯讀的 served_facilities 廠區清單)。"""

    id: int
    name: str
    status: str
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    served_facilities: list[Facility] = Field(default_factory=list)


class VendorProfileUpdate(BaseModel):
    """PATCH /vendor/me/profile body — 全欄位 optional。"""

    # extra='ignore' 讓 served_facilities 等唯讀欄位被默默忽略，不回 422。
    model_config = ConfigDict(extra="ignore")

    name: NonBlankStr | None = None
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


# -------- Categories --------


class Category(BaseModel):
    """菜單分類。"""

    id: int
    vendor_id: int
    name: str
    sort_order: int
    created_at: datetime


class CategoryCreate(BaseModel):
    """建立分類。"""

    name: NonBlankStr
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """局部更新分類；全欄位 optional。"""

    name: NonBlankStr | None = None
    sort_order: int | None = None


# -------- Menu items --------


class MenuItem(BaseModel):
    """菜單項目（回傳用）。"""

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


class MenuItemCreate(BaseModel):
    """建立菜單項目。

    `daily_quota`：None = 不限；0 = 暫停供應 (與 available=False 不同：保留份數設定意圖)。
    """

    name: NonBlankStr
    description: str | None = None
    price_cents: int = Field(ge=0)
    category_id: int | None = None
    available: bool = True
    daily_quota: int | None = Field(default=None, ge=0)


class MenuItemUpdate(BaseModel):
    """局部更新；全欄位 optional。"""

    name: NonBlankStr | None = None
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    category_id: int | None = None
    available: bool | None = None
    daily_quota: int | None = Field(default=None, ge=0)


class PhotoUploadResponse(BaseModel):
    """上傳圖片後回傳的路徑。"""

    photo_path: str
