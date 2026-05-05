"""Integration tier — runs against a real Postgres once the DB layer wires up.

These tests are marked `integration` and skipped by default in the unit run.
Enable with: pytest -m integration
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skip(reason="awaiting DB persistence wiring")]


def test_menu_crud_round_trip_against_real_db() -> None:
    """End-to-end: POST /vendor/me/menu → row in menu_items → GET → PATCH → DELETE."""
    raise AssertionError("implement once persistence layer lands")


def test_vendor_cascade_deletes_categories_and_items() -> None:
    """Deleting a vendor removes their menu_categories + menu_items rows."""
    raise AssertionError("implement once persistence layer lands")


def test_served_facilities_join_returned_in_profile() -> None:
    """vendor_facilities row → /vendor/me/profile shows it under served_facilities."""
    raise AssertionError("implement once persistence layer lands")


def test_photo_upload_orphan_cleanup_on_db_failure() -> None:
    """Simulated DB failure after file write must not leave an orphan file."""
    raise AssertionError("implement once persistence layer lands")
