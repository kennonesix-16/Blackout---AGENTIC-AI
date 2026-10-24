import { useState } from 'react'
import { BatteryCharging, Building2, HeartPulse, Home, RadioTower, Zap } from 'lucide-react'
import type { GridNode, GridLine } from '../types'

interface TopologyMapProps {
  nodes: GridNode[]
  lines: GridLine[]
  onSelect: (node: GridNode) => void
  selectedId?: string
}

const icons = { hospital: HeartPulse, ev: BatteryCharging, commercial: Building2, residential: Home, substation: RadioTower }

export function TopologyMap({ nodes, lines, onSelect, selectedId }: TopologyMapProps) {
  const byId = Object.fromEntries(nodes.map((node) => [node.id, node]))
  const lineColor = (line: GridLine) => line.status === 'overloaded' ? '#ff5d6c' : line.status === 'warning' ? '#f6ba55' : '#2bd8a5'
  const nodeColor = (node: GridNode) => node.type === 'hospital' ? '#ff5d6c' : node.type === 'ev' ? '#56a8ff' : node.type === 'commercial' ? '#b191ff' : node.type === 'residential' ? '#f6ba55' : '#2bd8a5'

  return <div className="topology-shell"><svg viewBox="0 0 100 100" role="img" aria-label="Interactive eight-node city grid">
    <defs><filter id="glow"><feGaussianBlur stdDeviation="1.5" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
    <g className="grid-lines">{[15, 30, 45, 60, 75, 90].map((step) => <line key={`h-${step}`} x1={step} y1="4" x2={step} y2="96" />)}{[15, 30, 45, 60, 75, 90].map((step) => <line key={`v-${step}`} x1="4" y1={step} x2="96" y2={step} />)}</g>
    {lines.map((line) => { const from = byId[line.from_node]; const to = byId[line.to_node]; if (!from || !to) return null; return <g key={line.id}><line className="feeder-underlay" x1={from.x} y1={from.y} x2={to.x} y2={to.y} /><line className={`feeder ${line.status}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={lineColor(line)} /><text className="line-load" x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 2}>{Math.round(line.loading_pct)}%</text></g> })}
    {nodes.map((node) => { const Icon = icons[node.type as keyof typeof icons] || Zap; const color = nodeColor(node); return <g key={node.id} className={`map-node ${selectedId === node.id ? 'selected' : ''}`} onClick={() => onSelect(node)} tabIndex={0} role="button" aria-label={`Select ${node.label}`} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onSelect(node) }}><circle className="node-halo" cx={node.x} cy={node.y} r="6.5" fill={color} /><circle className="node-core" cx={node.x} cy={node.y} r="4.8" /><foreignObject x={node.x - 2.3} y={node.y - 2.3} width="4.6" height="4.6"><div className="node-icon" style={{ color }}><Icon size={11} /></div></foreignObject><text className="node-label" x={node.x} y={node.y + 10}>{node.label.replace('Residential ', 'Res. ').replace('Commercial ', 'Comm. ')}</text></g> })}
  </svg><div className="map-legend"><span><i className="legend-mark green" />normal feeder</span><span><i className="legend-mark amber" />warning</span><span><i className="legend-mark red" />overloaded</span><span className="map-hint">click a node for telemetry</span></div></div>
}

export function NodeDetails({ node }: { node?: GridNode }) {
  if (!node) return <div className="node-details empty-state">Select a node on the schematic to inspect its live state.</div>
  return <div className="node-details"><div className="detail-heading"><span className={`node-type-dot ${node.type}`} /> <strong>{node.label}</strong><span className="status-chip">{node.status}</span></div><div className="detail-grid"><span>Requested</span><b>{Math.round(node.requested_kw)} kW</b><span>Served</span><b>{Math.round(node.served_kw)} kW</b><span>Unmet</span><b className={node.unmet_kw ? 'text-red' : ''}>{Math.round(node.unmet_kw)} kW</b>{node.soc_pct != null && <><span>Battery SoC</span><b>{Math.round(node.soc_pct)}%</b></>}</div></div>
}
