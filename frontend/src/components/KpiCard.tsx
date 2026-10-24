import type { ReactNode } from 'react'

interface KpiCardProps {
  label: string
  value: string
  detail: string
  icon: ReactNode
  tone: 'green' | 'blue' | 'amber' | 'red' | 'purple'
}

export function KpiCard({ label, value, detail, icon, tone }: KpiCardProps) {
  return <article className={`kpi-card kpi-${tone}`}><div className="kpi-icon">{icon}</div><div className="kpi-copy"><span className="label">{label}</span><strong>{value}</strong><small>{detail}</small></div></article>
}
