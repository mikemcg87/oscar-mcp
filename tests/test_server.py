"""Integration tests for the MCP tools against a synthetic OSCAR database."""
from __future__ import annotations

from oscar_mcp import server


def test_status_finds_database(oscar_db):
    out = server.oscar_status()
    assert out["found"] is True
    assert out["active_profile_id"] == 1
    assert out["nights"] == 4
    assert out["first_night"] == "2026-09-01"
    assert out["last_night"] == "2026-09-04"


def test_list_profiles_and_machines(oscar_db):
    assert [p["username"] for p in server.list_profiles()] == ["tester"]
    machines = server.list_machines()
    assert machines[0]["brand"] == "ResMed"
    assert machines[0]["model"] == "AirSense 11"


def test_data_range(oscar_db):
    out = server.data_range()
    assert out == {"profile_id": 1, "nights": 4, "first_night": "2026-09-01", "last_night": "2026-09-04"}


def test_daily_summary_hit_and_miss(oscar_db):
    hit = server.daily_summary("2026-09-03")
    assert hit["found"] is True
    assert hit["ahi"] == 2.0
    assert hit["rera_count"] == 3.0
    miss = server.daily_summary("2020-01-01")
    assert miss == {"date": "2020-01-01", "found": False}


def test_therapy_trend_flags_uars_night(oscar_db):
    out = server.therapy_trend(days=30)
    assert out["nights"] == 4
    joined = " ".join(out["flags"])
    assert "UARS" in joined          # 2026-09-03: low AHI but RERAs
    assert "leak" in joined          # 2026-09-02: high leak
    assert "under 4 h" in joined     # 2026-09-04: short night


def test_event_breakdown(oscar_db):
    out = server.event_breakdown("2026-09-01")
    assert out["found"] is True
    assert out["obstructive_count"] == 2
    assert out["hypopnea_count"] == 5


def test_list_channels(oscar_db):
    chans = server.list_channels()
    assert chans[0]["channel_code"] == "CPAP_Pressure"


def test_status_reports_when_db_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("OSCAR_DB_PATH", str(tmp_path / "nope.db"))
    server._db = None
    try:
        out = server.oscar_status()
        assert out["found"] is False
        assert "oscar.db" in out["detail"]
    finally:
        server._db = None
