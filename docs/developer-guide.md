# Developer Guide

## Running in Docker

```bash
cp .env.example .env   # fill in real keys if not using mock mode
docker compose up eval-runner     # runs the eval once against v8
docker compose up dashboard       # Streamlit dashboard at http://localhost:8501
```

Or standalone:

```bash
docker build -t llm-eval .
docker run --env-file .env -v $(pwd)/data:/app/data llm-eval --prompt prompts/v8.yaml
```

---

## Extending this to your own LLM feature

1. Replace `src/llm_feature.py` with your feature's logic and I/O contract.
2. Update `src/models.py` if your output shape isn't
   `{category, summary}` — e.g. a different Pydantic model.
3. Rebuild the golden dataset for your feature's domain (same JSON shape,
   different `expected_*` fields, or extend `TestCase`).
4. Everything else — runner, scoring, diffing, drift, reports, alerts,
   both dashboards, CI — works unchanged, because they only depend on
   `CaseResult` and `EvalRun`, not on what the feature actually does.
5. If your feature needs a different judge rubric, edit
   `golden_dataset/judge_rubric.yaml` — no code changes.

---

## Local development notes

- Tests: `python tests/test_comparison.py` and
  `python tests/test_providers_and_import.py` (no pytest dependency
  required — run directly; both exit non-zero on failure so they're
  CI-friendly too).
- The Streamlit dashboard's Settings page has a "Run eval" button that
  shells out to the CLI for convenience — handy for demos, not a
  replacement for CI.
- `data/reports/latest.html` always points at the most recent report,
  regardless of run ID, for quick access during local iteration.
- The web dashboard backend exposes `GET /api/prompts/{filename}` to
  serve prompt template YAML contents — used by the Cases page to render
  the prompt under test inline next to each case's results.
- Prompt paths in the Settings dropdown use POSIX forward slashes
  (`prompts/v7.yaml`) on all platforms including Windows.
- The React frontend's pre-built `dist/` is committed so
  `uvicorn dashboard-web.backend.main:app` works standalone with zero
  Node install. Rebuild after frontend changes:
  `cd dashboard-web/frontend && npm install && npm run build`.

---

## Alert channels

All independently configurable in `.env` — set any subset:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_USER=...
EMAIL_SMTP_PASSWORD=...
EMAIL_TO=team@example.com
```

An unconfigured channel is silently skipped, not an error — you don't
need all three to use any one of them.
