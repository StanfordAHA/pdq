import abc
import dataclasses
from typing import List, Optional, Tuple, Union

import magma as m

from pdq.circuit_tools.circuit_utils import (
    find_defn_ref, find_inst_ref, make_port_selector)
from pdq.common.validator import ValidatorResult, validator


class SignalPath(abc.ABC):
    """An abstract path for a signal"""
    src: m.Bit
    dst: m.Bit
    path: Optional[List['SignalPath']]

    def __eq__(self, _):
        raise NotImplementedError(
            f"{type(self)} does not support __eq__. Use the 'paths_equal' "
            f"method instead")


@dataclasses.dataclass(frozen=True, eq=False)
class InternalSignalPath(SignalPath):
    """Represents a path between instances"""
    src: m.In(m.Bit)
    dst: m.Out(m.Bit)
    path: Optional[List['InternalSignalPath']] = None

    def _validate_impl(self, ckt: m.DefineCircuitKind, curr: m.Bit) -> m.Bit:
        assert isinstance(self.src, m.In(m.Bit))
        assert isinstance(self.dst, m.Out(m.Bit))
        inst = None
        for bit in (self.src, self.dst):
            ref = find_inst_ref(bit)
            assert ref is not None and ref.inst in ckt.instances
            assert inst is None or inst is ref.inst
            inst = ref.inst
        assert self.src.trace() is curr
        if self.path is None:
            return self.dst
        selector = make_port_selector(self.src).child
        curr = selector.select(type(inst))
        for sub_path in self.path:
            assert isinstance(sub_path, InternalSignalPath)
            curr = sub_path._validate_impl(type(inst), curr)
        selector = make_port_selector(self.dst).child
        assert selector.select(type(inst)).trace() is curr
        return self.dst

    @validator
    def validate(self, ckt: m.DefineCircuitKind) -> None:
        self._validate_impl(ckt, self.src)


@dataclasses.dataclass(frozen=True, eq=False)
class TopSignalPath(SignalPath):
    """Represents a top-level path"""
    src: m.Out(m.Bit)
    dst: m.In(m.Bit)
    path: Optional[List[InternalSignalPath]] = None

    @validator
    def validate(self, ckt: m.DefineCircuitKind) -> None:
        assert isinstance(self.src, m.Out(m.Bit))
        assert isinstance(self.dst, m.In(m.Bit))
        for bit in (self.src, self.dst):
            ref = find_defn_ref(bit)
            assert ref is not None and ref.defn is ckt
        curr = self.src
        if self.path is not None:
            for sub_path in self.path:
                assert isinstance(sub_path, InternalSignalPath)
                curr = sub_path._validate_impl(ckt, curr)
        assert self.dst.trace() is curr


def paths_equal(l: SignalPath, r: SignalPath):
    return (
        (type(l) is type(r)) and
        (l.src is r.src and l.dst is r.dst) and
        ((l.path is None and r.path is None) or
         ((isinstance(l.path, list) and isinstance(r.path, list)) and
          (len(l.path) == len(r.path)) and
          (all(paths_equal(lp, rp) for lp, rp in zip(l.path, r.path))))))
