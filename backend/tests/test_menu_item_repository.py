"""In-memory MenuItemRepository — vendor-scoped CRUD + photo-path bookkeeping."""
from backend.repositories.menu_item_repository import MenuItemRepository


def test_create_assigns_id_and_defaults() -> None:
    repo = MenuItemRepository()
    item = repo.create(vendor_id=1, category_id=None, name="Rice", price_cents=80)
    assert item.id > 0
    assert item.available is True
    assert item.daily_quota is None
    assert item.photo_path is None


def test_list_filters_by_vendor() -> None:
    repo = MenuItemRepository()
    repo.create(vendor_id=1, name="A", price_cents=10)
    repo.create(vendor_id=2, name="B", price_cents=10)
    assert {i.name for i in repo.list(vendor_id=1)} == {"A"}


def test_list_filters_by_category() -> None:
    repo = MenuItemRepository()
    a = repo.create(vendor_id=1, category_id=10, name="A", price_cents=10)
    repo.create(vendor_id=1, category_id=20, name="B", price_cents=10)
    listed = repo.list(vendor_id=1, category_id=10)
    assert [i.id for i in listed] == [a.id]


def test_list_filters_by_available() -> None:
    repo = MenuItemRepository()
    a = repo.create(vendor_id=1, name="A", price_cents=10, available=True)
    repo.create(vendor_id=1, name="B", price_cents=10, available=False)
    listed = repo.list(vendor_id=1, available=True)
    assert [i.id for i in listed] == [a.id]


def test_get_returns_none_for_other_vendor() -> None:
    repo = MenuItemRepository()
    item = repo.create(vendor_id=1, name="A", price_cents=10)
    assert repo.get(vendor_id=2, item_id=item.id) is None


def test_update_partial_fields() -> None:
    repo = MenuItemRepository()
    item = repo.create(vendor_id=1, name="A", price_cents=10, daily_quota=50)
    updated = repo.update(vendor_id=1, item_id=item.id, fields={"daily_quota": 0})
    assert updated is not None
    assert updated.daily_quota == 0
    assert updated.name == "A"


def test_delete_removes_record() -> None:
    repo = MenuItemRepository()
    item = repo.create(vendor_id=1, name="A", price_cents=10)
    assert repo.delete(vendor_id=1, item_id=item.id) is True
    assert repo.get(vendor_id=1, item_id=item.id) is None


def test_set_and_clear_photo_path() -> None:
    repo = MenuItemRepository()
    item = repo.create(vendor_id=1, name="A", price_cents=10)
    repo.set_photo_path(vendor_id=1, item_id=item.id, photo_path="vendors/1/menu/1.jpg")
    assert repo.get(vendor_id=1, item_id=item.id).photo_path == "vendors/1/menu/1.jpg"
    repo.clear_photo_path(vendor_id=1, item_id=item.id)
    assert repo.get(vendor_id=1, item_id=item.id).photo_path is None


def test_has_items_in_category_true_and_false() -> None:
    repo = MenuItemRepository()
    repo.create(vendor_id=1, category_id=10, name="A", price_cents=10)
    assert repo.has_items_in_category(vendor_id=1, category_id=10) is True
    assert repo.has_items_in_category(vendor_id=1, category_id=99) is False
    assert repo.has_items_in_category(vendor_id=2, category_id=10) is False
