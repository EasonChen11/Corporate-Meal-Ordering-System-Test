"""In-memory VendorProfileRepository — production stub until DB lands."""
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord


def test_get_returns_seeded_vendor() -> None:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice Bento", status="approved"))
    got = repo.get(1)
    assert got is not None
    assert got.name == "Alice Bento"
    assert got.status == "approved"


def test_get_unknown_returns_none() -> None:
    repo = VendorProfileRepository()
    assert repo.get(999) is None


def test_update_changes_only_provided_fields() -> None:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice", status="approved", address="Old"))
    updated = repo.update(1, {"address": "New"})
    assert updated is not None
    assert updated.address == "New"
    assert updated.name == "Alice"  # not provided → unchanged


def test_list_facilities_empty_by_default() -> None:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice", status="approved"))
    assert repo.list_facilities(1) == []


def test_assign_and_list_facilities() -> None:
    repo = VendorProfileRepository()
    repo.seed(VendorRecord(id=1, name="Alice", status="approved"))
    repo.assign_facility(1, facility_id=10, code="F12A", name="Fab 12A")
    repo.assign_facility(1, facility_id=11, code="F14B", name="Fab 14B")
    facilities = repo.list_facilities(1)
    assert {f.code for f in facilities} == {"F12A", "F14B"}
