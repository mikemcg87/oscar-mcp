"""Pure therapy-analysis helpers over OSCAR daily summaries.

Kept free of MCP and DB concerns so they can be unit-tested directly. Each
function takes plain mappings (sqlite3.Row or dict) and returns plain dicts.
"""
from __future__ import annotations

from statistics import mean
from typing import Iterable, Mapping, Sequence

# Thresholds used for the coarse flags below. They are conventional starting
# points (AASM-ish), not clinical advice: the consumer is an AI assistant that
# should treat them as prompts to look closer, not verdicts.
COMPLIANCE_HOURS = 4.0          # a night counts as compliant at >= 4 h used
RESIDUAL_AHI_OK = 5.0           # treated AHI under this is considered controlled
LEAK_HIGH = 24.0                # L/min, a common "large leak" ballpark
RERA_PROMINENT = 1.0            # RERA/h where flow-limitation work-up is worth it

DAILY_FIELDS = (
    "date", "session_count", "enabled_session_count", "total_hours", "mask_on_hours",
    "ahi", "rdi", "obstructive_count", "unclassified_count", "hypopnea_count",
    "rera_count", "clear_airway_count", "central_hypopnea_count", "all_apnea_count",
    "oahi", "cahi", "pressure_avg", "pressure_min", "pressure_max", "pressure_95th",
    "leak_total_avg", "leak_total_95th", "leak_unintentional_avg",
    "spo2_avg", "spo2_min", "pulse_avg", "pulse_min", "pulse_max",
    "is_compliant", "has_oximetry",
)


def _round(value: float | None, ndigits: int = 2) -> float | None:
    return None if value is None else round(value, ndigits)


def day_summary(row: Mapping) -> dict:
    """Shape one daily_summaries row into a stable, reduced dict."""
    out = {field: row[field] for field in DAILY_FIELDS if field in row.keys()}
    out["is_compliant"] = bool(out.get("is_compliant"))
    return out


def _average(rows: Sequence[Mapping], field: str) -> float | None:
    values = [row[field] for row in rows if row[field] is not None]
    return _round(mean(values)) if values else None


def trend(rows: Sequence[Mapping]) -> dict:
    """Aggregate a run of nights into averages, compliance, and coarse flags.

    `rows` must be ordered oldest-to-newest and share the profile.
    """
    if not rows:
        return {"nights": 0, "first_night": None, "last_night": None, "averages": {}, "flags": []}

    hours = [row["total_hours"] or 0.0 for row in rows]
    compliant = sum(1 for h in hours if h >= COMPLIANCE_HOURS)
    averages = {
        "ahi": _average(rows, "ahi"),
        "rdi": _average(rows, "rdi"),
        "total_hours": _round(mean(hours)),
        "mask_on_hours": _average(rows, "mask_on_hours"),
        "rera_count": _average(rows, "rera_count"),
        "pressure_avg": _average(rows, "pressure_avg"),
        "pressure_95th": _average(rows, "pressure_95th"),
        "leak_total_avg": _average(rows, "leak_total_avg"),
        "leak_total_95th": _average(rows, "leak_total_95th"),
        "spo2_avg": _average(rows, "spo2_avg"),
        "spo2_min": min((row["spo2_min"] for row in rows if row["spo2_min"] is not None), default=None),
    }

    flags: list[str] = []
    worst_leak = max(
        (row["leak_total_95th"] for row in rows if row["leak_total_95th"] is not None),
        default=None,
    )
    if compliant < len(hours):
        flags.append(
            f"{len(hours) - compliant}/{len(hours)} nights under {COMPLIANCE_HOURS:g} h "
            "(usage below the usual compliance line)"
        )
    if averages["ahi"] is not None and averages["ahi"] >= RESIDUAL_AHI_OK:
        flags.append(f"mean AHI {averages['ahi']} — residual events, therapy may be suboptimal")
    if worst_leak is not None and worst_leak >= LEAK_HIGH:
        # A single bad night matters more than an average that hides it.
        flags.append(
            f"peak 95th-percentile leak {_round(worst_leak)} L/min on at least one night "
            "— possible large leak"
        )
    if averages["rera_count"] is not None and averages["rera_count"] >= RERA_PROMINENT:
        flags.append(
            f"RERAs present (mean {averages['rera_count']}/night) with "
            f"AHI {averages['ahi']} — consider flow limitation / UARS"
        )

    return {
        "nights": len(rows),
        "first_night": rows[0]["date"],
        "last_night": rows[-1]["date"],
        "compliant_nights": compliant,
        "averages": averages,
        "flags": flags,
    }
