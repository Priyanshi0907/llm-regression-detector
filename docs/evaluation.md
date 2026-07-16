# Evaluation Methodology

Being specific about this matters, because "evaluation platform" can mean
very different levels of rigor. Here's exactly what's implemented.

| What | How |
|---|---|
| Category accuracy | Deterministic exact-match against the golden dataset label — binary, no fuzziness |
| Summary relevance | **Configurable-rubric LLM-as-judge**: a second LLM call scores 1–5 against `golden_dataset/judge_rubric.yaml` (criteria + weights) — edit that file, no code changes needed |
| Semantic similarity | **Optional** embeddings cosine similarity (`SEMANTIC_SIMILARITY_ENABLED=true`), a second and distinct dimension from the judge score. Off by default; falls back to a clearly-labeled token-overlap approximation rather than a silent gap in the data |
| Confidence | Self-reported by the model in its own structured output — not calibrated, treat as the model's opinion of itself, not ground truth |
| Multi-provider | OpenAI, Anthropic, and Gemini adapters behind one interface (`src/providers/`) — same prompt/dataset, run once per provider, directly comparable as separate tagged runs, all graded by the same fixed judge provider |
| Regression significance | Two-proportion z-test (α=0.05) on pass rates vs. baseline |
| Drift | Rolling N-run moving average vs. the first full window recorded |

**Not implemented** (worth naming explicitly rather than leaving vague):
BERTScore, ROUGE, and no dependency on Promptfoo, DeepEval, or LangSmith —
this is a from-scratch harness. BERTScore/ROUGE would mostly duplicate
what embeddings-based semantic similarity already covers here; not worth
the extra dependency weight unless a specific failure mode calls for them.

---

## How mock mode works (and why it's safe to leave in)

The provider registry (`src/providers/registry.py`) checks `MOCK_MODE` and
each provider's API key independently, substituting a deterministic
keyword-based classifier + a content-overlap "judge" for any provider that
isn't configured. It's seeded by a hash of the provider name + prompt +
input, so re-running the same prompt against the same dataset always
produces the same scores — and different providers produce visibly
different (but each internally stable) results, so a multi-provider
side-by-side comparison looks meaningful even with zero API keys.

This is exactly what you want for CI smoke tests, reproducible demos, and
trying the multi-provider comparison feature before deciding to pay for
three API keys. It is **not** meant to be a substitute for real evals
when you're actually deciding whether to ship a prompt change or pick a
provider — flip `MOCK_MODE=false` for that.

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
(p < 0.05 via a two-proportion z-test — see `src/comparison.py`). This
matters on a 60-case dataset: 2 flipped cases out of 60 is well within
normal noise and shouldn't page anyone. The z-test is what keeps the
pipeline from crying wolf.

---

## Multi-provider evaluation in depth

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

Nothing else changes — same CLI, same dashboards, same report format,
whichever provider(s) you use.

---

## The judge rubric

`golden_dataset/judge_rubric.yaml` defines the criteria and weights the
judge uses when scoring summary relevance. Editing this file changes
scoring behavior on the next run — no code changes required. This is
also where you'd add a new criterion (e.g. "does the summary avoid
leaking PII") if your feature domain needs it.

## Semantic similarity

Off by default because it's an extra API call per case. When enabled
(`SEMANTIC_SIMILARITY_ENABLED=true`) with an OpenAI key configured, it
computes embeddings cosine similarity between the expected and actual
summary as a second, independent score alongside the judge score — the
two can disagree, and that disagreement is itself a useful signal (e.g.
a summary that's lexically close but the judge correctly flags as
missing the actual intent). When disabled, the field is populated with a
clearly-labeled token-overlap approximation rather than left empty.
