export default function ProfileView({ profile }) {
  if (!profile) {
    return (
      <div className="panel">
        <span className="eyebrow">Approved profile</span>
        <p className="empty-note">No active profile on this agent.</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <span className="eyebrow">Approved profile — {profile.name}</span>
      <div className="profile-grid">
        <div>
          <h4>Allowed tools</h4>
          <div className="chip-row">
            {profile.allowed_tools.map((t) => <span key={t} className="chip">{t}</span>)}
          </div>
        </div>
        <div>
          <h4>Allowed data sources</h4>
          <div className="chip-row">
            {profile.allowed_data_sources.map((d) => <span key={d} className="chip">{d}</span>)}
          </div>
        </div>
        <div>
          <h4>Allowed actions</h4>
          <div className="chip-row">
            {profile.allowed_actions.map((a) => <span key={a} className="chip">{a}</span>)}
          </div>
        </div>
      </div>

      {profile.guardrails.length > 0 && (
        <div className="guardrails">
          <h4>Guardrails</h4>
          {profile.guardrails.map((g) => (
            <div key={g.metric_name} className="guardrail-row">
              <span className="guardrail-row__name">{g.metric_name}</span>
              <span className="guardrail-row__meta">
                limit {g.max_value} · warn {g.warning_pct}% · critical {g.critical_pct}%
              </span>
              <span className={`badge badge--level-${g.last_warning_level.toLowerCase()}`}>
                {g.last_warning_level}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
