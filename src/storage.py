"""
SQLite persistence layer. Zero-infrastructure, git-friendly, and plenty
fast for a golden dataset in the tens-to-low-hundreds of cases.

Two tables:
  runs         - one row per evaluation run (aggregate metrics)
  case_results - one row per (run, test case) pair (granular detail)
"""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.config import settings
from src.models import EvalRun, CaseResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    prompt_version TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT DEFAULT 'openai',
    baseline_run_id TEXT,
    timestamp TEXT NOT NULL,
    total_cases INTEGER,
    overall_accuracy REAL,
    category_accuracy TEXT,
    difficulty_breakdown TEXT,
    avg_summary_relevance REAL,
    avg_semantic_similarity REAL,
    avg_latency_ms REAL,
    avg_tokens REAL,
    avg_cost_usd REAL DEFAULT 0,
    status TEXT,
    regressions INTEGER,
    improvements INTEGER,
    no_change INTEGER,
    p_value REAL,
    statistically_significant INTEGER
);

CREATE TABLE IF NOT EXISTS case_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    input TEXT,
    expected_category TEXT,
    actual_category TEXT,
    expected_summary TEXT,
    actual_summary TEXT,
    expected_difficulty TEXT DEFAULT 'medium',
    category_match INTEGER,
    summary_score REAL,
    judge_rationale TEXT,
    semantic_similarity REAL,
    semantic_similarity_is_real INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0,
    latency_ms REAL,
    tokens_used INTEGER,
    passed INTEGER,
    error TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_case_results_run ON case_results(run_id);
"""


def _db_path() -> Path:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_conn():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection):
    """Lightweight forward-only migration: add any columns that a schema
    update introduced but an existing on-disk DB predates. Keeps the demo
    DB shipped in the repo compatible with schema changes."""
    case_cols = {row["name"] for row in conn.execute("PRAGMA table_info(case_results)")}
    if "confidence" not in case_cols:
        conn.execute("ALTER TABLE case_results ADD COLUMN confidence REAL DEFAULT 0")
    if "expected_difficulty" not in case_cols:
        conn.execute("ALTER TABLE case_results ADD COLUMN expected_difficulty TEXT DEFAULT 'medium'")
    if "judge_rationale" not in case_cols:
        conn.execute("ALTER TABLE case_results ADD COLUMN judge_rationale TEXT")
    if "semantic_similarity" not in case_cols:
        conn.execute("ALTER TABLE case_results ADD COLUMN semantic_similarity REAL")
    if "semantic_similarity_is_real" not in case_cols:
        conn.execute("ALTER TABLE case_results ADD COLUMN semantic_similarity_is_real INTEGER DEFAULT 0")

    run_cols = {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
    if "difficulty_breakdown" not in run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN difficulty_breakdown TEXT DEFAULT '{}'")
    if "avg_cost_usd" not in run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN avg_cost_usd REAL DEFAULT 0")
    if "provider" not in run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN provider TEXT DEFAULT 'openai'")
    if "avg_semantic_similarity" not in run_cols:
        conn.execute("ALTER TABLE runs ADD COLUMN avg_semantic_similarity REAL")


def save_run(run: EvalRun, case_results: list[CaseResult]):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO runs
               (run_id, prompt_version, model, provider, baseline_run_id, timestamp,
                total_cases, overall_accuracy, category_accuracy, difficulty_breakdown,
                avg_summary_relevance, avg_semantic_similarity, avg_latency_ms, avg_tokens,
                avg_cost_usd, status,
                regressions, improvements, no_change, p_value, statistically_significant)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run.run_id, run.prompt_version, run.model, run.provider, run.baseline_run_id, run.timestamp,
                run.total_cases, run.overall_accuracy, json.dumps(run.category_accuracy),
                json.dumps(run.difficulty_breakdown),
                run.avg_summary_relevance, run.avg_semantic_similarity, run.avg_latency_ms, run.avg_tokens,
                run.avg_cost_usd, run.status,
                run.regressions, run.improvements, run.no_change, run.p_value,
                int(run.statistically_significant),
            ),
        )
        conn.executemany(
            """INSERT INTO case_results
               (run_id, case_id, input, expected_category, actual_category,
                expected_summary, actual_summary, expected_difficulty, category_match, summary_score,
                judge_rationale, semantic_similarity, semantic_similarity_is_real,
                confidence, latency_ms, tokens_used, passed, error)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    run.run_id, cr.case_id, cr.input, cr.expected_category.value,
                    cr.actual_category.value if cr.actual_category else None,
                    cr.expected_summary, cr.actual_summary, cr.expected_difficulty.value,
                    int(cr.category_match),
                    cr.summary_score, cr.judge_rationale, cr.semantic_similarity,
                    int(cr.semantic_similarity_is_real),
                    cr.confidence, cr.latency_ms, cr.tokens_used,
                    int(cr.passed), cr.error,
                )
                for cr in case_results
            ],
        )


def get_latest_run(exclude_run_id: str | None = None) -> EvalRun | None:
    with get_conn() as conn:
        query = "SELECT * FROM runs"
        params = ()
        if exclude_run_id:
            query += " WHERE run_id != ?"
            params = (exclude_run_id,)
        query += " ORDER BY timestamp DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()
        return _row_to_run(row) if row else None


def get_run(run_id: str) -> EvalRun | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None


def get_all_runs(limit: int = 100) -> list[EvalRun]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY timestamp ASC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_run(r) for r in rows]


def get_case_results(run_id: str) -> list[CaseResult]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM case_results WHERE run_id = ?", (run_id,)
        ).fetchall()
        return [_row_to_case_result(r) for r in rows]


def _row_to_run(row: sqlite3.Row) -> EvalRun:
    d = dict(row)
    d["category_accuracy"] = json.loads(d["category_accuracy"] or "{}")
    d["difficulty_breakdown"] = json.loads(d.get("difficulty_breakdown") or "{}")
    d["statistically_significant"] = bool(d["statistically_significant"])
    return EvalRun(**d)


def _row_to_case_result(row: sqlite3.Row) -> CaseResult:
    d = dict(row)
    d.pop("id", None)
    d.pop("run_id", None)
    d["category_match"] = bool(d["category_match"])
    d["passed"] = bool(d["passed"])
    d["semantic_similarity_is_real"] = bool(d.get("semantic_similarity_is_real", 0))
    return CaseResult(**d)
