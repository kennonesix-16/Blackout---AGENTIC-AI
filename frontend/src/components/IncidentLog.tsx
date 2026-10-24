import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from 'lucide-react'
import type { Incident } from '../types'

const icons = { info: Info, success: CheckCircle2, warning: ShieldAlert, danger: AlertTriangle }
export function IncidentLog({ incidents }: { incidents: Incident[] }) {
  return <div className="incident-log">{incidents.slice(0, 7).map((incident) => { const Icon = icons[incident.tone]; return <div className="incident" key={incident.id}><span className={`incident-icon ${incident.tone}`}><Icon size={14} /></span><div><div className="incident-title"><strong>{incident.title}</strong><time>{incident.timestamp}</time></div><p>{incident.detail}</p></div></div> })}</div>
}
