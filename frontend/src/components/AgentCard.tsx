import { BatteryCharging, Building2, HeartPulse, Home, RadioTower } from 'lucide-react'
import type { AgentState } from '../types'

const details = {
  hospital: { label: 'Hospital Agent', icon: HeartPulse, tone: 'red' },
  ev: { label: 'EV Fleet Agent', icon: BatteryCharging, tone: 'blue' },
  commercial: { label: 'Commercial Agent', icon: Building2, tone: 'purple' },
  residential: { label: 'Residential Agent', icon: Home, tone: 'amber' },
  substation: { label: 'Substation Agent', icon: RadioTower, tone: 'green' },
}

export function AgentCard({ agent }: { agent: AgentState }) {
  const config = details[agent.type as keyof typeof details] || details.substation
  const Icon = config.icon
  const primary = agent.type === 'hospital' ? `${Math.round(agent.served_kw)} / ${Math.round(agent.requested_kw)} kW` : agent.type === 'ev' ? `${Math.round(agent.soc_pct || 0)}% SoC` : agent.type === 'commercial' ? `${Math.round(agent.curtailed_kw)} kW shed` : agent.type === 'residential' ? `${Math.round(agent.requested_kw)} kW load` : 'clearing active'
  const secondary = agent.type === 'hospital' ? `${Math.round(Math.max(0, agent.requested_kw - agent.served_kw))} kW unmet` : agent.type === 'ev' ? `${Math.round(agent.availability_kw)} kW offered` : agent.type === 'commercial' ? 'flexible load committed' : agent.type === 'residential' ? 'transparent local response' : `${Math.round(agent.availability_kw)} kW available`
  return <article className={`agent-card agent-${config.tone}`}><div className="agent-top"><span className="agent-icon"><Icon size={17} /></span><div><strong>{config.label}</strong><small>{agent.policy_note}</small></div><span className="live-dot" /></div><div className="agent-metric"><b>{primary}</b><span>{secondary}</span></div>{agent.type === 'ev' && <div className="progress"><span style={{ width: `${agent.soc_pct || 0}%` }} /></div>}</article>
}
