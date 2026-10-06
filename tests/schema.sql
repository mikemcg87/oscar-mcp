-- Minimal but faithful subset of the OSCAR 2.x SQLite schema, used only to build
-- test fixtures. Column names and types mirror oscar/database/database_schema.cpp
-- (schema v19). It is NOT the full schema: it contains just the tables and
-- columns the MCP tools read.

CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    data_folder TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'missing', 'archived')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    machine_id INTEGER NOT NULL,
    loader_name TEXT NOT NULL,
    machine_type INTEGER NOT NULL,
    brand TEXT,
    model TEXT,
    series TEXT,
    serial_number TEXT,
    model_number TEXT,
    last_imported TEXT,
    FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE CASCADE
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    machine_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER NOT NULL,
    duration INTEGER NOT NULL,
    enabled INTEGER DEFAULT 1,
    FOREIGN KEY (machine_id) REFERENCES machines (id) ON DELETE CASCADE
);

CREATE TABLE daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    session_count INTEGER DEFAULT 0,
    enabled_session_count INTEGER DEFAULT 0,
    total_hours REAL DEFAULT 0,
    mask_on_hours REAL DEFAULT 0,
    ahi REAL DEFAULT 0,
    rdi REAL DEFAULT 0,
    obstructive_count INTEGER DEFAULT 0,
    unclassified_count INTEGER DEFAULT 0,
    hypopnea_count INTEGER DEFAULT 0,
    rera_count INTEGER DEFAULT 0,
    clear_airway_count INTEGER DEFAULT 0,
    central_hypopnea_count INTEGER DEFAULT 0,
    all_apnea_count INTEGER DEFAULT 0,
    oahi REAL DEFAULT 0,
    cahi REAL DEFAULT 0,
    pressure_avg REAL,
    pressure_min REAL,
    pressure_max REAL,
    pressure_95th REAL,
    leak_total_avg REAL,
    leak_total_95th REAL,
    leak_unintentional_avg REAL,
    spo2_avg REAL,
    spo2_min REAL,
    pulse_avg REAL,
    pulse_min REAL,
    pulse_max REAL,
    is_compliant INTEGER DEFAULT 0,
    has_oximetry INTEGER DEFAULT 0,
    FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE CASCADE,
    UNIQUE (profile_id, date)
);

CREATE TABLE channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    channel_code TEXT NOT NULL,
    type INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    fullname TEXT,
    label TEXT,
    description TEXT,
    lower_threshold REAL,
    upper_threshold REAL,
    FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE CASCADE,
    UNIQUE (profile_id, channel_id)
);

CREATE TABLE respiratory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    profile_id INTEGER NOT NULL,
    channel_id INTEGER,
    event_type INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER NOT NULL,
    duration INTEGER NOT NULL,
    desaturation REAL,
    severity INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE CASCADE
);
