from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class NodeSpec:
    id: str
    label: str
    type: str
    x: float
    y: float


@dataclass(frozen=True)
class LineSpec:
    id: str
    from_node: str
    to_node: str
    capacity_kw: float


NODES = [
    NodeSpec("substation-east", "Substation East", "substation", 12, 48),
    NodeSpec("substation-west", "Substation West", "substation", 12, 78),
    NodeSpec("hospital", "Ward 4 Hospital", "hospital", 52, 48),
    NodeSpec("ev-depot", "EV Fleet Depot", "ev", 52, 78),
    NodeSpec("commercial-north", "Commercial North", "commercial", 82, 26),
    NodeSpec("commercial-south", "Commercial South", "commercial", 82, 54),
    NodeSpec("residential-north", "Residential North", "residential", 82, 78),
    NodeSpec("residential-south", "Residential South", "residential", 82, 92),
]

LINES = [
    LineSpec("line-east-hospital", "substation-east", "hospital", 420),
    LineSpec("line-west-ev", "substation-west", "ev-depot", 300),
    LineSpec("line-hospital-commercial-n", "hospital", "commercial-north", 150),
    LineSpec("line-hospital-commercial-s", "hospital", "commercial-south", 160),
    LineSpec("line-ev-residential-n", "ev-depot", "residential-north", 50),
    LineSpec("line-ev-residential-s", "ev-depot", "residential-south", 110),
    LineSpec("line-east-west-tie", "substation-east", "substation-west", 240),
]


def build_graph() -> nx.Graph:
    graph = nx.Graph()
    for node in NODES:
        graph.add_node(node.id, label=node.label, type=node.type, x=node.x, y=node.y)
    for line in LINES:
        graph.add_edge(line.from_node, line.to_node, id=line.id, capacity_kw=line.capacity_kw)
    return graph


GRAPH = build_graph()
