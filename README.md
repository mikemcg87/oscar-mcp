# oscar-mcp

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants **read-only**
access to your OSCAR CPAP therapy data.

Ask Claude (or Cursor, or pi):

> *"How has my therapy been over the last 30 nights, and is anything being missed?"*

…and it can actually read your data instead of guessing. OSCAR 2.x keeps every profile in a
single SQLite database (`oscar.db`); this server opens that file **read-only** and exposes
it as a small, focused set of tools and prompts.

> **Not affiliated with the OSCAR project**, and **not medical advice**. See
> [Safety](#safety).

## Why

OSCAR stores a lot — nightly AHI/RDI, apnoea/hypopnoea/RERA counts, leak, pressure, SpO₂ —
but you have to go digging. This puts it one question away, and adds a nudge toward
**UARS / flow-limitation**, which plain AHI-based reports routinely miss.

## Tools

| Tool | What it returns |
|---|---|
| `oscar_status` | Whether a database was found, its path, and the profiles in it |
| `list_profiles` | Profiles (people) in the database |
| `list_machines` | Imported machines for a profile |
| `data_range` | Span of nights with data |
| `daily_summary(date)` | One night's metrics (AHI, RDI, hours, leak, pressure, SpO₂) |
| `therapy_trend(days)` | Averages over recent nights, plus adherence / leak / residual-AHI / UARS flags |
| `event_breakdown(date)` | Event counts by type for one night |
| `list_channels` | Data channels (signals) available |

Plus two **prompts** — `assess_therapy` and `review_for_uars` — that frame a review for the
assistant.

## Requirements

- Python 3.10+
- **OSCAR 2.x** data (`oscar.db`). The 1.x file-based layout is not supported.

## Install

```bash
git clone https://github.com/mikemcg87/oscar-mcp.git
cd oscar-mcp
python3 -m venv .venv
./.venv/bin/pip install -e .
```

The server finds your database automatically at `~/Documents/OSCAR20_Data/oscar.db`.
Override with the `OSCAR_DB_PATH` environment variable.

## Configure

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "oscar": {
      "command": "/absolute/path/to/oscar-mcp/.venv/bin/oscar-mcp"
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add oscar -- /absolute/path/to/oscar-mcp/.venv/bin/oscar-mcp
```

**Cursor** — the same `mcpServers` block in `~/.cursor/mcp.json`.

**pi** — manage servers with the `pi mcp` command (see `pi mcp --help`).

If your database is not in the default location, pass it in the `env` block:

```json
"env": { "OSCAR_DB_PATH": "/Users/you/Documents/OSCAR20_Data/oscar.db" }
```

## How it works

- Reads a single local file (`oscar.db`) over **stdio**. No network, no telemetry, nothing
  leaves your machine.
- The database is opened with SQLite `mode=ro` **and** `PRAGMA query_only = ON`, so the
  server cannot modify your therapy data.
- The tools only run the queries you ask for; there is no arbitrary SQL entry point.

## Safety

- **Not medical advice.** The flags it computes (residual AHI, leak, RERA/UARS hints) are
  conventional starting points to prompt a closer look — not a diagnosis or a treatment
  plan. Discuss any change with a clinician.
- Therapy data is sensitive. The server sends none of it anywhere by itself; note only that
  whatever you then ask your AI assistant is subject to *that* assistant's own handling.

## Development

```bash
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pytest
```

The tests build a synthetic `oscar.db` from `tests/schema.sql` (a faithful subset of
OSCAR's schema v19), so they run anywhere with **no patient data**.
`test_protocol.py` spawns the server over real stdio and exercises the MCP handshake —
initialise, list tools/prompts, call a tool.

## License

GPL-3.0-or-later, matching the OSCAR ecosystem.
