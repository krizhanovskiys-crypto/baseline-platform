"""Tests for the Court Registry (Sprint 10.3 Phase 2 — Court Registry v1.0)."""
from backend.app.data.courts import COURTS_BY_ZONE, TENNIS_ZONES, get_courts_for_zone


def test_tennis_zones_derived_from_registry():
    """TENNIS_ZONES is the registry's key order — one source of truth."""
    assert TENNIS_ZONES == list(COURTS_BY_ZONE.keys())
    assert len(TENNIS_ZONES) == 8


def test_every_zone_has_seven_to_ten_courts():
    for zone, courts in COURTS_BY_ZONE.items():
        assert 7 <= len(courts) <= 10, f"{zone} has {len(courts)} courts"


def test_no_duplicate_courts_within_a_zone():
    for zone, courts in COURTS_BY_ZONE.items():
        assert len(courts) == len(set(courts)), f"{zone} has duplicate court names"


def test_get_courts_for_zone_returns_only_that_zones_courts():
    downtown = get_courts_for_zone("Downtown")
    etobicoke = get_courts_for_zone("West Toronto / Etobicoke")

    assert "Ramsden Park" in downtown
    assert "High Park" not in downtown  # belongs to a different zone

    assert "High Park" in etobicoke
    assert "Colonel Samuel Smith Park" in etobicoke


def test_get_courts_for_zone_unknown_zone_returns_empty_list():
    """An unrecognized zone (e.g. a stale pre-migration value) must not raise —
    it just has no registry courts to show; custom courts remain available."""
    assert get_courts_for_zone("Atlantis") == []


def test_get_courts_for_zone_returns_a_copy():
    """Callers must not be able to mutate the registry through the returned list."""
    courts = get_courts_for_zone("Downtown")
    courts.append("Fake Park")
    assert "Fake Park" not in COURTS_BY_ZONE["Downtown"]
