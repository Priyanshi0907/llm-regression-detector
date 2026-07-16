# Golden Dataset Guide

The golden dataset (`golden_dataset/dataset_v1.json`) is hand-labeled —
this is not optional. Do not generate new cases with an LLM; the entire
point of a golden dataset is that it's ground truth a model didn't invent
for itself.

## Schema

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

Aim to keep a ~30% "hard" / edge-case mix (ambiguous, short, typos,
sarcasm, mixed language) — that's what actually catches regressions.
Cases where any reasonable prompt gets 100% right forever don't tell you
anything when you change the prompt.

---

## Importing real cases in bulk (CSV/JSON)

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
*import*, not a later eval run.

The same importer is also exposed over HTTP as `POST /api/dataset/upload`
on the web dashboard's backend, with a matching upload page in the React
UI (**Import Dataset** in the sidebar) — client-side validation there
checks schema, flags duplicate IDs, previews row counts, and shows the
difficulty mix before you commit to the import. This is what replaces
"demo data only" with real data, from either the CLI or a browser.
