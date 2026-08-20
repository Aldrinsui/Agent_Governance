const STATE_META = {
  ACTIVE: { label: 'Active', className: 'badge badge--active' },
  PAUSED: { label: 'Paused · Approval needed', className: 'badge badge--paused' },
  BLOCKED: { label: 'Blocked', className: 'badge badge--blocked' },
}

export default function AgentList({ agents, selectedId, onSelect }) {
  return (
    <div className="agent-list">
      <div className="agent-list__header">
        <span className="eyebrow">Monitored agents</span>
        <span className="agent-list__count">{agents.length}</span>
      </div>
      {agents.length === 0 && (
        <p className="empty-note">No agents yet. Run a scenario to provision one.</p>
      )}
      <ul>
        {agents.map((a) => {
          const meta = STATE_META[a.state] || STATE_META.ACTIVE
          return (
            <li key={a.id}>
              <button
                className={`agent-row ${selectedId === a.id ? 'agent-row--selected' : ''}`}
                onClick={() => onSelect(a.id)}
              >
                <span className="agent-row__name">{a.name}</span>
                <span className={meta.className}>{meta.label}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
