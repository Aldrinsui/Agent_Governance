import { useState, useEffect, useCallback } from 'react'
import { api } from './api'
import AgentList from './components/AgentList'
import ProfileView from './components/ProfileView'
import FindingsFeed from './components/FindingsFeed'
import AuditTrail from './components/AuditTrail'
import ScenarioRunner from './components/ScenarioRunner'

const STATE_META = {
  ACTIVE: { label: 'Active', className: 'badge badge--active' },
  PAUSED: { label: 'Paused · Approval needed', className: 'badge badge--paused' },
  BLOCKED: { label: 'Blocked', className: 'badge badge--blocked' },
}

export default function App() {
  const [agents, setAgents] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [profile, setProfile] = useState(null)
  const [findings, setFindings] = useState([])
  const [audit, setAudit] = useState([])
  const [running, setRunning] = useState(false)
  const [busyFindingId, setBusyFindingId] = useState(null)
  const [error, setError] = useState(null)

  const refreshAgents = useCallback(async () => {
    const list = await api.listAgents()
    setAgents(list)
    return list
  }, [])

  const loadAgentDetail = useCallback(async (id) => {
    if (!id) return
    const [prof, find, aud] = await Promise.all([
      api.getActiveProfile(id),
      api.listFindings(id),
      api.getAudit(id),
    ])
    setProfile(prof)
    setFindings(find)
    setAudit(aud)
  }, [])

  useEffect(() => {
    refreshAgents().catch((e) => setError(e.message))
  }, [refreshAgents])

  useEffect(() => {
    if (selectedId) {
      loadAgentDetail(selectedId).catch((e) => setError(e.message))
    }
  }, [selectedId, loadAgentDetail])

  const handleSelect = (id) => {
    setError(null)
    setSelectedId(id)
  }

  const handleRunScenario = async (name) => {
    setRunning(true)
    setError(null)
    try {
      const result = await api.runScenario(name)
      const list = await refreshAgents()
      const newAgent = list.find((a) => a.id === result.agent_id)
      if (newAgent) {
        setSelectedId(newAgent.id)
        await loadAgentDetail(newAgent.id)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const handleApprove = async (findingId) => {
    setBusyFindingId(findingId)
    setError(null)
    try {
      await api.approve(findingId, 'reviewer@flyyy.ai', 'Approved via console')
      await refreshAgents()
      await loadAgentDetail(selectedId)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyFindingId(null)
    }
  }

  const handleReject = async (findingId) => {
    setBusyFindingId(findingId)
    setError(null)
    try {
      await api.reject(findingId, 'reviewer@flyyy.ai', 'Rejected via console')
      await refreshAgents()
      await loadAgentDetail(selectedId)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyFindingId(null)
    }
  }

  const selectedAgent = agents.find((a) => a.id === selectedId)

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <span className="app-header__eyebrow">FLYYY.AI</span>
          <h1>Agent Governance Console</h1>
        </div>
        <span className="app-header__tag">Define → Monitor → Detect → Respond → Audit</span>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <ScenarioRunner onRun={handleRunScenario} running={running} />

      <div className="app-body">
        <AgentList agents={agents} selectedId={selectedId} onSelect={handleSelect} />

        <main className="app-main">
          {!selectedAgent && (
            <div className="panel">
              <p className="empty-note">
                Select an agent, or run a scenario above to provision one and see the
                full governance loop end to end.
              </p>
            </div>
          )}

          {selectedAgent && (
            <>
              <div className="panel panel--agent-summary">
                <div>
                  <span className="eyebrow">Agent</span>
                  <h2>{selectedAgent.name}</h2>
                </div>
                <span className={STATE_META[selectedAgent.state].className}>
                  {STATE_META[selectedAgent.state].label}
                </span>
              </div>

              <ProfileView profile={profile} />
              <FindingsFeed
                findings={findings}
                onApprove={handleApprove}
                onReject={handleReject}
                busyId={busyFindingId}
              />
              <AuditTrail entries={audit} />
            </>
          )}
        </main>
      </div>
    </div>
  )
}
