import { ArrowRight, CheckCircle2, Network, ShieldAlert, Thermometer } from 'lucide-react'
import { explainDecision } from '../services/decisionExplain'
import type { TelemetrySnapshot, TradeDecision } from '../types'

export function DecisionInspector({ snapshot, decision, onSelect }: { snapshot: TelemetrySnapshot; decision?: TradeDecision; onSelect: (decision: TradeDecision) => void }) {
  const decisions = snapshot.recent_decisions.slice(0, 8)
  if (!decision) return <div className="decision-inspector empty-state">The governor decision panel will populate after the first auction cycle.</div>
  const explanation = explainDecision(decision, snapshot)
  const { limitingLine } = explanation
  return <div className="decision-inspector">
    <div className="decision-tabs">{decisions.map((item) => <button className={item.trade_id === decision.trade_id ? 'selected' : ''} key={item.trade_id} onClick={() => onSelect(item)}><span className={item.accepted ? 'tab-dot accepted' : 'tab-dot rejected'} />{item.accepted ? 'ACCEPTED' : 'REJECTED'}<small>{Math.round(item.quantity_kw)} kW</small></button>)}</div>
    <div className={`decision-banner ${decision.accepted ? 'accepted' : 'rejected'}`}><span className="decision-banner-icon">{decision.accepted ? <CheckCircle2 size={17} /> : <ShieldAlert size={17} />}</span><div><span className="eyebrow">{explanation.outcomeLabel}</span><strong>{decision.seller_id} <ArrowRight size={13} /> {decision.buyer_id}</strong></div><b>{Math.round(decision.quantity_kw)} kW</b></div>
    <div className="decision-facts"><div><span><Network size={13} /> affected path</span><strong>{explanation.path.length ? explanation.path.map((node) => node.label).join(' → ') : 'Path unavailable in snapshot'}</strong></div><div><span><Thermometer size={13} /> governor reason</span><strong>{explanation.reasonLabel}</strong></div>{limitingLine && <div><span><ShieldAlert size={13} /> limiting feeder</span><strong>{limitingLine.id} · {Math.round(limitingLine.loading_pct)}% loaded / {Math.round(limitingLine.capacity_kw)} kW rated</strong></div>}</div>
    <p className="decision-note">{decision.accepted ? 'The modeled governor allowed this trade because the simulated path stayed within its conservative capacity checks.' : 'The modeled governor blocked this trade before allocation because the simulated feeder constraint would be exceeded.'}</p>
  </div>
}
