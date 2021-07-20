import abc
import dataclasses
from typing import Iterable, Union

import magma as m

from pdq.circuit_tools.circuit_primitives import get_primitive_drivers
from pdq.circuit_tools.circuit_utils import (
    find_inst_ref, find_defn_ref, inst_port_to_defn_port,
    defn_port_to_inst_port)
from pdq.circuit_tools.signal_path import Scope, ScopedBit
from pdq.common.validator import validator


def _empty() -> Iterable:
    yield from ()


def _trace_drivees(bit: m.Bit) -> Iterable[m.Bit]:
    drivees = bit.driving()
    if not drivees:
        return _empty()
    for drivee in drivees:
        if drivee.is_input() or drivee.is_inout():
            yield drivee
            continue
        yield from _trace_drivees(drivee)


class NodeInterface(abc.ABC):
    # NOTE(rsetaluri): We'd like this class to have abstract methods __eq__ and
    # __hash__, but unfortunately implementations relying on dataclass
    # implementations trigger the abstract class instantiation TypeError.
    pass


class GraphInterface(abc.ABC):
    @abc.abstractmethod
    def neighbors(self, node: NodeInterface) -> Iterable[NodeInterface]:
        raise NotImplementedError()


class DirectedGraphInterface(GraphInterface):
    @abc.abstractmethod
    def incoming(self, node: NodeInterface) -> Iterable[NodeInterface]:
        raise NotImplementedError()

    @abc.abstractmethod
    def outgoing(self, node: NodeInterface) -> Iterable[NodeInterface]:
        raise NotImplementedError()

    def neighbors(self, node: NodeInterface) -> Iterable[NodeInterface]:
        """Default implementation just defers to incoming/outgoing methods."""
        yield from self.incoming(node)
        yield from self.outgoing(node)


@dataclasses.dataclass(frozen=True, eq=True)
class BitPortNode(NodeInterface):
    bit: ScopedBit

    def __str__(self):
        return str(self.bit)


class SimpleDirectedGraphViewBase(DirectedGraphInterface):
    def __init__(self, ckt: m.DefineCircuitKind):
        self._ckt = ckt

    def incoming(self, node: NodeInterface) -> Iterable[NodeInterface]:
        return self._neighbors_impl(
            node, include_incoming=True, include_outgoing=False)

    def outgoing(self, node: NodeInterface) -> Iterable[NodeInterface]:
        return self._neighbors_impl(
            node, include_incoming=False, include_outgoing=True)

    def neighbors(self, node: NodeInterface) -> Iterable[NodeInterface]:
        return self._neighbors_impl(
            node, include_incoming=True, include_outgoing=True)

    def _neighbors_impl(
            self,
            node: BitPortNode,
            include_incoming: bool,
            include_outgoing: bool) -> Iterable[BitPortNode]:
        if not (include_incoming or include_outgoing):
            return _empty()
        # TODO(rsetaluri): Check that this node is contained in ckt.
        if node.bit.defn is not None:
            # We can safely assume that any neighbor will have the same scope as
            # this node, since all connections are to other top-level defn ports
            # or singly nested inst ports.
            scope = node.bit.scope
            if node.bit.value.is_input():
                if include_incoming:
                    driver = node.bit.value.trace()
                    if driver is None:
                        return _empty
                    if driver.const():
                        yield BitPortNode(ScopedBit(driver, Scope(None)))
                        return _empty()
                    yield BitPortNode(ScopedBit(driver, scope))
                return
            assert node.bit.value.is_output()  # no support for InOut types
            if include_outgoing:
                for drivee in _trace_drivees(node.bit.value):
                    yield BitPortNode(ScopedBit(drivee, scope))
            return
        assert node.bit.inst is not None  # no support for anon bits
        if node.bit.value.is_output():
            if include_outgoing:
                for drivee in _trace_drivees(node.bit.value):
                    ref = find_inst_ref(drivee)
                    if ref is not None:
                        yield BitPortNode(ScopedBit(drivee, node.bit.scope))
                        continue
                    ref = find_defn_ref(drivee)
                    assert ref is not None  # no support for anon bits
                    if node.bit.scope.is_root():
                        scope = node.bit.scope
                    else:
                        scope, inst = node.bit.scope.pop()
                        drivee = defn_port_to_inst_port(drivee, inst)
                    yield BitPortNode(ScopedBit(drivee, scope))
            if include_incoming:
                type_ = type(node.bit.inst)
                if not m.isdefinition(type_):  # primitive instance case
                    drivers = self._get_primitive_drivers(type_, node.bit.value)
                    for driver in drivers:
                        driver = defn_port_to_inst_port(driver, node.bit.inst)
                        yield BitPortNode(ScopedBit(driver, node.bit.scope))
                    return
                # Non-primitive instance case; we descend into the definition.
                defn_port = inst_port_to_defn_port(node.bit.value, node.bit.ref)
                driver = defn_port.trace()
                if driver is None:
                    return _empty()
                if driver.const():
                    yield BitPortNode(ScopedBit(driver, Scope(None)))
                    return _empty()
                ref = find_defn_ref(driver)
                if ref is not None:
                    # TODO(rsetaluri): Implement this case.
                    raise NotImplementedError()
                ref = find_inst_ref(driver)
                assert ref is not None  # no support for anon bits
                scope = node.bit.scope.extend(node.bit.inst)
                yield BitPortNode(ScopedBit(driver, scope))
            return
        assert node.bit.value.is_input()  # no support for InOut types
        if include_incoming:
            driver = node.bit.value.trace()
            if driver is None:
                yield from _empty()
            elif driver.const():
                yield BitPortNode(ScopedBit(driver, Scope(None)))
            else:
                ref = find_defn_ref(driver)
                if ref is not None:
                    if node.bit.scope.is_root():
                        scope = node.bit.scope
                    else:
                        scope, inst = node.bit.scope.pop()
                        driver = defn_port_to_inst_port(driver, inst)
                    yield BitPortNode(ScopedBit(driver, scope))
                else:
                    ref = find_inst_ref(driver)
                    assert ref is not None  # no support for anon bits
                    yield BitPortNode(ScopedBit(driver, node.bit.scope))
        if include_outgoing:
            type_ = type(node.bit.inst)
            if not m.isdefinition(type_):  # primitive instance case
                drivees = self._get_primitive_drivees(type_, node.bit.value)
                for drivee in drivees:
                    drivee = defn_port_to_inst_port(drivee, node.bit.inst)
                    yield BitPortNode(ScopedBit(drivee, node.bit.scope))
                return
            defn_port = inst_port_to_defn_port(node.bit.value, node.bit.ref)
            for drivee in _trace_drivees(defn_port):
                ref = find_defn_ref(drivee)
                if ref is not None:
                    # TODO(rsetaluri): Implement this case.
                    raise NotImplementedError()
                ref = find_inst_ref(drivee)
                assert ref is not None  # no support for anon bits
                scope = node.bit.scope.extend(node.bit.inst)
                yield BitPortNode(ScopedBit(drivee, scope))
        return
        # TODO(rsetaluri): Implement remaining cases.
        raise NotImplementedError()

    def _get_primitive_drivers(
            self,
            primitive: m.DefineCircuitKind,
            inst_bit: m.Out(m.Bit)) -> Iterable[m.Bit]:
        assert inst_bit.is_output()
        defn_bit = inst_port_to_defn_port(inst_bit)
        return get_primitive_drivers(defn_bit, allow_default=False)

    def _get_primitive_drivees(
            self,
            primitive: m.DefineCircuitKind,
            inst_bit: m.In(m.Bit)) -> Iterable[m.Bit]:
        assert inst_bit.is_input()
        for port in primitive.interface.ports.values():
            port_as_bits = m.as_bits(port)
            for other_bit in port_as_bits:
                if other_bit.is_input():
                    yield other_bit
