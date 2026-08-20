export default function AuditTrail({ entries }) {
  if (entries.length === 0) {
    return (
      <div className="panel">
        <span className="eyebrow">Audit trail</span>
        <p className="empty-note">No audit entries yet.</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <span className="eyebrow">Audit trail — {entries.length} entries</span>
      <ol className="audit-list">
        {entries.map((e) => (
          <li key={e.id} className="audit-row">
            <time className="audit-row__time">{new Date(e.created_at).toLocaleString()}</time>
            <span className="audit-row__type">{e.event_type.replaceAll('_', ' ')}</span>
            {e.from_state && e.to_state && e.from_state !== e.to_state && (
              <span className="audit-row__transition">
                {e.from_state} → {e.to_state}
              </span>
            )}
            <span className="audit-row__actor">{e.actor}</span>
            <span className="audit-row__reason">{e.reason}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
