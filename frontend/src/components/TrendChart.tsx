import type { HistoryPoint } from '../types'

export function TrendChart({ points }: { points: HistoryPoint[] }) {
  const values = points.length ? points : [{ tick: 0, demand: 0, supply: 0, price: 0, hospital: 0 }]
  const maxPower = Math.max(1000, ...values.flatMap((point) => [point.demand, point.supply]))
  const width = 600
  const height = 190
  const x = (index: number) => 18 + (index / Math.max(values.length - 1, 1)) * 560
  const y = (value: number) => 160 - (value / maxPower) * 120
  const path = (key: 'demand' | 'supply') => values.map((point, index) => `${index ? 'L' : 'M'} ${x(index)} ${y(point[key])}`).join(' ')
  const latest = values[values.length - 1]
  return <div className="chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Demand and supply history"><g className="chart-grid">{[0, 1, 2, 3].map((step) => <line key={step} x1="18" y1={40 + step * 40} x2="578" y2={40 + step * 40} />)}</g><path d={path('demand')} className="chart-line demand" /><path d={path('supply')} className="chart-line supply" /><text className="chart-axis" x="18" y="181">T-{values.length}</text><text className="chart-axis" x="554" y="181">NOW</text></svg><div className="chart-legend"><span><i className="legend-line red" />demand</span><span><i className="legend-line green" />available supply</span><b>{Math.round(latest?.demand || 0)} kW demand</b></div></div>
}

export function PriceChart({ points }: { points: HistoryPoint[] }) {
  const values = points.length ? points : [{ tick: 0, demand: 0, supply: 0, price: 0, hospital: 0 }]
  const max = Math.max(30, ...values.map((point) => point.price))
  const x = (index: number) => 18 + (index / Math.max(values.length - 1, 1)) * 560
  const y = (value: number) => 160 - (value / max) * 120
  const path = values.map((point, index) => `${index ? 'L' : 'M'} ${x(index)} ${y(point.price)}`).join(' ')
  const latest = values[values.length - 1]
  return <div className="chart-wrap"><svg viewBox="0 0 600 190" role="img" aria-label="Market clearing price history"><g className="chart-grid">{[0, 1, 2, 3].map((step) => <line key={step} x1="18" y1={40 + step * 40} x2="578" y2={40 + step * 40} />)}</g><path d={path} className="chart-line price" /><text className="chart-axis" x="18" y="181">T-{values.length}</text><text className="chart-axis" x="554" y="181">NOW</text></svg><div className="chart-legend"><span><i className="legend-line blue" />clearing price</span><b>₹{(latest?.price || 0).toFixed(2)} / kWh</b></div></div>
}
