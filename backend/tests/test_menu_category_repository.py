"""In-memory MenuCategoryRepository — vendor-scoped CRUD."""
from backend.repositories.menu_category_repository import MenuCategoryRepository


def test_create_assigns_id_and_returns_record() -> None:
    repo = MenuCategoryRepository()
    cat = repo.create(vendor_id=1, name="Hot", sort_order=0)
    assert cat.id > 0
    assert cat.vendor_id == 1
    assert cat.name == "Hot"


def test_list_returns_only_caller_vendors_categories() -> None:
    repo = MenuCategoryRepository()
    repo.create(vendor_id=1, name="A")
    repo.create(vendor_id=1, name="B")
    repo.create(vendor_id=2, name="X")
    categories = repo.list(vendor_id=1)
    assert {c.name for c in categories} == {"A", "B"}


def test_get_returns_none_if_other_vendor() -> None:
    repo = MenuCategoryRepository()
    cat = repo.create(vendor_id=1, name="A")
    assert repo.get(vendor_id=2, category_id=cat.id) is None


def test_update_changes_name_and_sort_order() -> None:
    repo = MenuCategoryRepository()
    cat = repo.create(vendor_id=1, name="A", sort_order=0)
    updated = repo.update(vendor_id=1, category_id=cat.id, fields={"name": "B", "sort_order": 5})
    assert updated is not None
    assert updated.name == "B"
    assert updated.sort_order == 5


def test_delete_removes_record() -> None:
    repo = MenuCategoryRepository()
    cat = repo.create(vendor_id=1, name="A")
    assert repo.delete(vendor_id=1, category_id=cat.id) is True
    assert repo.get(vendor_id=1, category_id=cat.id) is None


def test_delete_unknown_returns_false() -> None:
    repo = MenuCategoryRepository()
    assert repo.delete(vendor_id=1, category_id=999) is False
