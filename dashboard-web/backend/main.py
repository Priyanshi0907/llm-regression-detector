"""
Thin read-only API layer over the existing eval pipeline. Reuses src/storage.py,
src/comparison.py, src/drift.py, and src/explain.py directly rather than
reimplementing any logic — this backend is a view, not a second source of truth.

Run with: uvicorn dashboard-web.backend.main:app --reload --port 8000
(run from the project root so `src` resolves)
"""
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from src import storage
from src.config import settings
from src.comparison import compare_runs
from src.drift import check_drift
from src.explain import explain_failure, explain_verdict, short_reason
from src.dataset_importer import import_dataset, DatasetImportError

app = FastAPI(title="LLM Regression Detector API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()


def _run_dict(r):
    return r.model_dump()


def _case_dict(c):
    d = c.model_dump()
    d["failure_reason"] = short_reason(c)
    d["failure_explanation"] = explain_failure(c)
    return d


@app.get("/api/meta")
def meta():
    from src.providers.registry import SUPPORTED_PROVIDERS, default_model_for
    from src.judge import load_rubric
    return {
        "mock_mode": settings.mock_mode or not settings.openai_api_key,
        "llm_model": settings.llm_model,
        "llm_provider": settings.llm_provider,
        "judge_model": settings.judge_model,
        "judge_provider": settings.judge_provider,
        "supported_providers": SUPPORTED_PROVIDERS,
        "provider_availability": {p: bool(_provider_has_key(p)) for p in SUPPORTED_PROVIDERS},
        "semantic_similarity_enabled": settings.semantic_similarity_enabled,
        "warning_threshold_pct": settings.warning_threshold_pct,
        "critical_threshold_pct": settings.critical_threshold_pct,
        "drift_window": settings.drift_window,
        "drift_threshold_pct": settings.drift_threshold_pct,
        "slack_configured": bool(settings.slack_webhook_url),
        "discord_configured": bool(settings.discord_webhook_url),
        "email_configured": bool(settings.email_smtp_host and settings.email_from and settings.email_to),
        "rubric": load_rubric(),
    }


def _provider_has_key(name: str) -> bool:
    return {
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "gemini": bool(settings.gemini_api_key),
    }.get(name, False)


@app.get("/api/runs")
def list_runs(limit: int = 1000):
    runs = storage.get_all_runs(limit=limit)
    return [_run_dict(r) for r in reversed(runs)]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _run_dict(run)


@app.get("/api/runs/{run_id}/cases")
def get_run_cases(run_id: str):
    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    cases = storage.get_case_results(run_id)
    return [_case_dict(c) for c in cases]


@app.get("/api/overview")
def overview():
    """Everything the Overview page needs in one call: latest run, baseline
    comparison, drift status, and the regression/improvement diff list."""
    runs = storage.get_all_runs(limit=1000)
    if not runs:
        return {"has_data": False}

    latest = runs[-1]
    baseline = runs[-2] if len(runs) > 1 else None
    latest_cases = storage.get_case_results(latest.run_id)
    baseline_cases = storage.get_case_results(baseline.run_id) if baseline else None
    comparison = compare_runs(latest_cases, baseline_cases) if baseline else None
    drift = check_drift(runs)

    baseline_by_id = {c.case_id: c for c in baseline_cases} if baseline_cases else {}

    regressions = []
    improvements = []
    if comparison:
        for c in comparison.regressions:
            cur = next((cc for cc in latest_cases if cc.case_id == c.case_id), None)
            base = baseline_by_id.get(c.case_id)
            regressions.append({
                "case_id": c.case_id, "input": c.input, "expected_category": c.expected_category,
                "previous_category": c.previous_category, "new_category": c.new_category,
                "previous_summary_score": c.previous_summary_score, "new_summary_score": c.new_summary_score,
                "previous_summary": base.actual_summary if base else None,
                "new_summary": cur.actual_summary if cur else None,
                "verdict": explain_verdict(base, cur) if cur else None,
                "confidence_delta": (cur.confidence - base.confidence) if (cur and base) else 0.0,
                "latency_delta": (cur.latency_ms - base.latency_ms) if (cur and base) else 0.0,
                "tokens_delta": (cur.tokens_used - base.tokens_used) if (cur and base) else 0,
                "summary_score_delta": (cur.summary_score - base.summary_score) if (cur and base) else 0.0,
            })
        for c in comparison.improvements:
            improvements.append({
                "case_id": c.case_id, "input": c.input, "expected_category": c.expected_category,
                "previous_category": c.previous_category, "new_category": c.new_category,
                "previous_summary_score": c.previous_summary_score, "new_summary_score": c.new_summary_score,
            })

    return {
        "has_data": True,
        "latest": _run_dict(latest),
        "baseline": _run_dict(baseline) if baseline else None,
        "comparison": {
            "overall_accuracy_delta": comparison.overall_accuracy_delta,
            "category_accuracy_delta": comparison.category_accuracy_delta,
            "no_change_count": comparison.no_change_count,
            "p_value": comparison.p_value,
            "statistically_significant": comparison.statistically_significant,
            "status": comparison.status,
        } if comparison else None,
        "regressions": regressions,
        "improvements": improvements,
        "drift": {
            "is_drifting": drift.is_drifting,
            "current_moving_avg": drift.current_moving_avg,
            "reference_avg": drift.reference_avg,
            "delta_pct": drift.delta_pct,
            "window": drift.window,
            "message": drift.message,
        } if drift else None,
        "total_runs": len(runs),
    }


@app.get("/api/compare")
def compare(run_a: str, run_b: str):
    a = storage.get_run(run_a)
    b = storage.get_run(run_b)
    if not a or not b:
        raise HTTPException(404, "One or both runs not found")
    a_cases = storage.get_case_results(run_a)
    b_cases = storage.get_case_results(run_b)
    cmp = compare_runs(b_cases, a_cases)
    return {
        "run_a": _run_dict(a),
        "run_b": _run_dict(b),
        "regressions": len(cmp.regressions),
        "improvements": len(cmp.improvements),
        "p_value": cmp.p_value,
        "statistically_significant": cmp.statistically_significant,
    }


@app.get("/api/compare-multi")
def compare_multi(run_ids: str):
    """N-way comparison — the endpoint behind multi-provider side-by-side.
    run_ids is a comma-separated list; each run's raw metrics are returned
    together so the frontend can render a single table with one column per
    run (provider, prompt version, or both — whatever the caller selected)."""
    ids = [r.strip() for r in run_ids.split(",") if r.strip()]
    if len(ids) < 2:
        raise HTTPException(400, "Provide at least 2 run_ids")
    runs = []
    for rid in ids:
        r = storage.get_run(rid)
        if not r:
            raise HTTPException(404, f"Run not found: {rid}")
        runs.append(_run_dict(r))
    return {"runs": runs}


class DatasetImportRequest(BaseModel):
    content: str  # raw file content (CSV or JSON text)
    filename: str  # used to detect .csv vs .json
    output_path: str = "golden_dataset/dataset_imported.json"
    merge_with: str | None = None
    dataset_version: str = "imported"


@app.post("/api/dataset/upload")
def upload_dataset(req: DatasetImportRequest):
    """Accepts raw file content over HTTP (rather than a filesystem path)
    so this works from a browser upload, not just the CLI. Writes a temp
    file so we can reuse the exact same validation path as the CLI
    importer — no duplicated parsing logic."""
    suffix = ".csv" if req.filename.lower().endswith(".csv") else ".json"
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(req.content)
        tmp_path = f.name

    try:
        summary = import_dataset(
            tmp_path, req.output_path,
            merge_with=req.merge_with, dataset_version=req.dataset_version,
        )
        return summary
    except DatasetImportError as e:
        raise HTTPException(400, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/drift")
def drift_detail():
    runs = storage.get_all_runs(limit=1000)
    drift = check_drift(runs)
    return {
        "runs": [_run_dict(r) for r in runs],
        "drift": {
            "is_drifting": drift.is_drifting,
            "current_moving_avg": drift.current_moving_avg,
            "reference_avg": drift.reference_avg,
            "delta_pct": drift.delta_pct,
            "window": drift.window,
            "message": drift.message,
        } if drift else None,
    }


@app.get("/api/prompts")
def list_prompts():
    prompts_dir = PROJECT_ROOT / "prompts"
    if not prompts_dir.exists():
        return []
    # Return paths as "prompts/v8.yaml" (not bare "v8.yaml") so they match
    # what run_evaluation()'s security check and src.cli --prompt expect.
    return sorted(f"prompts/{p.name}" for p in prompts_dir.glob("*.yaml"))


class RunEvalRequest(BaseModel):
    prompt_file: str


@app.post("/api/run-eval")
def run_evaluation(req: RunEvalRequest):
    import subprocess
    # Ensure the path is inside prompts directory for security
    prompts_dir = (PROJECT_ROOT / "prompts").resolve()
    path = (PROJECT_ROOT / req.prompt_file).resolve()
    if not str(path).startswith(str(prompts_dir)):
        raise HTTPException(400, "Invalid prompt path")

    try:
        # Run under the active python interpreter
        python_exe = sys.executable
        # The main uvicorn process has cwd=dashboard-web/backend, so its env
        # vars (DATASET_PATH, RUBRIC_PATH, etc.) are set relative to that
        # (e.g. "../../golden_dataset/dataset_v1.json"). This subprocess runs
        # with cwd=PROJECT_ROOT instead (required for `python -m src.cli` to
        # resolve), so those same relative values would point two levels too
        # high. Override them here to be relative to PROJECT_ROOT directly.
        import os
        subprocess_env = os.environ.copy()
        subprocess_env["DATASET_PATH"] = "golden_dataset/dataset_v1.json"
        subprocess_env["RUBRIC_PATH"] = "golden_dataset/judge_rubric.yaml"
        subprocess_env["PROMPTS_DIR"] = "prompts"
        subprocess_env["DB_PATH"] = "data/eval_results.db"
        subprocess_env["REPORTS_DIR"] = "data/reports"

        result = subprocess.run(
            [python_exe, "-m", "src.cli", "--prompt", req.prompt_file, "--no-slack"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
            env=subprocess_env,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to run evaluation: {str(e)}")


@app.get("/api/prompts/{filename:path}")
def get_prompt_content(filename: str):
    try:
        clean_name = filename.replace("\\", "/").split("/")[-1]
        prompt_path = PROJECT_ROOT / "prompts" / clean_name
        if not prompt_path.exists():
            raise HTTPException(404, "Prompt template not found")
        return {"content": prompt_path.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/reports/{run_id}", response_class=HTMLResponse)
def get_report(run_id: str):
    import json as _json
    from src.report_generator import generate_report
    from src.drift import check_drift
    from src.comparison import compare_runs
    from src.cli import _build_trend_data

    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    # FIX: was Path("data/reports") — relative to cwd, which breaks on Render
    # since its working directory is dashboard-web/backend, not the project
    # root. PROJECT_ROOT is an absolute path computed from __file__, so this
    # resolves correctly regardless of where the process is launched from.
    reports_dir = PROJECT_ROOT / "data" / "reports"
    report_path = reports_dir / f"{run_id}.html"
    if report_path.exists():
        return HTMLResponse(content=report_path.read_text(encoding="utf-8"))

    # Build cases
    cases = storage.get_case_results(run_id)

    # Baseline & Comparison
    baseline_run = None
    comparison = None
    if run.baseline_run_id:
        baseline_run = storage.get_run(run.baseline_run_id)
        if baseline_run:
            baseline_cases = storage.get_case_results(run.baseline_run_id)
            comparison = compare_runs(cases, baseline_cases)

    # Drift
    all_runs = storage.get_all_runs(limit=1000)
    sorted_runs = sorted(all_runs, key=lambda r: r.timestamp)
    run_idx = next((i for i, r in enumerate(sorted_runs) if r.run_id == run_id), -1)

    drift = None
    if run_idx >= 0:
        drift_history = sorted_runs[:run_idx + 1]
        drift = check_drift(drift_history)

    # Trend Data
    history_chunk = sorted_runs[max(0, run_idx - 6):run_idx + 1] if run_idx >= 0 else sorted_runs[-7:]
    trend_data = _build_trend_data(history_chunk, settings.drift_window)

    # Generate HTML
    html = generate_report(
        run=run,
        baseline_run=baseline_run,
        current_cases=cases,
        comparison=comparison,
        drift=drift,
        trend_data=trend_data,
        dataset_version=settings.dataset_path
    )

    # Save cache
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Serve the built React app (dashboard-web/frontend/dist) if it exists, so
# `uvicorn dashboard-web.backend.main:app` alone is enough in production —
# no separate frontend dev server needed. In local development, run the
# Vite dev server instead (it proxies /api to this backend); this static
# mount is skipped automatically if `dist/` hasn't been built yet.
# ---------------------------------------------------------------------------
_dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=_dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        candidate = _dist_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist_dir / "index.html")