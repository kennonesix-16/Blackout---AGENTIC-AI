import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Activity, AlertTriangle, BatteryCharging, CircleDot, Clock3, Gauge, HeartPulse, Pause, Play, RefreshCw, RotateCcw, ShieldCheck, Sparkles, WifiOff, Zap } from 'lucide-react'
import { DecisionInspector } from '../components/DecisionInspector'
import { AgentCard } from '../components/AgentCard'
import { IncidentLog } from '../components/IncidentLog'
import { KpiCard } from '../components/KpiCard'
import { NodeDetails, TopologyMap } from '../components/TopologyMap'
import { OrderBook } from '../components/OrderBook'
import { PriceChart, TrendChart } from '../components/TrendChart'
import { getHealth, getState, injectScenario, resetSimulation, startSimulation } from '../services/api'
import { createMockSnapshot, historyFromSnapshot, incidentsFromSnapshot } from '../services/mockData'
import { createTelemetrySocket } from '../services/websocket'
import type { CrisisScenario, GridNode, HistoryPoint, Incident, PowerBalance, TelemetrySnapshot, TradeDecision } from '../types'

function isPowerBalance(value: unknown): value is PowerBalance {
  if (!value || typeof value !== 'object') return false
  const balance = value as Record<string, unknown>
  return ['total_demand_kw', 'available_supply_kw', 'served_load_kw', 'unmet_demand_kw', 'deficit_kw'].every((key) => {
    const metric = balance[key]
    return typeof metric === 'number' && Number.isFinite(metric) && metric >= 0
  })
}

function isSnapshot(value: unknown): value is TelemetrySnapshot {
  if (!value || typeof value !== 'object') return false
  const snapshot = value as Partial<TelemetrySnapshot>
  return Boolean(snapshot.schema_version === '1.0' && Array.isArray(snapshot.nodes) && Array.isArray(snapshot.lines) && Array.isArray(snapshot.agents) && Array.isArray(snapshot.order_book) && Array.isArray(snapshot.recent_decisions) && snapshot.metrics && snapshot.scenario && isPowerBalance(snapshot.power_balance))
}

const scenarioLabels: Record<CrisisScenario, string> = { normal: 'Normal operation', supply_deficit: '20% supply reduction', feeder_loss: '50% feeder capacity loss', solar_reduction: 'Solar generation reduction' }

export function DashboardPage() {
  const [snapshot, setSnapshot] = useState<TelemetrySnapshot>(() => createMockSnapshot())
  const [history, setHistory] = useState<HistoryPoint[]>(() => [historyFromSnapshot(createMockSnapshot())])
  const [incidents, setIncidents] = useState<Incident[]>(() => incidentsFromSnapshot(createMockSnapshot()))
  const [selectedNode, setSelectedNode] = useState<GridNode>()
  const [selectedDecision, setSelectedDecision] = useState<TradeDecision>()
  const [connected, setConnected] = useState(false)
  const [liveMode, setLiveMode] = useState(false)
  const [paused, setPaused] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('Demo mode is active until the backend becomes available.')
  const mockTick = useRef(1)

  const pushSnapshot = useCallback((next: TelemetrySnapshot, source: 'live' | 'mock') => {
    setSnapshot(next)
    setHistory((current) => [...current, historyFromSnapshot(next)].slice(-28))
    setIncidents((current) => [...incidentsFromSnapshot(next), ...current].filter((item, index, all) => all.findIndex((candidate) => candidate.id === item.id) === index).slice(0, 18))
    setLiveMode(source === 'live')
    setNotice(source === 'live' ? '' : 'Demo fallback · connect the backend for live telemetry.')
  }, [])

  useEffect(() => {
    let mounted = true
    getHealth().then(() => getState()).then((value) => { if (mounted && isSnapshot(value)) pushSnapshot(value, 'live') }).catch(() => { if (mounted) setNotice('Backend unavailable · demo fallback is running with clearly labeled synthetic data.') })
    const cleanup = createTelemetrySocket<TelemetrySnapshot>({ onMessage: (value) => { if (mounted && isSnapshot(value)) pushSnapshot(value, 'live') }, onStatus: (value) => mounted && setConnected(value), onError: (message) => mounted && setNotice(message) })
    return () => { mounted = false; cleanup() }
  }, [pushSnapshot])

  useEffect(() => {
    if (liveMode || paused) return
    const timer = window.setInterval(() => {
      mockTick.current += 1
      const scenario: CrisisScenario = snapshot.scenario.shock_label.includes('Feeder') ? 'feeder_loss' : snapshot.scenario.shock_label.includes('Supply') ? 'supply_deficit' : snapshot.scenario.shock_label.includes('Solar') ? 'solar_reduction' : 'normal'
      pushSnapshot(createMockSnapshot(mockTick.current, scenario), 'mock')
    }, 1800)
    return () => window.clearInterval(timer)
  }, [liveMode, paused, pushSnapshot, snapshot.scenario.shock_label])

  const { total_demand_kw: demand, available_supply_kw: supply, deficit_kw: deficit } = snapshot.power_balance
  const hospital = snapshot.nodes.find((node) => node.id === 'hospital')
  const ev = snapshot.agents.find((agent) => agent.type === 'ev')
  const commercial = snapshot.agents.find((agent) => agent.type === 'commercial')
  const buyOrders = snapshot.order_book.filter((order) => order.side === 'buy')
  const sellOrders = snapshot.order_book.filter((order) => order.side === 'sell')
  const clearingPrice = buyOrders.length && sellOrders.length ? (Math.max(...buyOrders.map((order) => order.price_per_kwh)) + Math.min(...sellOrders.map((order) => order.price_per_kwh))) / 2 : 0
  const accepted = snapshot.recent_decisions.filter((decision) => decision.accepted).length
  const rejected = snapshot.recent_decisions.filter((decision) => !decision.accepted).length
  const activeDecision = selectedDecision && snapshot.recent_decisions.some((decision) => decision.trade_id === selectedDecision.trade_id) ? selectedDecision : snapshot.recent_decisions[0]
  const displayAgents = useMemo(() => snapshot.agents.some((agent) => agent.type === 'substation') ? snapshot.agents : [...snapshot.agents, {
    agent_id: 'auction-coordinator-view',
    type: 'substation',
    node_id: snapshot.nodes.find((node) => node.type === 'substation')?.id || 'substation-east',
    requested_kw: 0,
    served_kw: 0,
    availability_kw: 0,
    soc_pct: null,
    curtailed_kw: 0,
    policy_note: 'Derived coordinator view from market decisions and governor telemetry.',
  }], [snapshot])

  const updateScenario = async (scenario: CrisisScenario) => {
    setBusy(true)
    setNotice('')
    try {
      if (!liveMode) {
        pushSnapshot(createMockSnapshot(mockTick.current + 1, scenario), 'mock')
        mockTick.current += 1
        setNotice(`Demo scenario applied · ${scenarioLabels[scenario]}.`)
        return
      }
      if (scenario === 'solar_reduction') throw new Error('The backend contract does not expose a solar reduction event yet.')
      const next = scenario === 'normal' ? await injectScenario({ event_type: 'clear', target_id: 'ward-4-feeder', magnitude: 0, units: 'fraction', seed: 42 }) : await injectScenario({ event_type: scenario === 'feeder_loss' ? 'feeder_loss' : 'supply_deficit', target_id: 'ward-4-feeder', magnitude: scenario === 'feeder_loss' ? 0.5 : 0.2, units: 'fraction', seed: 42 })
      if (isSnapshot(next)) pushSnapshot(next, 'live')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Scenario request failed. No successful backend response was received.')
    } finally { setBusy(false) }
  }

  const handleStart = async () => {
    setBusy(true)
    try { if (liveMode) await startSimulation(); setPaused(false); setNotice(liveMode ? 'Simulation loop started.' : 'Demo loop started.') } catch { setNotice('Start request failed. The backend did not confirm the action.') } finally { setBusy(false) }
  }

  const handleReset = async () => {
    setBusy(true)
    try {
      if (liveMode) { const next = await resetSimulation(); if (isSnapshot(next)) pushSnapshot(next, 'live') } else { mockTick.current = 1; pushSnapshot(createMockSnapshot(1), 'mock') }
      setPaused(false)
      setNotice('Scenario reset to baseline.')
    } catch { setNotice('Reset request failed. The backend did not confirm the action.') } finally { setBusy(false) }
  }

  return <main className="app-shell">
    <header className="app-header"><div className="brand"><span className="brand-badge"><Zap size={18} /></span><div><div className="brand-overline">AUTONOMOUS ENERGY MARKET · WARD 4</div><h1>BLACKOUT <span>BROKER</span></h1></div></div><div className="header-right"><span className={`connection-pill ${connected ? 'connected' : ''}`}><CircleDot size={12} />{connected ? 'LIVE TELEMETRY' : 'DEMO TELEMETRY'}</span><span className="mode-pill"><Sparkles size={12} />{liveMode ? 'BACKEND CONNECTED' : 'SIMULATION FALLBACK'}</span><button className="icon-btn" title="Refresh state" onClick={() => window.location.reload()}><RefreshCw size={16} /></button></div></header>

    <section className="hero"><div><div className="eyebrow orange">CITY RESILIENCE EXCHANGE / CONTROL ROOM</div><h2>Coordinate the city<br /><span>before the blackout spreads.</span></h2><p>Autonomous agents bid, shed, and discharge against a deterministic simulation of an eight-node urban grid.</p></div><div className={`system-state ${snapshot.scenario.shock_active ? 'shock' : ''}`}><div><span className="state-dot" /> SYSTEM {snapshot.scenario.shock_active ? 'UNDER SHOCK' : 'STABLE'}</div><strong>{snapshot.scenario.shock_label}</strong><small>PHYSICS MODE · {snapshot.scenario.physics_mode}</small></div></section>

    <section className="control-strip"><div className="control-intro"><span className="eyebrow">SIMULATION CONTROL</span><strong>{paused ? 'Telemetry view paused' : snapshot.scenario.shock_active ? 'Crisis state is active' : 'Baseline market is running'}</strong><small>{notice || 'Choose a scenario to exercise the market and safety governor.'}</small></div><div className="control-actions"><button className="control-btn" disabled={busy} onClick={handleStart}><Play size={14} /> Start</button><button className={`control-btn ${paused ? 'active' : ''}`} disabled={busy} onClick={() => { setPaused((value) => !value); setNotice(paused ? 'Demo telemetry resumed.' : 'Demo telemetry paused locally; backend loop is unchanged.') }}><Pause size={14} /> {paused ? 'Resume' : 'Pause'}</button><button className="control-btn" disabled={busy} onClick={handleReset}><RotateCcw size={14} /> Reset</button></div><div className="scenario-actions"><button disabled={busy} onClick={() => updateScenario('normal')}>Normal</button><button disabled={busy} onClick={() => updateScenario('supply_deficit')}>-20% supply</button><button disabled={busy} onClick={() => updateScenario('feeder_loss')} className="danger-action"><AlertTriangle size={13} /> -50% feeder</button><button disabled={busy} onClick={() => updateScenario('solar_reduction')}>Solar -20%</button></div></section>
    {notice && <div className={`notice ${notice.includes('unavailable') || notice.includes('failed') || notice.includes('does not') ? 'warning' : ''}`}><WifiOff size={15} /> {notice}</div>}

    <section className="kpi-grid"><KpiCard label="Market demand" value={`${Math.round(demand).toLocaleString()} kW`} detail="current auction buy quantity" icon={<Gauge size={19} />} tone="blue" /><KpiCard label="Available supply" value={`${supply.toLocaleString()} kW`} detail="current auction sell quantity" icon={<Zap size={19} />} tone={deficit ? 'amber' : 'green'} /><KpiCard label="Market deficit" value={`${deficit.toLocaleString()} kW`} detail="unmet demand after latest clearing" icon={<AlertTriangle size={19} />} tone={deficit ? 'red' : 'green'} /><KpiCard label="Hospital allocation" value={`${Math.round(hospital?.served_kw || 0)} kW`} detail={`${Math.round(hospital?.unmet_kw || 0)} kW unmet of ${Math.round(hospital?.requested_kw || 0)} kW`} icon={<HeartPulse size={19} />} tone={hospital?.unmet_kw ? 'red' : 'green'} /><KpiCard label="Clearing price" value={`₹${clearingPrice.toFixed(2)}`} detail="modeled midpoint / kWh" icon={<Activity size={19} />} tone="purple" /><KpiCard label="Trade decisions" value={`${accepted} / ${rejected}`} detail="accepted / rejected" icon={<ShieldCheck size={19} />} tone="green" /></section>

    <section className="content-grid topology-layout"><article className="panel topology-panel"><div className="panel-header"><div><span className="eyebrow">SYNTHETIC NETWORK VIEW</span><h3>Eight-node topology</h3></div><span className="panel-tag">NETWORK VALUES · NOT MARKET TOTALS</span></div><TopologyMap nodes={snapshot.nodes} lines={snapshot.lines} onSelect={setSelectedNode} selectedId={selectedNode?.id} /><NodeDetails node={selectedNode} /></article><aside className="side-column"><article className="panel health-panel"><div className="panel-header"><div><span className="eyebrow">RESILIENCE SIGNALS</span><h3>Critical load health</h3></div><span className="live-label"><span className="state-dot" /> live</span></div><div className="health-row"><HeartPulse size={17} /><div><span>Hospital ICU circuits</span><b>{hospital?.unmet_kw ? 'attention required' : 'protected'}</b></div><strong>{Math.round(hospital?.served_kw || 0)}<small> kW</small></strong></div><div className="health-row"><BatteryCharging size={17} /><div><span>EV fleet reserve</span><b>V2G ready</b></div><strong>{Math.round(ev?.soc_pct || 0)}<small>%</small></strong></div><div className="health-row"><Gauge size={17} /><div><span>Commercial flexibility</span><b>negawatt offer</b></div><strong>{Math.round(commercial?.curtailed_kw || 0)}<small> kW</small></strong></div></article><article className="panel timing-panel"><div className="panel-header"><div><span className="eyebrow">ENGINE TELEMETRY</span><h3>Observed runtime</h3></div><Clock3 size={17} /></div><div className="timing-grid"><span>Auction p50</span><b>{snapshot.metrics.auction_p50_ms.toFixed(2)} ms</b><span>Auction p95</span><b>{snapshot.metrics.auction_p95_ms.toFixed(2)} ms</b><span>Telemetry p95</span><b>{snapshot.metrics.telemetry_p95_ms.toFixed(2)} ms</b><span>Cycles sampled</span><b>{snapshot.metrics.auction_samples}</b></div><small className="panel-footnote">Targets: 200 ms auction / 100 ms telemetry. Observed simulation values only.</small></article></aside></section>

    <section className="content-grid two-column"><article className="panel"><div className="panel-header"><div><span className="eyebrow">SUPPLY / DEMAND HISTORY</span><h3>Grid balance</h3></div><span className="panel-tag">LAST {history.length} TICKS</span></div><TrendChart points={history} /></article><article className="panel"><div className="panel-header"><div><span className="eyebrow">MARKET SIGNAL</span><h3>Clearing price</h3></div><span className="panel-tag">MIDPOINT RULE</span></div><PriceChart points={history} /></article></section>

    <section className="content-grid market-layout"><article className="panel"><div className="panel-header"><div><span className="eyebrow">CONTINUOUS DOUBLE AUCTION</span><h3>Live order book</h3></div><span className="panel-tag">{snapshot.order_book.length} OPEN ORDERS</span></div><OrderBook orders={snapshot.order_book} decisions={snapshot.recent_decisions} /></article><article className="panel"><div className="panel-header"><div><span className="eyebrow">SAFETY GOVERNOR</span><h3>Why this trade?</h3></div><span className="panel-tag">EXPLAINABLE CHECKS</span></div><DecisionInspector snapshot={snapshot} decision={activeDecision} onSelect={setSelectedDecision} /><div className="incident-divider"><div className="panel-header"><div><span className="eyebrow">AGENT ACTIVITY</span><h3>Decision feed</h3></div><span className="panel-tag">RECENT EVENTS</span></div><IncidentLog incidents={incidents} /></div></article></section>

    <section className="panel agents-panel"><div className="panel-header"><div><span className="eyebrow">AUTONOMOUS PARTICIPANTS</span><h3>Agent operating states</h3></div><span className="panel-tag">{displayAgents.length} SYNTHETIC NETWORK VIEW</span></div><div className="agent-grid">{displayAgents.map((agent) => <AgentCard key={agent.agent_id} agent={agent} />)}</div></section>

    <footer><span>BLACKOUT BROKER · FRONTEND MVP</span><span><ShieldCheck size={13} /> Simulation only · no production dispatch, safety certification, or continuity guarantee</span></footer>
  </main>
}
