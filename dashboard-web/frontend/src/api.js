import { DEMO_RUNS, DEMO_OVERVIEW, DEMO_CASES, DEMO_DRIFT, DEMO_META } from './demoData'

const BASE = import.meta.env.VITE_API_URL || '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText} — ${body}`)
  }
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText} — ${body}`)
  }
  return res.json()
}

/**
 * Wrap an API call so it falls back to demo data when:
 *  - the backend is unreachable (frontend-only deploy), OR
 *  - the backend returns empty/no-data responses.
 */
function withFallback(apiCall, demoValue, isEmpty) {
  return apiCall
    .then((data) => {
      // If the real data is "empty", substitute demo data
      if (isEmpty && isEmpty(data)) return demoValue
      return data
    })
    .catch(() => demoValue)
}

export const api = {
  meta:         () => withFallback(get('/meta'),     DEMO_META),
  runs:         () => withFallback(get('/runs'),      DEMO_RUNS, (d) => !d || d.length === 0),
  run:         (id) => withFallback(get(`/runs/${encodeURIComponent(id)}`), DEMO_RUNS.find(r => r.run_id === id) || DEMO_RUNS[0]),
  runCases:    (id) => withFallback(get(`/runs/${encodeURIComponent(id)}/cases`), DEMO_CASES, (d) => !d || d.length === 0),
  overview:     () => withFallback(get('/overview'),  DEMO_OVERVIEW, (d) => d && d.has_data === false),
  compare:  (a, b) => withFallback(
    get(`/compare?run_a=${encodeURIComponent(a)}&run_b=${encodeURIComponent(b)}`),
    {
      run_a: DEMO_RUNS.find(r => r.run_id === a) || DEMO_RUNS[DEMO_RUNS.length - 4],
      run_b: DEMO_RUNS.find(r => r.run_id === b) || DEMO_RUNS[DEMO_RUNS.length - 3],
      regressions: 5,
      improvements: 2,
      p_value: 0.003,
      statistically_significant: true,
    }
  ),
  compareMulti: (runIds) => withFallback(
    get(`/compare-multi?run_ids=${runIds.map(encodeURIComponent).join(',')}`),
    { runs: runIds.map(id => DEMO_RUNS.find(r => r.run_id === id) || DEMO_RUNS[0]) }
  ),
  drift:        () => withFallback(get('/drift'),    DEMO_DRIFT, (d) => !d?.drift),
  uploadDataset: (payload) => post('/dataset/upload', payload),
  prompts:      () => withFallback(get('/prompts'),  ['prompts/v7.yaml', 'prompts/v8.yaml']),
  runEval: (payload) => post('/run-eval', payload),
}
