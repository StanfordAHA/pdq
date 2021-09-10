import dataclasses
import itertools
import types
from typing import Iterable, List, Optional

import magma as m
from magma.primitives.register import _CoreIRRegister

from pdq.circuit_tools.circuit_utils import InstSelector
from pdq.circuit_tools.graph_view import (
    BitPortNode, SimpleDirectedGraphViewBase)
from pdq.circuit_tools.signal_path import Scope, ScopedBit, ScopedValue


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


@dataclasses.dataclass(frozen=True)
class ExtractFromTerminalsOpts:
    num_neighbors: int = 0


def _chain_values_as_bits(*values):
    return itertools.chain(*map(m.as_bits, values))


def _find_port_or_die(ifc, name: str):
    """Finds a port with name @name in @ifc"""
    for port_name, port in ifc.ports.items():
        if port.name.name == name:
            return port_name, port
    raise RuntimeError(f"Could not find {name} in {ifc}")


def _clk_type_name(T: m.Kind):
    if T is m.Clock:
        return "CLK"
    raise NotImplementedError(T)


def _lift_extracted_bits_to_ports(bits, qualifier, namer):
    extracted_bit_to_lifted_port_name = {}
    ports = {}
    for i, bit in enumerate(bits):
        # NOTE(rsetaluri): `driven()` should be used in other places, not
        # `value() is not None`.
        # NOTE(rsetaluri): This check is a bit hacky. We should do it in another
        # place or forego it altogether.
        if qualifier is m.In:
            assert not bit.driven()
        name = namer(i, bit)
        ports[name] = qualifier(m.Bit)
        extracted_bit_to_lifted_port_name[bit] = name
    return ports, extracted_bit_to_lifted_port_name


def _get_fanout_sinks(graph, node):
    sinks = []
    work = list(graph.outgoing(node))
    while work:
        curr = work.pop()
        is_sink = (curr.bit.defn is not None or
                   ((curr.bit.inst is not None) and
                    (m.isprimitive(type(curr.bit.inst)))))
        if is_sink:
            sinks += [curr]
            continue
        work += list(graph.outgoing(curr))
    return sinks


def _process_graph(ckt, terminals, opts):
    graph = SimpleDirectedGraphViewBase(ckt)
    node_to_bit = {}
    roots = []
    new_insts = {}


    def _add_or_get_inst(key: ScopedInst):
        try:
            inst = new_insts[key]
        except KeyError:
            name = str(key).replace(".", "_")
            inst = type(key.inst)(name=name)
            new_insts[key] = inst
            return inst, True
        return inst, False


    def _visit_register_output(node):
        assert node.bit.value.is_output()
        key = ScopedInst(node.bit.inst, node.bit.scope)
        extracted_reg, extracted_reg_is_new = _add_or_get_inst(key)
        if extracted_reg_is_new:
            for orig_reg_input_bit in node.bit.inst.I:
                sel = m.value_utils.make_selector(orig_reg_input_bit)
                orig_reg_input_bit_node = BitPortNode(
                    ScopedBit(orig_reg_input_bit, node.bit.scope))
                roots.append(orig_reg_input_bit_node)
                assert orig_reg_input_bit_node not in node_to_bit
                extracted_bit = m.Bit()
                node_to_bit[orig_reg_input_bit_node] = extracted_bit
                sel = m.value_utils.make_selector(orig_reg_input_bit)
                extracted_reg_input_bit = sel.select(extracted_reg.I)
                extracted_reg_input_bit @= extracted_bit
        sel = InstSelector(
            m.value_utils.make_selector(node.bit.value), node.bit.ref.name)
        extracted_reg_input_bit = sel.select(extracted_reg)
        extracted_bit = node_to_bit[node]
        extracted_bit @= extracted_reg_input_bit


    def _visit_register_port(node, flags):
        assert isinstance(type(node.bit.inst), _CoreIRRegister)
        if node.bit.value.is_input():
            # TODO(rsetaluri): The logic below needs to be tested.
            # if node not in terminals:
            #     terminals.append(node)
            # return
            raise NotImplementedError()
        assert node.bit.value.is_output()
        flags.is_register_output = True
        _visit_register_output(node)


    def _visit_primitive_port(node, flags):
        if isinstance(type(node.bit.inst), _CoreIRRegister):
            _visit_register_port(node, flags)
            return
        key = ScopedInst(node.bit.inst, node.bit.scope)
        extracted_prim, _ = _add_or_get_inst(key)
        sel = InstSelector(
            m.value_utils.make_selector(node.bit.value), node.bit.ref.name)
        extracted_prim_port_bit = sel.select(extracted_prim)
        if node.bit.value.is_output():
            flags.is_primitive_output = True
        extracted_bit = node_to_bit[node]
        if extracted_prim_port_bit.is_output():
            extracted_bit @= extracted_prim_port_bit
        else:
            assert extracted_prim_port_bit.is_input()
            extracted_prim_port_bit @= extracted_bit


    def _visit_incoming(node, neighbor, flags):
        extracted_bit = node_to_bit[node]
        if flags.is_primitive_output:
            return
        if neighbor.bit.value.const():
            extracted_driver = neighbor.bit.value
        else:
            # Note that we need to use setdefault() here because we don't know
            # if we've visited this neighbor or not yet.
            extracted_driver = node_to_bit.setdefault(neighbor, m.Bit())
        extracted_bit @= extracted_driver


    work = terminals.copy()
    seen = set()
    while work:
        node = work.pop(0)
        if node in seen:
            continue
        assert node not in seen
        seen.add(node)
        node_to_bit.setdefault(node, m.Bit())
        flags = types.SimpleNamespace(
            is_primitive_output=False, is_register_output=False)
        if node.bit.inst is not None and m.isprimitive(type(node.bit.inst)):
            _visit_primitive_port(node, flags)
        is_root = True
        for neighbor in graph.incoming(node):
            is_root = False
            _visit_incoming(node, neighbor, flags)
            skip_neighbor = (neighbor in seen) or neighbor.bit.value.const()
            if not skip_neighbor:
                work.append(neighbor)
        if is_root and not flags.is_register_output:
            roots.append(node)


    def _get_inst(key):
        return new_insts[key]


    def _expand_neighbors(insts):
        sink_map = {}
        for scoped_inst, new_inst in insts.items():
            bits = filter(
                lambda b: b.is_output(),
                _chain_values_as_bits(
                    *(scoped_inst.inst.interface.ports.values())))
            for bit in bits:
                node = BitPortNode(ScopedBit(bit, scoped_inst.scope))
                sinks = filter(
                    lambda s: s not in node_to_bit,
                    _get_fanout_sinks(graph, node))
                sink_map[node] = sinks
        new_insts = {}
        for node, sinks in sink_map.items():
            if node in node_to_bit:
                driver = node_to_bit[node]
            else:
                driver = m.Bit()
                node_to_bit[node] = driver
                sel = InstSelector(
                    m.value_utils.make_selector(node.bit.value),
                    node.bit.ref.name)
                inst = _get_inst(ScopedInst(node.bit.inst, node.bit.scope))
                driver @= sel.select(inst)
            for sink in sinks:
                if sink.bit.inst is not None:
                    scoped_inst = ScopedInst(sink.bit.inst, sink.bit.scope)
                    new_inst, new_inst_is_new = _add_or_get_inst(scoped_inst)
                    if new_inst_is_new:
                        new_insts[scoped_inst] = new_inst
                    sel = InstSelector(
                        m.value_utils.make_selector(sink.bit.value),
                        sink.bit.ref.name)
                    extracted_sink = sel.select(new_inst)
                    extracted_sink @= driver
                elif sink.bit.defn is not None:
                    extracted_sink = node_to_bit.setdefault(sink, m.Bit())
                    extracted_sink @= driver
                    terminals.append(sink)
                else:
                    raise NotImplementedError(f"Unexpected sink {str(sink)}")
        return new_insts

    curr_neighbors = new_insts.copy()
    for _ in range(opts.num_neighbors):
        curr_neighbors = _expand_neighbors(curr_neighbors)

    return node_to_bit, roots, new_insts


class _PortGrouper:
    def __init__(self, node_to_bit):
        self._groups = {}
        self._node_to_bit = node_to_bit

    def _group_nodes_by_root(self, nodes: Iterable[BitPortNode]):
        for node in nodes:
            # NOTE(rsetaluri): This if statement is a work-around, since
            # `node.bit.ref.value()` doesn't work. In theory, it could, but
            # magma needs to support it.
            if node.bit.inst is not None:
                ifc = node.bit.inst.interface
            else:
                assert node.bit.defn is not None
                ifc = node.bit.defn.interface
            _, port = _find_port_or_die(ifc, node.bit.ref.name)
            key = ScopedValue(port, node.bit.scope)
            group = self._groups.setdefault(key, [])
            group.append(node)

    def add(self, nodes: Iterable[BitPortNode]):
        self._group_nodes_by_root(nodes)

    def make_ports(self):
        ports = {}
        port_name_to_extracted_value = {}
        for key, nodes in self._groups.items():
            port_name = f"{str(key)}".replace(".", "_")
            T = type(key.value)
            assert T is not T.undirected_t  # debug check
            # NOTE(rsetaluri): typed_value is only used as a proxy to get the
            # direction below.
            if key.defn is not None:
                port_type = T.flip()
                typed_value = T()
            else:
                assert key.inst is not None
                port_type = T
                typed_value = T.flip()()
            assert port_name not in ports
            ports[port_name] = port_type
            extracted_value = port_type.undirected_t()
            port_name_to_extracted_value[port_name] = extracted_value
            for node in nodes:
                sel = m.value_utils.make_selector(node.bit.value)
                extracted_bit = sel.select(extracted_value)
                typed_bit = sel.select(typed_value)
                extracted_bit_of_node = self._node_to_bit[node]
                if typed_bit.is_input():
                    assert not extracted_bit.driven()
                    extracted_bit @= extracted_bit_of_node
                else:
                    assert typed_bit.is_output()
                    assert not extracted_bit_of_node.driven()
                    extracted_bit_of_node @= extracted_bit
        return ports, port_name_to_extracted_value


def _extract_from_terminals_impl(
        ckt: m.DefineCircuitKind,
        terminals: List[BitPortNode],
        opts: ExtractFromTerminalsOpts):
    node_to_bit, roots, new_insts = _process_graph(ckt, terminals, opts)

    port_grouper = _PortGrouper(node_to_bit)
    port_grouper.add(roots)
    port_grouper.add(terminals)
    base_ports, base_port_name_to_extracted_value = port_grouper.make_ports()

    inst_bits = list(_chain_values_as_bits(
        *itertools.chain(
            *(inst.interface.ports.values() for inst in new_insts.values()))))
    inputs_to_lift = []
    for port_name, extracted_value in base_port_name_to_extracted_value.items():
        typed_value = base_ports[port_name].flip()()
        values_as_bits = zip(*map(m.as_bits, (typed_value, extracted_value)))
        for typed_bit, extracted_bit in values_as_bits:
            if typed_bit.is_output() or extracted_bit.driven():
                continue
            inputs_to_lift.append(extracted_bit)

    clk_ports = {}
    for bit in filter(lambda b: b.is_input(), inst_bits):
        if isinstance(bit, m.ClockTypes):
            T = type(bit).undirected_t
            clk_ports[_clk_type_name(T)] = m.In(T)
        elif not bit.driven():
            inputs_to_lift.append(bit)

    lifted_inputs, extracted_bit_to_lifted_input_name = (
        _lift_extracted_bits_to_ports(
            inputs_to_lift, m.In, lambda i, _: f"lifted_input{i}"))

    outputs_to_lift = filter(
        lambda b: b.is_output() and not b.driving(), inst_bits)
    lifted_outputs, extracted_bit_to_lifted_output_name = (
        _lift_extracted_bits_to_ports(
            outputs_to_lift, m.Out, lambda i, _: f"lifted_output_{i}"))

    io = m.IO(
        **base_ports,
        **lifted_inputs,
        **lifted_outputs,
        **clk_ports,
    )

    for port_name, value in base_port_name_to_extracted_value.items():
        port = getattr(io, port_name)
        assert type(port).undirected_t is type(value)
        for port_bit, value_bit in zip(m.as_bits(port), m.as_bits(value)):
            if port_bit.is_input():
                port_bit @= value_bit
            else:
                assert port_bit.is_output()
                value_bit @= port_bit
    for bit, port_name in extracted_bit_to_lifted_input_name.items():
        bit @= getattr(io, port_name)
    for bit, port_name in extracted_bit_to_lifted_output_name.items():
        port = getattr(io, port_name)
        port @= bit

    return io


def extract_from_terminals(
        ckt: m.DefineCircuitKind,
        terminals: List[BitPortNode],
        name: Optional[str] = None,
        **kwargs) -> m.DefineCircuitKind:
    name_ = name
    if name_ is None:
        name_ = f"{ckt.name}_Partial"
    opts = ExtractFromTerminalsOpts(**kwargs)

    class _Partial(m.Circuit):
        io = _extract_from_terminals_impl(ckt, terminals, opts)
        name = name_

    return _Partial
