import dataclasses
import itertools
import networkx as nx
from typing import Callable, Iterable, List, Optional, Tuple

import magma as m

from pdq.circuit_tools.circuit_utils import InstSelector
from pdq.circuit_tools.graph_view import (
    BitPortNode, SimpleDirectedGraphViewBase)
from pdq.circuit_tools.graph_view_utils import materialize_graph
from pdq.circuit_tools.partial_extract_query import (
    PartialExtractQuery, query_is_empty)
from pdq.circuit_tools.signal_path import Scope, ScopedBit, ScopedValue
from pdq.common.algorithms import only, remove_all


Graph = nx.DiGraph


@dataclasses.dataclass(frozen=True)
class ScopedInst:
    inst: m.Circuit
    scope: Scope

    def __str__(self) -> str:
        return f"{str(self.scope)}.{self.inst.name}"

    def __eq__(self, other: 'ScopedInst') -> bool:
        if not isinstance(other, ScopedInst):
            return NotImplemented
        return self.inst is other.inst and self.scope == other.scope

    def __ne__(self, other: 'ScopedInst') -> bool:
        if not isinstance(other, ScopedInst):
            return NotImplemented
        return not self == other


class _CircuitReconstructor:
    def __init__(self, graph: Graph):
        self._graph = graph
        self._node_to_bit = {}
        self._instance_map = {}

    def find_node(self, bit: m.Bit) -> BitPortNode:
        node_to_bit = {n: b for n, b in self._node_to_bit.items() if b is bit}
        n, b = only(node_to_bit.items())
        assert b is bit
        return n

    @property
    def node_to_bit(self):
        return self._node_to_bit

    @property
    def instance_map(self):
        return self._instance_map

    def add_or_get_bit(self, key: BitPortNode) -> m.Bit:
        return self._node_to_bit.setdefault(key, m.Bit())

    def get_bit(self, key: BitPortNode) -> m.Bit:
        return self._node_to_bit[key]

    def add_or_get_instance(self, key: ScopedInst) -> m.Circuit:
        try:
            inst = self._instance_map[key]
        except KeyError:
            name = str(key).replace(".", "_")
            inst = type(key.inst)(name=name)
            self._instance_map[key] = inst
            return inst
        return inst

    def run(self):
        for node in self._graph.nodes:
            bit = self.add_or_get_bit(node)
            if node.bit.inst is not None:
                key = ScopedInst(node.bit.inst, node.bit.scope)
                sel = InstSelector(
                    m.value_utils.make_selector(node.bit.value),
                    node.bit.ref.name)
                if m.isprimitive(type(key.inst)):
                    if node.bit.value.is_input():
                        inst = self.add_or_get_instance(key)
                        inst_bit = sel.select(inst)
                        inst_bit @= bit
                    else:
                        assert node.bit.value.is_output()
                        if self._graph.in_degree(node) > 0:
                            inst = self.add_or_get_instance(key)
                            inst_bit = sel.select(inst)
                            bit @= inst_bit
                        continue
            for predecessor in self._graph.predecessors(node):
                predecessor_bit = self.add_or_get_bit(predecessor)
                bit @= predecessor_bit


def _reachable_from(graph: Graph, src: BitPortNode) -> Iterable[BitPortNode]:
    seen = set()
    stack = [src]
    while stack:
        curr = stack.pop()
        if not graph.has_node(curr):
            continue
        if curr in seen:
            continue
        yield curr
        seen.add(curr)
        stack += list(graph.successors(curr))


def _reaches_to(graph: Graph, dst: BitPortNode) -> Iterable[BitPortNode]:
    seen = set()
    stack = [dst]
    while stack:
        curr = stack.pop()
        if not graph.has_node(curr):
            continue
        if curr in seen:
            continue
        yield curr
        seen.add(curr)
        stack += list(graph.predecessors(curr))


def _subgraph(graph: Graph, nodes: Iterable[BitPortNode]) -> Graph:
    """
    Returns a *consistently ordered* subgraph of @graph induced by the set of
    nodes @nodes. Note that we can not use nx.Graph.subgraph since it has shown
    to be non-deterministic in terms of subgraph node ordering.
    """
    subgraph = graph.copy()
    nodes_set = set(nodes)
    subgraph.remove_nodes_from(n for n in graph if n not in nodes_set)
    return subgraph


def _filter_graph(graph: Graph, query: PartialExtractQuery) -> Graph:

    def _filter(g, fn, l):
        return itertools.chain(*(fn(g, BitPortNode(bit)) for bit in l))

    if query.from_list:
        nodes = _filter(graph, _reachable_from, query.from_list)
        graph = _subgraph(graph, nodes)
    if query.to_list:
        nodes = _filter(graph, _reaches_to, query.to_list)
        graph = _subgraph(graph, nodes)
    if query.through_lists:
        for through_list in query.through_lists:
            nodes = itertools.chain(
                _filter(graph, _reaches_to, through_list),
                _filter(graph, _reachable_from, through_list))
            graph = _subgraph(graph, nodes)
    return graph


def _lift_instance_inputs(
        reconstructor: _CircuitReconstructor) -> (
            Tuple[List[BitPortNode], List[BitPortNode]]):
    pi = []
    po = []

    def _process_value(value, scoped_inst, inst):
        node = BitPortNode(ScopedBit(value, scoped_inst.scope))
        sel = InstSelector(
            m.value_utils.make_selector(node.bit.value),
            node.bit.ref.name)
        if value.is_input():
            if isinstance(value, m.ClockTypes):
                return
            if node in reconstructor.node_to_bit:
                assert reconstructor.node_to_bit[node].driven()
                return
            assert node not in reconstructor.node_to_bit
            new_value = reconstructor.add_or_get_bit(node)
            inst_value = sel.select(inst)
            assert not inst_value.driven()
            inst_value @= new_value
            pi.append(node)
        elif value.is_output():
            if node in reconstructor.node_to_bit:
                return
            new_value = reconstructor.add_or_get_bit(node)
            inst_value = sel.select(inst)
            assert not inst_value.driving()
            new_value @= inst_value
            po.append(node)
        else:
            raise NotImplementedError(value, type(value))

    for scoped_inst, inst in reconstructor.instance_map.items():
        for port in scoped_inst.inst.interface.ports.values():
            for bit in m.as_bits(port):
                _process_value(bit, scoped_inst, inst)

    return pi, po


def _is_register_port(
        node: BitPortNode,
        value_predicate: Optional[Callable[[m.Type], bool]] = None) -> bool:
    from magma.primitives.register import _CoreIRRegister
    if value_predicate is not None and not value_predicate(node.bit.value):
        return False
    inst = node.bit.inst
    if inst is None:
        return False
    defn = type(inst)
    if not m.isprimitive(defn):
        return False
    if not isinstance(defn, _CoreIRRegister):
        return False
    return True


def _is_register_input(node: BitPortNode) -> bool:
    return _is_register_port(node, lambda v: v.is_output())


def _is_register_output(node: BitPortNode) -> bool:
    return _is_register_port(node, lambda v: v.is_input())


def _add_input_registers(
        graph: Graph,
        reconstructor: _CircuitReconstructor) -> List[BitPortNode]:
    pi_to_remove = []
    for node in graph.nodes:
        if not _is_register_input(node):
            continue
        scoped_inst = ScopedInst(node.bit.inst, node.bit.scope)
        assert node not in reconstructor.instance_map
        inst = reconstructor.add_or_get_instance(scoped_inst)
        sel = InstSelector(
            m.value_utils.make_selector(node.bit.value),
            node.bit.ref.name)
        inst_bit = sel.select(inst)
        bit = reconstructor.get_bit(node)
        bit @= inst_bit
        pi_to_remove.append(node)
    return pi_to_remove


def _reconstruct_circuit(graph: Graph, name: str) -> m.DefineCircuitKind:
    reconstructor = _CircuitReconstructor(graph)

    def _make_terminals(fn, g):
        return list(filter(lambda n: fn(g, n), g.nodes))

    def _is_po(g, n):
        return g.out_degree(n) == 0 and (not _is_register_output(n))

    pi = _make_terminals(lambda g, n: g.in_degree(n) == 0, graph)
    po = _make_terminals(_is_po, graph)
    _name = name


    class _Partial(m.Circuit):
        nonlocal pi
        nonlocal po
        reconstructor.run()
        pi_to_remove = _add_input_registers(graph, reconstructor)
        remove_all(pi, pi_to_remove)
        new_pi, new_po = _lift_instance_inputs(reconstructor)
        pi += new_pi
        po += new_po

        io =  m.IO(**{f"I{i}":  m.In(type(v.bit.value))
                      for i, v in enumerate(pi)})
        io += m.IO(**{f"O{i}": m.Out(type(v.bit.value))
                      for i, v in enumerate(po)})
        for i, pii in enumerate(pi):
            port = getattr(io, f"I{i}")
            bit = reconstructor.get_bit(pii)
            bit @= port
        for i, pio in enumerate(po):
            port = getattr(io, f"O{i}")
            bit = reconstructor.get_bit(pio)
            port @= bit
        name = _name

    return _Partial


def extract_partial(
        ckt: m.DefineCircuitKind,
        query: PartialExtractQuery,
        name: Optional[str] = None) -> m.DefineCircuitKind:
    if query_is_empty(query):
        raise ValueError("Can not extract from empty query")
    if name is None:
        name = f"{ckt.name}_Partial"
    graph = Graph()
    V, E = materialize_graph(ckt)
    graph.add_nodes_from(V)
    graph.add_edges_from(E)
    subgraph = _filter_graph(graph, query)
    partial = _reconstruct_circuit(subgraph, name)
    return partial
