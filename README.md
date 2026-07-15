# LLM Model Regression Detection System

CI/CD for LLM-powered features. This service runs your golden dataset
against a prompt/model version, scores the output across multiple
dimensions, diffs it against the last known-good run, and blocks the PR
if it finds a statistically significant regression — before it reaches
users.

## 🛠️ Tech Stack
- **Backend Service:** Python 3.10+, FastAPI (asynchronous backend router), SQLite (lightweight data persistence)
- **Frontend Dashboard:** React 18, Vite (build tool), TailwindCSS (premium styling), Recharts (Figma-grade composed vector charts)
- **DevOps & Integration:** GitHub Actions (CI/CD pipeline with automated push-back validation), Docker & Docker Compose
- **Evaluation Loop:** Jinja2 (HTML reports), OpenAI / Anthropic / Gemini SDK integrations, two-proportion z-tests for statistical significance

If you're joining the team and this is your first time touching prompt
evals, read this top to bottom once. It's written as onboarding docs, not
a tutorial.

---

## What this does, in one paragraph

Every time someone changes a file under `/prompts`, GitHub Actions runs
that prompt against a hand-labeled golden dataset of 60 customer support
emails, scores each response on category accuracy and summary relevance,
and compares the results to the previous run. If accuracy drops more than
3% it's a warning; more than 8% and it's statistically significant, it's a
FAIL and the merge is blocked. Either way, an HTML diff report is
generated and Slack/Discord/email alerts go out on whichever channels are
configured. A separate rolling 7-run moving average also watches for
slow, gradual drift that no single run would catch on its own.

The LLM feature under test here is a customer support email classifier
(billing / technical / account / general + a one-sentence summary), but
the harness — golden dataset, scoring, diffing, drift detection, alerting
— is intentionally feature-agnostic. Swap `src/llm_feature.py` for
whatever LLM-powered thing you're shipping and the rest of the pipeline
keeps working.

**Beyond the core loop, this also supports:**
- **Multi-provider comparison** — run the same prompt against OpenAI, Anthropic, and Gemini side by side (`--providers openai,anthropic,gemini`), compared in one table in the dashboard
- **Configurable LLM-as-judge rubric** — edit `golden_dataset/judge_rubric.yaml` to change scoring criteria/weights with no code changes, plus an optional embeddings-based semantic similarity score as a second dimension
- **Real dataset imports** — CSV/JSON upload (CLI or the web dashboard's Import Dataset page) instead of hand-editing JSON or being stuck with demo data
- **Multi-channel alerting** — Slack, Discord, and email, independently configurable, all firing from the same eval run
- **Two dashboards** — the original Streamlit app, and a custom React + FastAPI dashboard (`dashboard-web/`) reading the exact same data with a premium dark theme presentation layer featuring:
  - **User session management** — interactive sign-in/sign-up gatekeeper (supporting bypass demo account `PC` / Priyanshi Choudhary)
  - **Dynamic report serving** — on-the-fly Jinja2 HTML report generator API and one-click downloader buttons in runs panel
  - **Figma-grade composed charts** — high-fidelity accuracy trend charts matching mockup configurations (including circular colored dot nodes, white outlines, hover-triggered vertical grid cursor overlays, and legends)
  - **Interactive chart exports** — one-click CSV export buttons on Accuracy Trend and Drift Monitor charts for offline analysis
  - **Rich case debugging** — word-level diff highlighting (red = missing, green = new) between expected and predicted summaries, token usage breakdown bars (input vs. output), execution timeline visualizations (queue vs. LLM call), and live prompt template YAML viewer
  - **Smart dataset import UX** — client-side CSV/JSON validation on file selection (schema check, duplicate ID detection, row count preview, difficulty mix stats), animated import progress bar, and a success summary with total/added/updated stat cards
  - **Interactive layout grids** — circular difficulty dials (Easy, Medium, Hard progress rings), dual-column dataset import sandbox preview lists, and real-time header notification bell trays
  - **Paginated tables** — Runs table shows 10 rows with "Show all N runs / Show less" toggle; Overview regression diff viewer shows 5 rows with "View all regressions (N) / View less" toggle
  - **Evaluation Strategy selector** — interactive radio-button picker in Settings for choosing how outputs are scored: Exact Match, Semantic Similarity, LLM-as-a-Judge (recommended default), Regex Match, and JSON Structure Match — each with description badges communicating when to use which method

---

## Architecture

```
Prompt/Model Change → GitHub Actions Triggered → Run Evaluation Pipeline → Generate Report & Compare → Slack Alert (if regressions)
```

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

dashboard/app.py        Streamlit UI: Overview / Runs / Cases / Compare / Drift / Settings
dashboard-web/           React + FastAPI UI — same data, different presentation (see its own README)
prompts/*.yaml           Versioned prompt configs (the "code" under CI)
golden_dataset/*.json     Hand-labeled ground truth test cases
golden_dataset/judge_rubric.yaml   Configurable LLM-as-judge criteria + weights
.github/workflows/        GitHub Actions CI pipeline
```

Data flows one direction: `prompts/*.yaml` + `golden_dataset/*.json` go
into the eval runner, results land in SQLite, and everything downstream
(reports, dashboard, Slack) reads from SQLite. There's no hidden state.

---

## Quickstart (no API key required)

The whole pipeline runs in a deterministic **mock mode** out of the box —
useful for demos, onboarding, and CI smoke tests without burning API
credits. `MOCK_MODE=true` is the default in `.env.example`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env already has MOCK_MODE=true — leave it if you just want to try things out

# Run the baseline prompt, then the candidate prompt
python -m src.cli --prompt prompts/v7.yaml
python -m src.cli --prompt prompts/v8.yaml

# Open the generated diff report
open data/reports/latest.html   # (or just open the file in a browser)

# Explore results interactively
streamlit run dashboard/app.py
```

The dashboard includes Overview cards, a per-case Regression Diff Viewer,
a Compare Runs page for head-to-head version diffs, a multi-metric Drift
Monitor (accuracy / latency / tokens / summary quality), and searchable
Runs/Cases tables.

**Prefer a custom-built UI over Streamlit's default look?** There's also a
React + FastAPI dashboard reading the exact same data — see
[`dashboard-web/README.md`](dashboard-web/README.md). Same numbers, same
pipeline, different presentation layer (animated charts, command palette,
dark glassmorphism theme). Streamlit stays the zero-build fast path; the
web dashboard is for when you want something that doesn't read as a
prototyping tool.

This repo ships with a pre-populated `data/eval_results.db` containing a
demo run history (v7 baseline → v8 regression → v9-v14 recovery/drift) so
the dashboard has something to show immediately. Delete `data/` to start
from a clean slate.

### Switching to real providers — and running multiple side by side

```bash
# in .env — configure any subset; unconfigured providers fall back to mock
MOCK_MODE=false
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

```bash
# Single provider (uses LLM_PROVIDER/LLM_MODEL from .env, or override per-run)
python -m src.cli --prompt prompts/v8.yaml --provider anthropic

# Same prompt, same dataset, run against all three providers in one command —
# each becomes its own tagged run, directly comparable in the dashboard's
# Compare Runs → Side-by-Side (N-way) view
python -m src.cli --prompt prompts/v8.yaml --providers openai,anthropic,gemini
```

The judge is a **fixed provider** (`JUDGE_PROVIDER`, default `openai`)
regardless of which provider is under test — otherwise a cross-provider
comparison would be graded by different judges, which defeats the point.

Nothing else changes — same CLI, same dashboards, same report format,
whichever provider(s) you use.

---

## How mock mode works (and why it's safe to leave in)

The provider registry (`src/providers/registry.py`) checks `MOCK_MODE` and
each provider's API key independently, substituting a deterministic
keyword-based classifier + a content-overlap "judge" for any provider that
isn't configured. It's seeded by a hash of the provider name + prompt +
input, so re-running the same prompt against the same dataset always
produces the same scores — and different providers produce visibly
different (but each internally stable) results, so a multi-provider
side-by-side comparison looks meaningful even with zero API keys. This is
exactly what you want for CI smoke tests, reproducible demos, and trying
the multi-provider comparison feature before deciding to pay for three
API keys. It is **not** meant to be a substitute for real evals when
you're actually deciding whether to ship a prompt change or pick a
provider; flip `MOCK_MODE=false` for that.

---

## Adding new test cases to the golden dataset

The golden dataset (`golden_dataset/dataset_v1.json`) is hand-labeled —
this is not optional. Do not generate new cases with an LLM; the entire
point of a golden dataset is that it's ground truth a model didn't invent
for itself.

To add a case:

```json
{
  "id": "TC061",
  "input": "the raw email text",
  "expected_category": "billing | technical | account | general",
  "expected_summary": "one neutral sentence describing customer intent",
  "expected_difficulty": "easy | medium | hard",
  "notes": "why this case matters, especially if it's an edge case"
}
```

**The best source of new cases is production failures.** When a real
customer email gets misclassified, add it to the dataset with the correct
label. This is how the eval bar rises over time — you're not just testing
against what you thought of on day one, you're testing against what
actually broke. If you bump the dataset in a way that changes the pass
bar meaningfully, rename the file (`dataset_v2.json`) and update
`DATASET_PATH` in `.env` so old runs remain comparable to each other.

Aim to keep the ~30% "hard" / edge-case mix (ambiguous, short, typos,
sarcasm, mixed language) — that's what actually catches regressions.
Cases where any reasonable prompt gets 100% right forever don't tell you
anything when you change the prompt.

### Importing real cases in bulk (CSV/JSON) instead of hand-editing JSON

For adding more than a handful of cases at once — e.g. pulling a batch of
real misclassified production emails — use the importer instead of
hand-editing the dataset JSON:

```bash
# CSV with header: id,input,expected_category,expected_summary,expected_difficulty,notes
python -m src.dataset_importer --file new_cases.csv --output golden_dataset/dataset_v2.json

# Merge into an existing dataset instead of replacing it (new cases append;
# matching IDs get updated) — this is the common case
python -m src.dataset_importer --file new_cases.csv \
    --output golden_dataset/dataset_v2.json \
    --merge golden_dataset/dataset_v1.json
```

Every row is validated against the same `TestCase` schema the eval engine
uses — invalid categories, missing fields, or duplicate IDs fail the
*import*, not a later eval run. The same importer is also exposed over
HTTP as `POST /api/dataset/upload` on the web dashboard's backend, with a
matching upload page in the React UI (**Import Dataset** in the sidebar) —
this is what actually replaces the "demo data only" limitation with real
data, from either the CLI or a browser.

---

## Adjusting thresholds

All in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `WARNING_THRESHOLD_PCT` | 3.0 | Accuracy drop (pts) that triggers a WARNING |
| `CRITICAL_THRESHOLD_PCT` | 8.0 | Accuracy drop (pts) that triggers a FAIL (blocks merge) |
| `DRIFT_WINDOW` | 7 | Number of runs in the rolling moving average |
| `DRIFT_THRESHOLD_PCT` | 5.0 | Moving-average drop (pts) that triggers a slow-drift alert |

A FAIL also requires the drop to be **statistically significant**
(p < 0.05 via a two-proportion z-test — see `comparison.py`). This matters
on a 60-case dataset: 2 flipped cases out of 60 is well within normal
noise and shouldn't page anyone. The z-test is what keeps the pipeline
from crying wolf.

---

## Architecture decisions & rationale

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
touching the eval engine, scoring, or report generation.

**Why LLM-as-judge for summary scoring instead of exact-match or ROUGE?**
Summaries are free text — there's no single correct phrasing. An
LLM-as-judge (or the mock content-overlap heuristic in mock mode) can
recognize that two differently-worded summaries mean the same thing,
which string-similarity metrics can't reliably do. The tradeoff is judge
cost/latency and occasional judge inconsistency, which is why category
accuracy (binary, unambiguous) is scored separately and weighted equally
in the pass/fail decision rather than folded into one fuzzy score.

**Why block merge on FAIL but not on WARNING?**
A WARNING means something moved and a human should look at the diff
report before the next release. A FAIL means the regression is large
*and* statistically significant enough that shipping it blind is a bad
default. Teams that block on every WARNING train themselves to
routinely bypass CI; keeping FAIL rare and meaningful keeps the block
credible.

---

## Running in Docker

```bash
cp .env.example .env   # fill in real keys if not using mock mode
docker compose up eval-runner     # runs the eval once against v8
docker compose up dashboard       # dashboard at http://localhost:8501
```

Or standalone:

```bash
docker build -t llm-eval .
docker run --env-file .env -v $(pwd)/data:/app/data llm-eval --prompt prompts/v8.yaml
```

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

---

## Evaluation methodology — what's actually computing these numbers

Being specific about this matters, because "evaluation platform" can mean
very different levels of rigor. Here's exactly what's implemented:

| What | How |
|---|---|
| Category accuracy | Deterministic exact-match against the golden dataset label — binary, no fuzziness |
| Summary relevance | **Configurable-rubric LLM-as-judge**: a second LLM call scores 1–5 against `golden_dataset/judge_rubric.yaml` (criteria + weights) — edit that file, no code changes needed |
| Semantic similarity | **Optional** embeddings cosine similarity (`SEMANTIC_SIMILARITY_ENABLED=true`), a second and distinct dimension from the judge score. Off by default; falls back to a clearly-labeled token-overlap approximation rather than a silent gap in the data |
| Confidence | Self-reported by the model in its own structured output — not calibrated, treat as the model's opinion of itself, not ground truth |
| Multi-provider | OpenAI, Anthropic, and Gemini adapters behind one interface (`src/providers/`) — same prompt/dataset, run once per provider, directly comparable as separate tagged runs |
| Regression significance | Two-proportion z-test (α=0.05) on pass rates vs. baseline |
| Drift | Rolling N-run moving average vs. the first full window recorded |

**Not implemented** (worth naming explicitly rather than leaving vague):
BERTScore, ROUGE, and no dependency on Promptfoo, DeepEval, or LangSmith —
this is a from-scratch harness. BERTScore/ROUGE would mostly duplicate
what embeddings-based semantic similarity already covers here; not worth
the extra dependency weight unless a specific failure mode calls for them.

---

## Extending this to your own LLM feature

1. Replace `src/llm_feature.py` with your feature's logic and I/O contract.
2. Update `src/models.py` if your output shape isn't
   `{category, summary}` — e.g. a different Pydantic model.
3. Rebuild the golden dataset for your feature's domain (same JSON shape,
   different `expected_*` fields, or extend `TestCase`).
4. Everything else — runner, scoring, diffing, drift, reports, Slack,
   dashboard, CI — works unchanged, because they only depend on
   `CaseResult` and `EvalRun`, not on what the feature actually does.

---

## Local development notes

- Tests: `python tests/test_comparison.py` (no pytest dependency required
  — just run it directly; exits non-zero on failure so it's CI-friendly too).
- The dashboard's Settings page has a "Run eval" button that shells out to
  the CLI for convenience — handy for demos, not a replacement for CI.
- `data/reports/latest.html` always points at the most recent report,
  regardless of run ID, for quick access during local iteration.
- The web dashboard backend exposes `GET /api/prompts/{filename}` to serve
  prompt template YAML contents — used by the Cases page to render the
  prompt under test inline next to each case's results.
- Prompt paths in the Settings dropdown use POSIX forward slashes
  (`prompts/v7.yaml`) on all platforms including Windows.
