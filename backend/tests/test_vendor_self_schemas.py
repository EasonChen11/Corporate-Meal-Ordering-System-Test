"""Schema validation rules for the vendor self-service surface."""
import pytest
from pydantic import ValidationError

from backend.schemas.vendor_self import (
    Facility,
    MenuItemCreate,
    MenuItemUpdate,
    VendorProfileUpdate,
)


def test_menu_item_create_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        MenuItemCreate(name="Rice", price_cents=-1)


def test_menu_item_create_rejects_negative_daily_quota() -> None:
    with pytest.raises(ValidationError):
        MenuItemCreate(name="Rice", price_cents=80, daily_quota=-3)


def test_menu_item_create_allows_null_daily_quota() -> None:
    item = MenuItemCreate(name="Rice", price_cents=80, daily_quota=None)
    assert item.daily_quota is None


def test_menu_item_create_allows_zero_daily_quota() -> None:
    """Zero = today temporarily unavailable (distinct from `available=False`)."""
    item = MenuItemCreate(name="Rice", price_cents=80, daily_quota=0)
    assert item.daily_quota == 0


def test_menu_item_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        MenuItemCreate(name="   ", price_cents=80)


def test_menu_item_update_all_fields_optional() -> None:
    update = MenuItemUpdate()
    assert update.model_dump(exclude_unset=True) == {}


def test_vendor_profile_update_silently_drops_served_facilities() -> None:
    """spec: PATCH ignores served_facilities in body — does not 422."""
    update = VendorProfileUpdate.model_validate({"name": "Newname", "served_facilities": [{"id": 1, "code": "X", "name": "X"}]})
    assert "served_facilities" not in update.model_dump(exclude_unset=True)


def test_facility_round_trip() -> None:
    f = Facility(id=1, code="F12A", name="Fab 12A")
    assert f.code == "F12A"
