const SEVERITY_CLASS = {
  LOW: 'badge badge--low',
  MEDIUM: 'badge badge--medium',
  HIGH: 'badge badge--high',
}

const RESPONSE_LABEL = {
  NOTIFY: 'Notified',
  REQUIRE_APPROVAL: 'Approval required',
  BLOCK: 'Blocked',
}

export default function FindingsFeed({ findings, onApprove, onReject, busyId }) {
  if (findings.length === 0) {
    return (
      <div className="panel">
        <span className="eyebrow">Findings</span>
        <p className="empty-note">No deviations recorded for this agent.</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <span className="eyebrow">Findings — {findings.length} recorded</span>
      <ul className="findings-list">
        {findings.map((f) => (
          <li key={f.id} className="finding-card">
            <div className="finding-card__top">
              <span className={SEVERITY_CLASS[f.severity]}>{f.severity}</span>
              <span className="finding-card__type">{f.finding_type.replaceAll('_', ' ')}</span>
              <span className="finding-card__response">{RESPONSE_LABEL[f.response_action]}</span>
              <time className="finding-card__time">
                {new Date(f.created_at).toLocaleString()}
              </time>
            </div>

            <p className="finding-card__explanation">{f.explanation}</p>

            <div className="finding-card__evidence">
              <div>
                <span className="evidence-label">Expected</span>
                <span>{f.expected}</span>
              </div>
              <div>
                <span className="evidence-label">Actual</span>
                <span>{f.actual}</span>
              </div>
              <div>
                <span className="evidence-label">Run</span>
                <span className="mono">{f.run_id.slice(0, 8)}…</span>
              </div>
            </div>

            {f.response_action === 'REQUIRE_APPROVAL' && (
              <div className="finding-card__actions">
                <button
                  className="btn btn--approve"
                  disabled={busyId === f.id}
                  onClick={() => onApprove(f.id)}
                >
                  Approve
                </button>
                <button
                  className="btn btn--reject"
                  disabled={busyId === f.id}
                  onClick={() => onReject(f.id)}
                >
                  Reject
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
