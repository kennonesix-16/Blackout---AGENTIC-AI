import type { GridLine, GridNode, TelemetrySnapshot, TradeDecision } from '../types'

export interface DecisionExplanation {
  decision: TradeDecision
  buyer?: GridNode
  seller?: GridNode
  path: GridNode[]
  limitingLine?: GridLine
  reasonLabel: string
  outcomeLabel: string
}

function findNode(snapshot: TelemetrySnapshot, agentType: string, line?: GridLine) {
  const agent = snapshot.agents.find((candidate) => candidate.type === agentType && (!line || candidate.node_id === line.from_node || candidate.node_id === line.to_node))
    || snapshot.agents.find((candidate) => candidate.type === agentType)
  return snapshot.nodes.find((node) => node.id === agent?.node_id)
}

function findPath(nodes: GridNode[], lines: GridLine[], startId?: string, endId?: string) {
  if (!startId || !endId) return []
  const queue: string[][] = [[startId]]
  const visited = new Set([startId])
  while (queue.length) {
    const path = queue.shift()!
    const current = path[path.length - 1]
    if (current === endId) return path.map((id) => nodes.find((node) => node.id === id)).filter((node): node is GridNode => Boolean(node))
    for (const line of lines) {
      const next = line.from_node === current ? line.to_node : line.to_node === current ? line.from_node : undefined
      if (next && !visited.has(next)) {
        visited.add(next)
        queue.push([...path, next])
      }
    }
  }
  return []
}

export function explainDecision(decision: TradeDecision, snapshot: TelemetrySnapshot): DecisionExplanation {
  const lineId = decision.reason.match(/line ([^ ]+)/)?.[1]
  const limitingLine = snapshot.lines.find((line) => line.id === lineId)
  const buyer = findNode(snapshot, decision.buyer_id, limitingLine)
  const seller = findNode(snapshot, decision.seller_id, limitingLine)
  const path = findPath(snapshot.nodes, snapshot.lines, seller?.id, buyer?.id)
  const reasonLabel = decision.accepted
    ? `Path and capacity checks passed for ${Math.round(decision.quantity_kw)} kW.`
    : decision.reason.replace(/^line [^ ]+ /, '')
  const outcomeLabel = decision.accepted ? 'Governor accepted' : 'Governor rejected'
  return { decision, buyer, seller, path, limitingLine, reasonLabel, outcomeLabel }
}
