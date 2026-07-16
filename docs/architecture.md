# Architecture

## Data flow

```
Prompt/Model Change → GitHub Actions Triggered → Run Evaluation Pipeline → Generate Report & Compare → Alert (if regressions)
```

`prompts/*.yaml` + `golden_dataset/*.json` go into the eval runner,
results land in SQLite, and everything downstream (reports, both
dashboards, alerts) reads from SQLite. There's no hidden state — if a
number is on a dashboard, it came from a row in `data/eval_results.db`,
not a recomputation with different logic.

```
src/
  config.py            Environment-driven settings (single source of truth)
  models.py            Pydantic schemas shared by every module
  providers/           Multi-provider abstraction (OpenAI/Anthropic/Gemini/mock)
    base.py              Provider interface every adapter implements
    registry.py          get_provider(name) — real adapter or mock fallback
    openai_provider.py, anthropic_provider.py, gemini_provider.py
    mock_provider.py     Deterministic, provider-tagged mock for demos/CI
  judge.py             Configurable-rubric LLM-as-judge + semantic similarity
  llm_feature.py       The feature under test (email classifier)
  eval_runner.py       Async test runner, multi-dimensional scoring
  comparison.py        Diff logic + two-proportion z-test for significance
  drift.py             Rolling-average slow-drift detector
  storage.py           SQLite persistence (runs + case_results)
  report_generator.py  Self-contained HTML diff report (Jinja2 + Plotly)
  slack_alert.py, discord_alert.py, email_alert.py   Multi-channel alerting
  dataset_importer.py  CSV/JSON → golden dataset, with schema validation
  cli.py               Orchestrates all of the above, exits non-zero on FAIL

dashboard/app.py        Streamlit UI
dashboard-web/           React + FastAPI UI — same data, different presentation
prompts/*.yaml           Versioned prompt configs (the "code" under CI)
golden_dataset/*.json     Hand-labeled ground truth test cases
golden_dataset/judge_rubric.yaml   Configurable LLM-as-judge criteria + weights
.github/workflows/        GitHub Actions CI pipeline
```

---

## Design decisions & rationale

**Why diff against the *previous* run, not a fixed baseline?**
Because prompt engineering is iterative — you want to know if *this*
change made things worse than where you just were, not whether you've
regressed from six versions ago. `EvalRun.baseline_run_id` always points
at whatever the latest run was when this one started, so the diff is
always "what changed since last time."

**Why track slow drift separately from per-run regressions?**
Because a prompt can lose 1-2% on five consecutive small tweaks — each
one too small to trip the per-run threshold — and still end up materially
worse than where it started. A rolling moving average catches that
pattern; a single-run diff structurally cannot. This is the difference
between "did this PR break something" and "is quality trending down over
time," and teams that only check the former get surprised months later.

**Why SQLite instead of Postgres/a real eval platform?**
Zero infrastructure. This needs to run identically on a laptop, in
GitHub Actions, and in a container with no setup step. If you outgrow
SQLite (very large datasets, multiple concurrent writers), the storage
layer is isolated in `storage.py` — swap the connection logic without
touching the eval engine, scoring, or report generation. (This is also
the reason PostgreSQL is on the roadmap rather than already done — it's
a real tradeoff, not a missing checkbox.)

**Why LLM-as-judge for summary scoring instead of exact-match or ROUGE?**
Summaries are free text — there's no single correct phrasing. An
LLM-as-judge (or the mock content-overlap heuristic in mock mode) can
recognize that two differently-worded summaries mean the same thing,
which string-similarity metrics can't reliably do. The tradeoff is judge
cost/latency and occasional judge inconsistency, which is why category
accuracy (binary, unambiguous) is scored separately and weighted equally
in the pass/fail decision rather than folded into one fuzzy score. See
[`evaluation.md`](evaluation.md) for how the rubric and optional semantic
similarity score fit into this.

**Why block merge on FAIL but not on WARNING?**
A WARNING means something moved and a human should look at the diff
report before the next release. A FAIL means the regression is large
*and* statistically significant enough that shipping it blind is a bad
default. Teams that block on every WARNING train themselves to
routinely bypass CI; keeping FAIL rare and meaningful keeps the block
credible.

**Why a fixed judge provider regardless of which provider is under test?**
If Claude graded Claude's own outputs and GPT graded GPT's, a
multi-provider comparison would really be comparing two different judges,
not two different feature providers. `JUDGE_PROVIDER` is fixed
(default `openai`) so every provider is graded by the same judge.

---

## CI/CD (GitHub Actions)

`.github/workflows/llm-eval.yml` has two triggers with two distinct jobs:

- **`pull_request`** (touching `/prompts`, `/golden_dataset`, or `/src`):
  gatekeeping only. Runs the eval, uploads the HTML report as a workflow
  artifact, comments the result on the PR, and fails the job (blocking
  merge) if the run status is FAIL. Nothing is committed here — a PR's
  results aren't "official" until merged.
- **`push` to `main`**: the PR was accepted. Re-runs the eval against the
  merged state and **commits `data/eval_results.db` and `data/reports/`
  back to `main`**. This is what makes "the dashboard updates
  automatically" a factual claim rather than an aspirational one — pull
  `main` (or point a hosted dashboard at it) and you see the latest
  accepted run without a manual step.

Required repo secrets for live mode:
- `OPENAI_API_KEY` (also doubles as the fixed judge provider by default)
- `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` (optional — only needed if that provider is used in CI)
- `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`, `EMAIL_SMTP_*` (all optional — alerts on any unconfigured channel are silently skipped, not an error)

If `OPENAI_API_KEY` isn't set, the workflow automatically falls back to
`MOCK_MODE=true` so it's runnable on a fork with zero configuration.

**Full automated flow:**

```
Prompt changed → PR opened → GitHub Actions triggers → eval runs on
golden dataset (optionally across multiple providers) → rubric-driven
LLM-as-judge scores summaries → compared against baseline → z-test for
significance → drift checked → HTML report + Slack/Discord/email alert →
merge blocked if FAIL → on merge, results committed back to main →
dashboard reflects it on next load
```
