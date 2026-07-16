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

export const api = {
  meta: () => get('/meta'),
  runs: () => get('/runs'),
  run: (id) => get(`/runs/${encodeURIComponent(id)}`),
  runCases: (id) => get(`/runs/${encodeURIComponent(id)}/cases`),
  overview: () => get('/overview'),
  compare: (a, b) => get(`/compare?run_a=${encodeURIComponent(a)}&run_b=${encodeURIComponent(b)}`),
  compareMulti: (runIds) => get(`/compare-multi?run_ids=${runIds.map(encodeURIComponent).join(',')}`),
  drift: () => get('/drift'),
  uploadDataset: (payload) => post('/dataset/upload', payload),
  prompts: () => get('/prompts'),
  runEval: (payload) => post('/run-eval', payload),
}
