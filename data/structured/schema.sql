-- ============================================================
-- Yeşilvadi Municipality AI Assistant — SQLite Schema (Draft)
-- W1.4 · Course: AIC390 · Instructor: Huseyin Ulusoy
-- Sandbox only: no real data, no production connection.
-- All values are synthetic (R10).
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- departments
-- ------------------------------------------------------------
CREATE TABLE departments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    name_tr     TEXT    NOT NULL,
    name_en     TEXT    NOT NULL,
    sla_hours   INTEGER NOT NULL CHECK (sla_hours > 0),
    email       TEXT
);

-- ------------------------------------------------------------
-- neighborhoods
-- ------------------------------------------------------------
CREATE TABLE neighborhoods (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    district_zone TEXT    NOT NULL
        CHECK (district_zone IN ('north','south','east','west','central'))
);

-- ------------------------------------------------------------
-- tickets
-- ------------------------------------------------------------
CREATE TABLE tickets (
    ticket_id    TEXT    PRIMARY KEY
        CHECK (ticket_id GLOB 'YV-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    created_at   DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at   DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    channel      TEXT    NOT NULL
        CHECK (channel IN ('web','whatsapp','phone','email','walk-in')),
    language     TEXT    NOT NULL DEFAULT 'tr'
        CHECK (language IN ('tr','en')),
    category     TEXT    NOT NULL
        CHECK (category IN ('roads_sidewalks','street_lighting','waste_collection','water_sewer','parks_green','traffic_signals','permits_licensing','social_services','animals','noise_environment','other')),
    department_id    INTEGER NOT NULL REFERENCES departments(id),
    neighborhood_id  INTEGER REFERENCES neighborhoods(id),
    street       TEXT,
    description  TEXT    NOT NULL,
    urgency      TEXT    NOT NULL
        CHECK (urgency IN ('P1','P2','P3','P4')),
    status       TEXT    NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','in_progress','resolved','rejected')),
    citizen_ref  TEXT,               -- hashed, non-identifiable
    contact_last4 TEXT,              -- last 4 digits of phone
    duplicate_of TEXT REFERENCES tickets(ticket_id),
    staff_note   TEXT,
    resolved_at  DATETIME
);

-- Only confirmed complaints enter tickets. Draft creation does not write a ticket.
CREATE TABLE ticket_drafts (
    draft_id     TEXT PRIMARY KEY,
    created_at   DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    expires_at   DATETIME NOT NULL
);

CREATE TABLE ticket_updates (
    update_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id    TEXT NOT NULL REFERENCES tickets(ticket_id),
    created_at   DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    text         TEXT NOT NULL,
    source       TEXT NOT NULL CHECK (source IN ('citizen','agent','staff'))
);

CREATE TRIGGER tickets_updated_at_after_update
AFTER UPDATE ON tickets
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tickets SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')
    WHERE ticket_id = NEW.ticket_id;
END;

-- ------------------------------------------------------------
-- collection_schedule
-- ------------------------------------------------------------
CREATE TABLE collection_schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    neighborhood_id INTEGER NOT NULL REFERENCES neighborhoods(id),
    waste_type      TEXT    NOT NULL
        CHECK (waste_type IN ('general','recycling','organic','bulky')),
    weekday         TEXT    NOT NULL
        CHECK (weekday IN ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')),
    time_window     TEXT    NOT NULL  -- e.g. '07:00–10:00'
);

-- ------------------------------------------------------------
-- facilities
-- ------------------------------------------------------------
CREATE TABLE facilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT    NOT NULL
        CHECK (type IN ('park','library','social_center','health_clinic','recycling_point')),
    name            TEXT    NOT NULL,
    neighborhood_id INTEGER REFERENCES neighborhoods(id),
    opening_hours   TEXT,
    address         TEXT
);

-- ------------------------------------------------------------
-- fees_2026
-- ------------------------------------------------------------
CREATE TABLE fees_2026 (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code   TEXT    NOT NULL UNIQUE,
    service     TEXT    NOT NULL,       -- English
    service_tr  TEXT    NOT NULL,       -- Turkish
    amount_try  REAL    NOT NULL CHECK (amount_try >= 0),
    valid_from  DATE    NOT NULL,
    source_doc  TEXT
);

-- ------------------------------------------------------------
-- audit_log
-- ------------------------------------------------------------
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   TEXT    REFERENCES tickets(ticket_id),
    event_type  TEXT    NOT NULL
        CHECK (event_type IN ('created','status_change','duplicate_flagged','confirmed','rejected')),
    actor       TEXT    NOT NULL
        CHECK (actor IN ('agent','staff','citizen')),
    timestamp   DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    detail      TEXT
);

-- ============================================================
-- End of schema. No INSERT statements — sandbox data populated
-- separately via seed scripts (data/structured/seed_sandbox.sql).
-- ============================================================
