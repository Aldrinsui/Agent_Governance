const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  listAgents: () => request('/agents'),
  getAgent: (id) => request(`/agents/${id}`),
  getActiveProfile: (id) => request(`/agents/${id}/profiles/active`).catch(() => null),
  listFindings: (id) => request(`/agents/${id}/findings`),
  getAudit: (id) => request(`/agents/${id}/audit`),
  approve: (findingId, actor, reason) =>
    request(`/findings/${findingId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ actor, reason }),
    }),
  reject: (findingId, actor, reason) =>
    request(`/findings/${findingId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ actor, reason }),
    }),
  runScenario: (name) => request(`/demo/run-scenario/${name}`, { method: 'POST' }),
}
