export type NodeType = 'hospital' | 'commercial' | 'residential' | 'ev' | 'substation'
export type LineStatus = 'normal' | 'warning' | 'overloaded'
export type OrderSide = 'buy' | 'sell'

export interface GridNode {
  id: string
  label: string
  type: NodeType | string
  x: number
  y: number
  requested_kw: number
  served_kw: number
  unmet_kw: number
  soc_pct?: number | null
  curtailed_kw: number
  status: string
}

export interface GridLine {
  id: string
  from_node: string
  to_node: string
  capacity_kw: number
  loading_pct: number
  status: LineStatus
}

export interface AgentState {
  agent_id: string
  type: string
  node_id: string
  requested_kw: number
  served_kw: number
  availability_kw: number
  soc_pct?: number | null
  curtailed_kw: number
  policy_note: string
  allocation_reason?: string
}

export interface Order {
  id: string
  timestamp: string
  node_id: string
  side: OrderSide
  quantity_kw: number
  price_per_kwh: number
  status: string
  agent_type: string
}

export interface TradeDecision {
  trade_id: string
  buyer_id: string
  seller_id: string
  quantity_kw: number
  clearing_price: number
  accepted: boolean
  reason: string
  physics_mode: string
  timestamp: string
  decision_id?: string | null
  affected_id?: string | null
  decision_type?: 'trade' | 'allocation' | 'scenario'
  before?: Record<string, number>
  after?: Record<string, number>
}

export interface Metrics {
  auction_ms: number
  emission_ms: number
  telemetry_age_ms: number
  auction_target_ms: number
  telemetry_target_ms: number
  auction_samples: number
  telemetry_samples: number
  auction_p50_ms: number
  auction_p95_ms: number
  telemetry_p50_ms: number
  telemetry_p95_ms: number
  missed_auction_cycles: number
}

export interface ScenarioStatus {
  name: string
  phase: string
  shock_active: boolean
  shock_label: string
  seed: number
  physics_mode: string
  scenario_id?: string
}

export interface PowerBalance {
  total_demand_kw: number
  available_supply_kw: number
  served_load_kw: number
  unmet_demand_kw: number
  deficit_kw: number
}

export interface TelemetrySnapshot {
  schema_version: string
  timestamp: string
  tick: number
  nodes: GridNode[]
  lines: GridLine[]
  agents: AgentState[]
  order_book: Order[]
  recent_decisions: TradeDecision[]
  power_balance: PowerBalance
  metrics: Metrics
  scenario: ScenarioStatus
  generators?: GeneratorState[]
  event_log?: DecisionEvent[]
}

export interface GeneratorState {
  generator_id: string
  type: 'renewable' | 'conventional'
  node_id: string
  capacity_kw: number
  available_kw: number
  status: string
  allocation_kw: number
  reason: string
}

export interface DecisionEvent {
  decision_id: string
  kind: 'monitoring' | 'allocation' | 'trade' | 'scenario'
  affected_id: string
  decision: string
  reason: string
  timestamp: string
  before: Record<string, number>
  after: Record<string, number>
}

export interface HealthResponse {
  status: string
  physics_mode?: string
  simulator_running?: boolean
  schema_version?: string
}

export type CrisisScenario = 'normal' | 'supply_deficit' | 'supply_40' | 'feeder_loss' | 'feeder_outage' | 'solar_reduction' | 'renewable_drop'

export interface ChaosEvent {
  event_type: 'feeder_loss' | 'feeder_outage' | 'supply_deficit' | 'renewable_drop' | 'clear'
  target_id: string
  magnitude: number
  units: 'fraction'
  seed: number
}

export interface HistoryPoint {
  tick: number
  demand: number
  supply: number
  price: number
  hospital: number
}

export interface Incident {
  id: string
  timestamp: string
  tone: 'info' | 'success' | 'warning' | 'danger'
  title: string
  detail: string
}
