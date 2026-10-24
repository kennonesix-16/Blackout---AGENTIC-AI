import type { CrisisScenario, GridLine, GridNode, HistoryPoint, Incident, LineStatus, Order, TelemetrySnapshot } from '../types'

const nodeSpecs: GridNode[] = [
  { id: 'substation-east', label: 'Substation A', type: 'substation', x: 15, y: 28, requested_kw: 0, served_kw: 0, unmet_kw: 0, curtailed_kw: 0, status: 'normal' },
  { id: 'substation-west', label: 'Substation B', type: 'substation', x: 15, y: 72, requested_kw: 0, served_kw: 0, unmet_kw: 0, curtailed_kw: 0, status: 'normal' },
  { id: 'hospital', label: 'Hospital ICU', type: 'hospital', x: 44, y: 22, requested_kw: 280, served_kw: 280, unmet_kw: 0, curtailed_kw: 0, status: 'normal' },
  { id: 'commercial-north', label: 'Commercial A', type: 'commercial', x: 45, y: 50, requested_kw: 180, served_kw: 180, unmet_kw: 0, curtailed_kw: 0, status: 'responsive' },
  { id: 'residential-north', label: 'Residential A', type: 'residential', x: 45, y: 80, requested_kw: 150, served_kw: 150, unmet_kw: 0, curtailed_kw: 0, status: 'normal' },
  { id: 'ev-depot', label: 'EV Fleet Depot', type: 'ev', x: 75, y: 22, requested_kw: 0, served_kw: 0, unmet_kw: 0, soc_pct: 78, curtailed_kw: 0, status: 'flexible' },
  { id: 'commercial-south', label: 'Commercial B', type: 'commercial', x: 75, y: 50, requested_kw: 160, served_kw: 160, unmet_kw: 0, curtailed_kw: 0, status: 'responsive' },
  { id: 'residential-south', label: 'Residential B', type: 'residential', x: 75, y: 80, requested_kw: 120, served_kw: 120, unmet_kw: 0, curtailed_kw: 0, status: 'normal' },
]

const lineSpecs: GridLine[] = [
  { id: 'east-hospital', from_node: 'substation-east', to_node: 'hospital', capacity_kw: 420, loading_pct: 56, status: 'normal' },
  { id: 'east-commercial', from_node: 'substation-east', to_node: 'commercial-north', capacity_kw: 360, loading_pct: 58, status: 'normal' },
  { id: 'east-residential', from_node: 'substation-east', to_node: 'residential-north', capacity_kw: 300, loading_pct: 52, status: 'normal' },
  { id: 'hospital-ev', from_node: 'hospital', to_node: 'ev-depot', capacity_kw: 260, loading_pct: 46, status: 'normal' },
  { id: 'commercial-link', from_node: 'commercial-north', to_node: 'commercial-south', capacity_kw: 320, loading_pct: 64, status: 'normal' },
  { id: 'west-ev', from_node: 'substation-west', to_node: 'ev-depot', capacity_kw: 480, loading_pct: 28, status: 'normal' },
  { id: 'west-commercial', from_node: 'substation-west', to_node: 'commercial-south', capacity_kw: 340, loading_pct: 42, status: 'normal' },
  { id: 'west-residential', from_node: 'substation-west', to_node: 'residential-south', capacity_kw: 280, loading_pct: 49, status: 'normal' },
]

const baseOrders: Order[] = [
  { id: 'bid-hospital', timestamp: new Date().toISOString(), node_id: 'hospital', side: 'buy', quantity_kw: 280, price_per_kwh: 28.5, status: 'open', agent_type: 'hospital' },
  { id: 'bid-residential-a', timestamp: new Date().toISOString(), node_id: 'residential-north', side: 'buy', quantity_kw: 90, price_per_kwh: 11.2, status: 'open', agent_type: 'residential' },
  { id: 'ask-ev', timestamp: new Date().toISOString(), node_id: 'ev-depot', side: 'sell', quantity_kw: 120, price_per_kwh: 6.4, status: 'open', agent_type: 'ev' },
  { id: 'ask-commercial', timestamp: new Date().toISOString(), node_id: 'commercial-north', side: 'sell', quantity_kw: 100, price_per_kwh: 8.1, status: 'open', agent_type: 'commercial' },
]

function makeDecisions(shock: boolean) {
  const now = new Date().toISOString()
  return shock
    ? [
        { trade_id: 'trade-ev-hospital', buyer_id: 'hospital', seller_id: 'ev', quantity_kw: 120, clearing_price: 17.45, accepted: true, reason: 'Accepted: hospital priority and feeder path within thermal limit.', physics_mode: 'SIMULATION FALLBACK', timestamp: now },
        { trade_id: 'trade-commercial-hospital', buyer_id: 'hospital', seller_id: 'commercial', quantity_kw: 100, clearing_price: 18.3, accepted: true, reason: 'Accepted: commercial HVAC shed creates safe headroom.', physics_mode: 'SIMULATION FALLBACK', timestamp: now },
        { trade_id: 'trade-residential-hospital', buyer_id: 'hospital', seller_id: 'residential', quantity_kw: 60, clearing_price: 19.1, accepted: false, reason: 'Rejected: residential-north feeder exceeds conservative thermal limit.', physics_mode: 'SIMULATION FALLBACK', timestamp: now },
      ]
    : []
}

export function createMockSnapshot(tick = 1, scenario: CrisisScenario = 'normal'): TelemetrySnapshot {
  const shock = scenario !== 'normal'
  const severity = scenario === 'feeder_loss' ? 0.5 : scenario === 'supply_deficit' ? 0.2 : scenario === 'solar_reduction' ? 0.2 : 0
  const decisions = makeDecisions(shock)
  const hospitalServed = shock ? 250 : 280
  const commercialCurtail = shock ? 100 : 0
  const nodes = nodeSpecs.map((node) => {
    if (node.id === 'hospital') return { ...node, served_kw: hospitalServed, unmet_kw: node.requested_kw - hospitalServed, status: shock ? 'critical' : 'normal' }
    if (node.type === 'commercial') return { ...node, curtailed_kw: commercialCurtail, served_kw: node.requested_kw - commercialCurtail, status: shock ? 'shedding' : 'responsive' }
    if (node.id === 'ev-depot') return { ...node, soc_pct: shock ? 71 : 78 }
    return { ...node }
  })
  const lines: GridLine[] = lineSpecs.map((line) => {
    const loading = shock && line.id === 'east-hospital' ? 108 : shock && line.id === 'east-residential' ? 118 : Math.min(92, line.loading_pct + (tick % 4) * 2)
    const status: LineStatus = loading >= 100 ? 'overloaded' : loading >= 80 ? 'warning' : 'normal'
    return { ...line, loading_pct: loading, status }
  })
  const demand = 890
  const supply = Math.round(demand * (1 - severity) + (shock ? 80 : 0))
  return {
    schema_version: '1.0',
    timestamp: new Date().toISOString(),
    tick,
    nodes,
    lines,
    agents: [
      { agent_id: 'hospital-agent', type: 'hospital', node_id: 'hospital', requested_kw: 280, served_kw: hospitalServed, availability_kw: 0, curtailed_kw: 0, policy_note: 'Protect ICU circuits above price.' },
      { agent_id: 'ev-fleet-agent', type: 'ev', node_id: 'ev-depot', requested_kw: 0, served_kw: 0, availability_kw: shock ? 140 : 120, soc_pct: shock ? 71 : 78, curtailed_kw: 0, policy_note: 'Discharge above degradation cost.' },
      { agent_id: 'commercial-agent', type: 'commercial', node_id: 'commercial-north', requested_kw: 340, served_kw: 340 - commercialCurtail, availability_kw: commercialCurtail, curtailed_kw: commercialCurtail, policy_note: 'Shed HVAC before non-critical service.' },
      { agent_id: 'substation-agent', type: 'substation', node_id: 'substation-east', requested_kw: 0, served_kw: supply, availability_kw: supply, curtailed_kw: 0, policy_note: 'Clear only trades that pass path checks.' },
    ],
    order_book: baseOrders.map((order) => ({ ...order, timestamp: new Date().toISOString() })),
    recent_decisions: decisions,
    metrics: { auction_ms: shock ? 1.4 : 0.9, emission_ms: 0.5, telemetry_age_ms: 0, auction_target_ms: 200, telemetry_target_ms: 100, auction_samples: tick, telemetry_samples: tick * 2, auction_p50_ms: shock ? 1.2 : 0.8, auction_p95_ms: shock ? 2.1 : 1.4, telemetry_p50_ms: 0.4, telemetry_p95_ms: 0.8, missed_auction_cycles: 0 },
    scenario: { name: 'Ward 4 feeder resilience', phase: shock ? 'shock' : 'baseline', shock_active: shock, shock_label: scenario === 'normal' ? 'No active shock' : scenario === 'feeder_loss' ? 'Feeder Loss · 50%' : scenario === 'supply_deficit' ? 'Supply Deficit · 20%' : 'Solar Reduction · 20%', seed: 42, physics_mode: 'SIMULATION FALLBACK' },
  }
}

export function historyFromSnapshot(snapshot: TelemetrySnapshot): HistoryPoint {
  const demand = snapshot.nodes.reduce((sum, node) => sum + node.requested_kw, 0)
  const served = snapshot.nodes.reduce((sum, node) => sum + node.served_kw, 0)
  const flexibleSupply = snapshot.agents.filter((agent) => agent.type === 'ev').reduce((sum, agent) => sum + agent.availability_kw, 0)
  const supply = served + flexibleSupply
  const buys = snapshot.order_book.filter((order) => order.side === 'buy')
  const sells = snapshot.order_book.filter((order) => order.side === 'sell')
  const price = buys.length && sells.length ? (Math.max(...buys.map((order) => order.price_per_kwh)) + Math.min(...sells.map((order) => order.price_per_kwh))) / 2 : 0
  return { tick: snapshot.tick, demand, supply, price, hospital: snapshot.nodes.find((node) => node.id === 'hospital')?.served_kw || 0 }
}

export function incidentsFromSnapshot(snapshot: TelemetrySnapshot): Incident[] {
  const time = new Date(snapshot.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const incidents: Incident[] = []
  if (snapshot.scenario.shock_active) incidents.push({ id: `shock-${snapshot.tick}`, timestamp: time, tone: 'danger', title: snapshot.scenario.shock_label, detail: 'Scenario injected into the simulation.' })
  snapshot.recent_decisions.slice(0, 3).forEach((decision) => incidents.push({ id: decision.trade_id, timestamp: new Date(decision.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), tone: decision.accepted ? 'success' : 'warning', title: decision.accepted ? 'Trade accepted' : 'Trade rejected by governor', detail: `${decision.seller_id} → ${decision.buyer_id} · ${Math.round(decision.quantity_kw)} kW · ${decision.reason}` }))
  if (!incidents.length) incidents.push({ id: `ready-${snapshot.tick}`, timestamp: time, tone: 'info', title: 'Baseline market running', detail: 'Agents are submitting bids and asks against the synthetic city grid.' })
  return incidents
}
