"""Test fixtures: a synthetic OSCAR database built from the real schema.

Building the fixture from `schema.sql` (a faithful subset of OSCAR 2.x schema
v19) keeps the tests runnable anywhere, with no real patient data required.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from oscar_mcp import server

SCHEMA = Path(__file__).parent / "schema.sql"

# Four nights for one profile: a controlled night, a leaky night, a
# UARS-suggestive night (low AHI, RERAs), and a short/under-used night.
NIGHTS = [
    # date,        hours, ahi, rdi, rera, obs, hyp, leak95, p95,  spo2_min
    ("2026-09-01", 7.5, 1.2, 1.8, 0.2, 2, 5, 6.0, 12.0, 93),
    ("2026-09-02", 6.0, 3.1, 4.0, 0.6, 4, 9, 30.0, 13.5, 91),
    ("2026-09-03", 7.0, 2.0, 6.5, 3.0, 3, 6, 7.0, 12.5, 94),
    ("2026-09-04", 3.0, 4.0, 4.2, 0.5, 5, 7, 8.0, 12.2, 92),
]


@pytest.fixture()
def oscar_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "oscar.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA.read_text())
    conn.execute(
        "INSERT INTO profiles (id, username, data_folder, status) VALUES (1, 'tester', ?, 'active')",
        (str(tmp_path),),
    )
    conn.execute(
        "INSERT INTO machines (profile_id, machine_id, loader_name, machine_type, brand, model, "
        "series, serial_number, last_imported) VALUES (1, 42, 'ResMed', 0, 'ResMed', 'AirSense 11', "
        "'AirSense', 'SN123', '2026-09-04')"
    )
    conn.execute(
        "INSERT INTO channels (profile_id, channel_id, channel_code, type, fullname) "
        "VALUES (1, 1, 'CPAP_Pressure', 0, 'CPAP Pressure')"
    )
    for date, hours, ahi, rdi, rera, obs, hyp, leak95, p95, spo2 in NIGHTS:
        conn.execute(
            "INSERT INTO daily_summaries (profile_id, date, session_count, enabled_session_count, "
            "total_hours, mask_on_hours, ahi, rdi, obstructive_count, hypopnea_count, rera_count, "
            "all_apnea_count, pressure_avg, pressure_95th, leak_total_avg, leak_total_95th, "
            "spo2_avg, spo2_min, is_compliant) VALUES "
            "(1, ?, 1, 1, ?, ?, ?, ?, ?, ?, ?, ?, 11.4, ?, ?, ?, 96, ?, ?)",
            (
                date, hours, hours, ahi, rdi, obs, hyp, rera, obs + hyp,
                p95, leak95 - 1.0, leak95, spo2, 1 if hours >= 4 else 0,
            ),
        )
    conn.commit()
    conn.close()

    monkeypatch.setenv("OSCAR_DB_PATH", str(db_path))
    server._db = None  # drop any cached handle so the env var takes effect
    yield db_path
    server._db = None
