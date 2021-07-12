import abc
import dataclasses
from typing import Iterable, Union

import magma as m

from pdq.circuit_tools.circuit_utils import (
    find_inst_ref, find_defn_ref, inst_port_to_defn_port,
    defn_port_to_inst_port)
from pdq.circuit_tools.signal_path import ScopedBit
from pdq.common.validator import validator


class NodeInterface(abc.ABC):
    # @abc.abstractmethod
    # def __eq__(self, other: 'NodeInterface') -> bool:
    #     raise NotImplementedError()

    # @abc.abstractmethod
    # def __hash__(self) -> int:
    #     raise NotImplementedError()
    pass


class GraphInterface(abc.ABC):
    @abc.abstractmethod
    def neighbors(self, node: NodeInterface) -> Iterable[NodeInterface]:
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True, eq=True)
class BitPortNode(NodeInterface):
    bit: ScopedBit

    def __str__(self):
        return str(self.bit)


class SimpleGraphViewBase(GraphInterface):
    def __init__(self, ckt: m.DefineCircuitKind):
        self._ckt = ckt

    def neighbors(self, node: BitPortNode) -> Iterable[BitPortNode]:
        # TODO(rsetaluri): Check that this node is contained in ckt.
        if node.bit.defn is not None:
            # We can safely assume that any neighbor will have the same scope as
            # this node, since all connections are to other top-level defn ports
            # or singly nested inst ports.
            scope = node.bit.scope
            if node.bit.value.is_input():
                driver = node.bit.value.trace()
                if driver is None:
                    yield from ()
                    return
                yield BitPortNode(ScopedBit(driver, scope))
                return
            assert node.bit.value.is_output()  # no support for InOut types
            for drivee in node.bit.value.driving():
                yield BitPortNode(ScopedBit(drivee, scope))
            return
        assert node.bit.inst is not None  # no support for anon bits
        if node.bit.value.is_output():
            for drivee in node.bit.value.driving():
                ref = find_inst_ref(drivee)
                if ref is not None:
                    yield BitPortNode(ScopedBit(drivee, node.bit.scope))
                    continue
                ref = find_defn_ref(drivee)
                assert ref is not None  # no support for anon bits
                if node.bit.scope.is_root():
                    # TODO(rsetaluri): Implement this case.
                    raise NotImplementedError()
                else:
                    scope, inst = node.bit.scope.pop()
                    drivee = defn_port_to_inst_port(drivee, inst)
                yield BitPortNode(ScopedBit(drivee, scope))
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
                yield from ()
                return
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
        # TODO(rsetaluri): Check for primitive-ness of type.
        # TODO(rsetaluri): Get primitive drivees.
        driver = node.bit.value.trace()
        if driver is None:
            yield from ()
            return
        yield BitPortNode(ScopedBit(driver, node.bit.scope))
        return
        # TODO(rsetaluri): Implement remaining cases.
        raise NotImplementedError()

    def _get_primitive_drivers(
            self,
            primitive: m.DefineCircuitKind,
            inst_bit: m.Out(m.Bit)) -> Iterable[m.Bit]:
        assert inst_bit.is_output()
        for port in primitive.interface.ports.values():
            port_as_bits = m.as_bits(port)
            for other_bit in port_as_bits:
                if other_bit.is_output():
                    yield other_bit
