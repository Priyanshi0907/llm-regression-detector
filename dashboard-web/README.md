# Web Dashboard (React + FastAPI)

A custom-built alternative to the Streamlit dashboard — same underlying
data (same SQLite DB, same `src/` pipeline code, zero duplicated logic),
different presentation: dark glassmorphism theme, animated Recharts
visualizations, a command palette (⌘K), toast notifications, skeleton
loaders, and a proper multi-page React app instead of a Streamlit script.

The Streamlit dashboard (`dashboard/app.py`) still works and is still the
faster path if you just want to look at results with zero build step. This
is for when you want something that doesn't read as a rapid-prototyping
tool in a portfolio or demo.

## Architecture

```
dashboard-web/
  backend/
    main.py            FastAPI app — thin read-only wrapper over src/storage.py,
                        src/comparison.py, src/drift.py. No logic lives here;
                        it only serializes what the pipeline already computed.
  frontend/
    src/
      pages/            Overview, Runs, Cases, Compare (2-way diff + N-way
                        side-by-side for multi-provider comparison), Drift,
                        Import Dataset, How It Works
      components/       Sidebar, MetricCard, Badge, TrendChart, BarChartPanel,
                         CommandPalette, Skeleton
      api.js            fetch() wrapper for the backend endpoints
```

## Local development (two servers, hot reload)

```bash
# Terminal 1 — backend (from the project root, not dashboard-web/)
pip install -r dashboard-web/backend/requirements.txt
uvicorn dashboard-web.backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd dashboard-web/frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the
backend on port 8000 (see `vite.config.js`), so both need to be running.

## Production / single-command run

Build the frontend once, then run only the backend — it serves the built
static files itself, so there's exactly one process and one port:

```bash
cd dashboard-web/frontend && npm install && npm run build && cd ../..
pip install -r dashboard-web/backend/requirements.txt
uvicorn dashboard-web.backend.main:app --port 8000
```

Open http://localhost:8000 — this single URL serves the app, the API, and
handles client-side route refreshes (e.g. reloading on `/cases` directly).

## What's actually different from the Streamlit version

Same numbers, same pipeline, same golden dataset — this is a presentation
layer, not a second implementation. The one genuinely new thing is the
**How It Works** page, which didn't have a Streamlit equivalent: it
explicitly documents what LLM-as-judge is being used for, what statistical
test backs the "regression" label, and — just as importantly — what's
*not* implemented yet (BERTScore, embeddings-based similarity, ROUGE),
rather than letting a slick UI imply capabilities that aren't there.

## Known trade-offs

- No auth — this assumes local/internal use, same as the Streamlit version.
- The command palette's run search is client-side only (fine at hundreds
  of runs, would want a real search endpoint at large scale).
- Charts re-fetch on every page visit rather than using a shared cache —
  simple and correct, not optimized for very frequent navigation.
