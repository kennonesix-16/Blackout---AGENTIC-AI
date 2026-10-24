import type { Order, TradeDecision } from '../types'

export function OrderBook({ orders, decisions }: { orders: Order[]; decisions: TradeDecision[] }) {
  const sells = orders.filter((order) => order.side === 'sell').sort((a, b) => a.price_per_kwh - b.price_per_kwh)
  const buys = orders.filter((order) => order.side === 'buy').sort((a, b) => b.price_per_kwh - a.price_per_kwh)
  const midpoint = sells[0] && buys[0] ? (sells[0].price_per_kwh + buys[0].price_per_kwh) / 2 : 0
  return <div className="order-book"><div className="book-columns"><div><div className="book-title ask">ASKS · SELLERS</div>{sells.map((order) => <div className="book-row" key={order.id}><span>{order.agent_type}</span><b>₹{order.price_per_kwh.toFixed(2)}</b><small>{Math.round(order.quantity_kw)} kW</small></div>)}</div><div><div className="book-title bid">BIDS · BUYERS</div>{buys.map((order) => <div className="book-row" key={order.id}><span>{order.agent_type}</span><b>₹{order.price_per_kwh.toFixed(2)}</b><small>{Math.round(order.quantity_kw)} kW</small></div>)}</div></div><div className="book-midpoint"><span>MODELED CLEARING MIDPOINT</span><strong>₹{midpoint.toFixed(2)}<small>/kWh</small></strong><em>{decisions.filter((decision) => decision.accepted).length} accepted · {decisions.filter((decision) => !decision.accepted).length} rejected</em></div></div>
}
