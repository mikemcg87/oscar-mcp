"""OSCAR MCP server — exposes CPAP therapy data to AI assistants, read-only.

The server wraps an OSCAR 2.x `oscar.db` (SQLite) and offers tools to inspect
profiles, machines, nights, and trends, plus prompts that frame a therapy
review and a UARS/flow-limitation review. It never writes.
"""
from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from . import analysis
from .db import Database, OscarNotFound

mcp = MCPServer("oscar-cpap")

# A single resolved database per process keeps every tool call cheap. Resolved
# lazily so the server still starts when no database exists yet (the tools then
# report the problem instead of crashing at import).
_db: Database | None = None


def _database() -> Database:
    global _db
    if _db is None:
        _db = Database.open()
    return _db


def _profile(profile_id: int | None) -> int:
    pid = profile_id if profile_id is not None else _database().active_profile_id()
    if pid is None:
        raise ValueError("No OSCAR profiles found in the database.")
    return pid


@mcp.tool()
def oscar_status() -> dict:
    """Report whether OSCAR data was found, and a quick summary of it."""
    try:
        db = _database()
    except OscarNotFound as exc:
        return {"found": False, "detail": str(exc)}
    profiles = db.query("SELECT id, username, status FROM profiles ORDER BY id")
    pid = db.active_profile_id()
    span = (
        db.query(
            "SELECT COUNT(*) AS nights, MIN(date) AS first, MAX(date) AS last "
            "FROM daily_summaries WHERE profile_id = ?",
            (pid,),
        )[0]
        if pid is not None
        else None
    )
    return {
        "found": True,
        "database": str(db.path),
        "profiles": [dict(p) for p in profiles],
        "active_profile_id": pid,
        "nights": span["nights"] if span else 0,
        "first_night": span["first"] if span else None,
        "last_night": span["last"] if span else None,
    }


@mcp.tool()
def list_profiles() -> list[dict]:
    """List the OSCAR profiles (people) in the database."""
    return [dict(r) for r in _database().query("SELECT id, username, status FROM profiles ORDER BY id")]


@mcp.tool()
def list_machines(profile_id: int | None = None) -> list[dict]:
    """List imported machines for a profile (defaults to the active profile)."""
    pid = _profile(profile_id)
    rows = _database().query(
        "SELECT brand, model, series, serial_number, model_number, loader_name, last_imported "
        "FROM machines WHERE profile_id = ? ORDER BY id",
        (pid,),
    )
    return [dict(r) for r in rows]


@mcp.tool()
def data_range(profile_id: int | None = None) -> dict:
    """Show the span of nights with data for a profile."""
    pid = _profile(profile_id)
    row = _database().query(
        "SELECT COUNT(*) AS nights, MIN(date) AS first_night, MAX(date) AS last_night "
        "FROM daily_summaries WHERE profile_id = ?",
        (pid,),
    )[0]
    return {"profile_id": pid, **dict(row)}


@mcp.tool()
def daily_summary(date: str, profile_id: int | None = None) -> dict:
    """Return one night's therapy metrics. `date` is OSCAR's YYYY-MM-DD night."""
    pid = _profile(profile_id)
    rows = _database().query(
        "SELECT * FROM daily_summaries WHERE profile_id = ? AND date = ?",
        (pid, date),
    )
    if not rows:
        return {"date": date, "found": False}
    return {"found": True, **analysis.day_summary(rows[0])}


@mcp.tool()
def therapy_trend(days: int = 30, profile_id: int | None = None) -> dict:
    """Average the most recent `days` nights: AHI, RDI, hours, leak, pressure, and flags."""
    pid = _profile(profile_id)
    rows = _database().query(
        "SELECT * FROM daily_summaries WHERE profile_id = ? ORDER BY date DESC LIMIT ?",
        (pid, max(1, days)),
    )
    rows = list(reversed(rows))  # oldest-first for the pure helper
    result = analysis.trend(rows)
    return {"profile_id": pid, **result}


@mcp.tool()
def event_breakdown(date: str, profile_id: int | None = None) -> dict:
    """Event counts for one night, by type, as OSCAR records them."""
    pid = _profile(profile_id)
    rows = _database().query(
        "SELECT obstructive_count, unclassified_count, hypopnea_count, rera_count, "
        "clear_airway_count, central_hypopnea_count, all_apnea_count, oahi, cahi "
        "FROM daily_summaries WHERE profile_id = ? AND date = ?",
        (pid, date),
    )
    if not rows:
        return {"date": date, "found": False}
    return {"found": True, "date": date, **dict(rows[0])}


@mcp.tool()
def list_channels(profile_id: int | None = None) -> list[dict]:
    """List the data channels (signals) available for a profile."""
    pid = _profile(profile_id)
    rows = _database().query(
        "SELECT channel_code, fullname, label, type, enabled, lower_threshold, upper_threshold "
        "FROM channels WHERE profile_id = ? ORDER BY channel_id",
        (pid,),
    )
    return [dict(r) for r in rows]


@mcp.prompt()
def assess_therapy(days: int = 30) -> str:
    """Frame a therapy-efficacy review for the assistant to perform."""
    return (
        f"You are helping a CPAP patient understand their therapy. Call therapy_trend({days}) "
        "and oscar_status(). Assess: (1) adherence, against the usual >=4 h/night line; "
        "(2) residual AHI and event mix; (3) leak, and whether it plausibly undermines pressure; "
        "(4) pressure adequacy from the 95th percentile. Be concrete, cite the numbers you read, "
        "and never present this as medical advice — suggest discussing changes with a clinician."
    )


@mcp.prompt()
def review_for_uars(date: str | None = None) -> str:
    """Frame a UARS / flow-limitation review, which plain AHI often misses."""
    target = f"daily_summary({date!r}) and event_breakdown({date!r})" if date else "therapy_trend(30)"
    return (
        "Assess for Upper Airway Resistance Syndrome (UARS), which standard AHI-based reports "
        f"frequently miss. Call {target}. Look for RERAs, a low-but-nonzero AHI, persistent "
        "flow-limitation signals, and symptoms the numbers do not capture. Report RERA index, "
        "AHI-RDI gap, and whether the pattern warrants a flow-limitation work-up. This is "
        "informational only, not a diagnosis."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
