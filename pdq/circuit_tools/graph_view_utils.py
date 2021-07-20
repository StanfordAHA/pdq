import dataclasses
from typing import Iterable, Tuple

import magma as m

from pdq.circuit_tools.graph_view import (
    SimpleDirectedGraphViewBase, BitPortNode)
from pdq.circuit_tools.signal_path import Scope, ScopedBit


NodeType = BitPortNode
EdgeType = Tuple[NodeType, NodeType]


def materialize_graph(
        defn: m.DefineCircuitKind) -> (Iterable[NodeType], Iterable[EdgeType]):
    seen = set()
    node_indices = {}  # in order to get consistently ordered vertices
    edges = []
    queue = []
    for port in defn.interface.ports.values():
        for bit in m.as_bits(port):
            node = BitPortNode(ScopedBit(bit, Scope(defn)))
            queue.append(node)
    graph = SimpleDirectedGraphViewBase(defn)
    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.add(node)
        node_indices[node] = len(node_indices)
        for i in graph.incoming(node):
            edges.append((i, node))
            if i not in seen:
                queue.append(i)
        for o in graph.outgoing(node):
            if o not in seen:
                queue.append(o)
    assert len(node_indices) == len(seen)
    nodes = sorted(list(seen), key=lambda n: node_indices[n])
    return nodes, edges
