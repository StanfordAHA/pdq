import dataclasses
from typing import Iterable, Tuple

import magma as m

from pdq.circuit_tools.circuit_utils import (
    find_instances_name_equals, find_inst_ref)
from pdq.circuit_tools.graph_view import (
    SimpleDirectedGraphViewBase, BitPortNode)
from pdq.circuit_tools.signal_path import Scope, ScopedBit
from pdq.common.algorithms import only


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


def make_scoped_bit(defn: m.DefineCircuitKind, path: str) -> ScopedBit:
    parts = path.split(".")
    if parts.pop(0) != defn.name:
        raise ValueError(f"Expected path to start with {defn.name}")
    port_or_net_name = parts.pop()
    scope_path = []
    curr = defn
    while parts:
        inst_name = parts.pop(0)
        inst = only(find_instances_name_equals(curr, inst_name))
        scope_path.append(inst)
        curr = type(inst)
    if curr is defn:
        bit = getattr(defn, port_or_net_name)
    else:
        bit = getattr(inst, port_or_net_name)
        ref = find_inst_ref(bit)
        err_msg = f"Unsupported path ({path})"
        if ref is None:
            raise NotImplementedError(err_msg)
        if ref.inst is not inst:
            if ref.inst.defn is not type(inst):
                raise NotImplementedError(err_msg)
        else:
            scope_path.pop()    
    return ScopedBit(bit, Scope(defn, tuple(scope_path)))
