"""Unit tests for the pure analysis helpers (no DB, no MCP)."""
from __future__ import annotations

from oscar_mcp import analysis


def row(**kw):
    base = {k: None for k in analysis.DAILY_FIELDS}
    base.update(kw)
    return base


def test_day_summary_reduces_and_coerces():
    out = analysis.day_summary(row(date="2026-09-01", ahi=1.2, is_compliant=1))
    assert out["date"] == "2026-09-01"
    assert out["ahi"] == 1.2
    assert out["is_compliant"] is True  # int -> bool


def test_trend_empty():
    out = analysis.trend([])
    assert out["nights"] == 0
    assert out["averages"] == {}


def test_trend_averages_and_flags():
    rows = [
        row(date="2026-09-01", total_hours=7.5, ahi=1.0, rdi=1.2, rera_count=0.0,
            leak_total_95th=6.0, pressure_95th=12.0, spo2_min=93),
        row(date="2026-09-02", total_hours=3.0, ahi=4.0, rdi=6.5, rera_count=3.0,
            leak_total_95th=30.0, pressure_95th=13.5, spo2_min=91),
    ]
    out = analysis.trend(rows)
    assert out["nights"] == 2
    assert out["first_night"] == "2026-09-01"
    assert out["last_night"] == "2026-09-02"
    assert out["compliant_nights"] == 1
    assert out["averages"]["ahi"] == 2.5
    # AHI >= 5? no (2.5), but RERA + leak + usage should each flag
    joined = " ".join(out["flags"])
    assert "under 4 h" in joined
    assert "leak" in joined
    assert "UARS" in joined
