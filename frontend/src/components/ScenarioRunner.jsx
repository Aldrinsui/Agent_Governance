const SCENARIOS = [
  { id: 'A', label: 'A · Normal behavior', desc: 'All calls within approved profile' },
  { id: 'B', label: 'B · Unauthorized tool', desc: 'Agent calls file_delete, gets blocked' },
  { id: 'C', label: 'C · Guardrail escalation', desc: 'Call count crosses 80/90/100%' },
  { id: 'D', label: 'D · Human approval', desc: 'Unauthorized action pauses agent' },
]

export default function ScenarioRunner({ onRun, running }) {
  return (
    <div className="panel panel--scenarios">
      <span className="eyebrow">Run evaluation scenario</span>
      <div className="scenario-grid">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            className="scenario-btn"
            disabled={running}
            onClick={() => onRun(s.id)}
          >
            <span className="scenario-btn__label">{s.label}</span>
            <span className="scenario-btn__desc">{s.desc}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
