"""
Database Layer — SQLite schema, initialization, and query utilities.
Full production-grade design with normalized tables, indexes, and views.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

import shutil
import tempfile

_BUNDLED_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "resume_analytics.db")


def _resolve_db_path() -> str:
    """Use the bundled DB directly if writable; otherwise copy it to /tmp
    once per cold start (needed on read-only filesystems like Vercel)."""
    base_dir = os.path.dirname(_BUNDLED_DB_PATH)
    if os.access(base_dir, os.W_OK):
        return _BUNDLED_DB_PATH
    tmp_path = os.path.join(tempfile.gettempdir(), "resume_analytics.db")
    if not os.path.exists(tmp_path):
        shutil.copy(_BUNDLED_DB_PATH, tmp_path)
    return tmp_path


DB_PATH = _resolve_db_path()

# ──────────────────────────────────────────────
# SCHEMA DDL
# ──────────────────────────────────────────────

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Candidates master table
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id        TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    phone               TEXT,
    location            TEXT,
    years_experience    INTEGER,
    current_role        TEXT,
    education_degree    TEXT,
    education_field     TEXT,
    education_university TEXT,
    graduation_year     INTEGER,
    gpa                 REAL,
    applied_date        TEXT,
    source              TEXT,
    status              TEXT DEFAULT 'Under Review',
    resume_text         TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

-- Skills dimension table
CREATE TABLE IF NOT EXISTS skills (
    skill_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name  TEXT UNIQUE NOT NULL,
    category    TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Candidate ↔ Skill mapping (many-to-many)
CREATE TABLE IF NOT EXISTS candidate_skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    TEXT NOT NULL,
    skill_id        INTEGER NOT NULL,
    proficiency     TEXT DEFAULT 'Intermediate',
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id),
    UNIQUE(candidate_id, skill_id)
);

-- Job descriptions
CREATE TABLE IF NOT EXISTS job_descriptions (
    job_id          TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    department      TEXT,
    min_experience  INTEGER,
    location        TEXT,
    salary_range    TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Required skills per job (many-to-many)
CREATE TABLE IF NOT EXISTS job_required_skills (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    skill_name  TEXT NOT NULL,
    is_required INTEGER DEFAULT 1,   -- 1 = required, 0 = preferred
    FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id)
);

-- Candidate ↔ Job matching scores (core analytics table)
CREATE TABLE IF NOT EXISTS match_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id        TEXT NOT NULL,
    job_id              TEXT NOT NULL,
    overall_score       REAL,
    skill_match_score   REAL,
    experience_score    REAL,
    education_score     REAL,
    matched_skills      TEXT,       -- JSON list
    missing_skills      TEXT,       -- JSON list
    extra_skills        TEXT,       -- JSON list
    recommendation      TEXT,       -- Shortlist / Review / Reject
    scored_at           TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id),
    FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id),
    UNIQUE(candidate_id, job_id)
);

-- Work experience history
CREATE TABLE IF NOT EXISTS work_experience (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    TEXT NOT NULL,
    company         TEXT,
    title           TEXT,
    start_date      TEXT,
    end_date        TEXT,
    duration_years  INTEGER,
    description     TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    TEXT NOT NULL,
    project_name    TEXT,
    skills_used     TEXT,   -- JSON list
    impact          TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);

-- Certifications
CREATE TABLE IF NOT EXISTS certifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    TEXT NOT NULL,
    cert_name       TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);

-- Audit / event log for pipeline tracking
CREATE TABLE IF NOT EXISTS pipeline_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT,       -- e.g., 'resume_ingested', 'score_computed'
    entity_id   TEXT,
    details     TEXT,       -- JSON
    logged_at   TEXT DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────
-- INDEXES for query performance
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cand_status     ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_cand_location   ON candidates(location);
CREATE INDEX IF NOT EXISTS idx_cand_exp        ON candidates(years_experience);
CREATE INDEX IF NOT EXISTS idx_match_job       ON match_scores(job_id);
CREATE INDEX IF NOT EXISTS idx_match_score     ON match_scores(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_cand_skills     ON candidate_skills(candidate_id);
CREATE INDEX IF NOT EXISTS idx_skill_name      ON skills(skill_name);

-- ──────────────────────────────────────────────
-- VIEWS for fast analytics queries
-- ──────────────────────────────────────────────

CREATE VIEW IF NOT EXISTS v_candidate_summary AS
SELECT
    c.candidate_id,
    c.name,
    c.current_role,
    c.years_experience,
    c.location,
    c.status,
    c.source,
    c.applied_date,
    COUNT(DISTINCT cs.skill_id)                     AS total_skills,
    ROUND(AVG(ms.overall_score), 2)                 AS avg_match_score,
    MAX(ms.overall_score)                           AS best_match_score
FROM candidates c
LEFT JOIN candidate_skills cs ON c.candidate_id = cs.candidate_id
LEFT JOIN match_scores ms     ON c.candidate_id = ms.candidate_id
GROUP BY c.candidate_id;

CREATE VIEW IF NOT EXISTS v_job_skill_demand AS
SELECT
    jr.skill_name,
    COUNT(DISTINCT jr.job_id)   AS jobs_requiring,
    SUM(jr.is_required)         AS required_count,
    SUM(1 - jr.is_required)     AS preferred_count
FROM job_required_skills jr
GROUP BY jr.skill_name
ORDER BY jobs_requiring DESC;

CREATE VIEW IF NOT EXISTS v_skill_gap_analysis AS
SELECT
    jrs.skill_name,
    jrs.job_id,
    jd.title                                            AS job_title,
    COUNT(DISTINCT c.candidate_id)                      AS total_candidates,
    SUM(CASE WHEN s.skill_name IS NOT NULL THEN 1 ELSE 0 END) AS candidates_with_skill,
    ROUND(
        100.0 * SUM(CASE WHEN s.skill_name IS NOT NULL THEN 1 ELSE 0 END) / COUNT(DISTINCT c.candidate_id),
        1
    )                                                   AS skill_coverage_pct
FROM job_required_skills jrs
JOIN job_descriptions jd    ON jrs.job_id = jd.job_id
CROSS JOIN candidates c
LEFT JOIN candidate_skills cs ON c.candidate_id = cs.candidate_id
LEFT JOIN skills s ON cs.skill_id = s.skill_id AND LOWER(s.skill_name) = LOWER(jrs.skill_name)
GROUP BY jrs.skill_name, jrs.job_id;

CREATE VIEW IF NOT EXISTS v_hiring_funnel AS
SELECT
    status,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM candidates
GROUP BY status;

CREATE VIEW IF NOT EXISTS v_source_effectiveness AS
SELECT
    source,
    COUNT(*)                            AS total_applications,
    SUM(CASE WHEN status = 'Shortlisted' OR status = 'Interview Scheduled' OR status = 'Offer Extended' THEN 1 ELSE 0 END) AS qualified,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'Shortlisted' OR status = 'Interview Scheduled' OR status = 'Offer Extended' THEN 1 ELSE 0 END) / COUNT(*),
        1
    )   AS conversion_rate_pct,
    ROUND(AVG(ms.overall_score), 2) AS avg_match_quality
FROM candidates c
LEFT JOIN match_scores ms ON c.candidate_id = ms.candidate_id
GROUP BY source
ORDER BY qualified DESC;
"""


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a configured SQLite connection."""
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    except OSError:
        pass  # read-only filesystem (e.g. Vercel) — directory already exists
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass  # can't write -wal/-shm files on read-only filesystem, safe to skip for read-only dashboard use
    return conn


def initialize_db(db_path: str = DB_PATH) -> None:
    """Create all tables, indexes, and views."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at: {db_path}")


def log_event(conn: sqlite3.Connection, event_type: str, entity_id: str, details: dict) -> None:
    conn.execute(
        "INSERT INTO pipeline_log (event_type, entity_id, details) VALUES (?, ?, ?)",
        (event_type, entity_id, json.dumps(details))
    )


def fetch_all(query: str, params: tuple = (), db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_one(query: str, params: tuple = (), db_path: str = DB_PATH) -> Optional[dict]:
    conn = get_connection(db_path)
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None


if __name__ == "__main__":
    initialize_db()
