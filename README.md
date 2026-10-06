# oscar-mcp

An [MCP](https://modelcontextprotocol.io) server that gives AI assistants **read-only**
access to your OSCAR CPAP therapy data. Ask Claude (or Cursor, or pi) *"how has my therapy
been over the last 30 nights, and is anything being missed?"* — and it can actually read
your data instead of guessing.

OSCAR 2.x keeps every profile in a single SQLite database (`oscar.db`). This server opens
that file **read-only** and exposes it as a small, focused set of tools.

## Why

OSCAR stores a lot — nightly AHI/RDI, apnoea/hypopnoea/RERA counts, leak, pressure, SpO₂ —
but you have to go looking for it. This puts it one question away, and adds a nudge toward
**UARS / flow-limitation**, which plain AHI-based reports routinely miss.

## Tools

| Tool | What it returns |
|---|---|
| `oscar_status` | Whether a database was found, its path, and the profiles in it |
| `list_profiles` | Profiles (people) in the database |
| `list_machines` | Imported machines for a profile |
| `data_range` | Span of nights with data |
| `daily_summary(date)` | One night's metrics (AHI, RDI, hours, leak, pressure, SpO₂) |
| `therapy_trend(days)` | Averages over recent nights + adherence/leak/residual-AHI/UARS flags |
| `event_breakdown(date)` | Event counts by type for one night |
| `list_channels` | Data channels (signals) available |

Plus two **prompts** — `assess_therapy` and `review_for_uars` — that frame a review for the
assistant.

## Requirements

- Python 3.10+
- OSCAR 2.x data (`oscar.db`). The 1.x file-based layout is not supported.
- Nothing leaves your machine: the server reads a local file over stdio.

## Install

```bash
git clone <your-fork-url> oscar-mcp
cd oscar-mcp
python3 -m venv .venv
./.venv/bin/pip install -e .
```

The server finds your database automatically at `~/Documents/OSCAR20_Data/oscar.db`.
Override with the `OSCAR_DB_PATH` environment variable.

## Configure

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

**Cursor:** same `mcpServers` block in `~/.cursor/mcp.json`.

**pi:** manage servers with the `pi mcp` command (see `pi mcp --help`).

Set `OSCAR_DB_PATH` in the `env` block if your database is not in the default location:

```json
"env": { "OSCAR_DB_PATH": "/Users/you/Documents/OSCAR20_Data/oscar.db" }
```

## Safety

- The database is opened with SQLite `mode=ro` **and** `PRAGMA query_only = ON`. The server
  cannot write to your therapy data, even by mistake.
- It reads only the tables it needs and never runs a query you did not invoke.
- The flags it computes are conventional starting points, **not medical advice**.

## Development

```bash
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pytest
```

The tests build a synthetic `oscar.db` from `tests/schema.sql` (a faithful subset of
OSCAR's schema v19), so they run anywhere with no patient data — and `test_protocol.py`
spawns the server over real stdio and exercises the MCP handshake.

## License

GPL-3.0-or-later, matching the OSCAR ecosystem.
