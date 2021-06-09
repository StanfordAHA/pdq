import dataclasses
from typing import List, Optional, Set, Tuple

import magma as m

from pdq.circuit_tools.circuit_utils import (
    DefnSelector, InstSelector, find_defn_ref, find_inst_ref)
from pdq.circuit_tools.signal_path import (
    SignalPath, TopSignalPath, InternalSignalPath)
from pdq.common.algorithms import try_call
from pdq.common.validator import validator


def _inst_port_to_defn_port(value: m.Type, ref: Optional[m.ref.InstRef] = None):
    if ref is None:
        ref = find_inst_ref(value)
    if ref is None or not isinstance(ref, m.ref.InstRef):
        raise ValueError(f"Unexpected value (value={value}, ref={ref})")
    selector = DefnSelector(m.value_utils.make_selector(value), ref.name)
    return selector.select(type(ref.inst))


def _defn_port_to_inst_port(
        value: m.Type, inst: m.Circuit, ref: Optional[m.ref.InstRef] = None):
    if ref is None:
        ref = find_defn_ref(value)
    check = (ref is None or
             not isinstance(ref, m.ref.DefnRef)
             or not isinstance(inst, ref.defn))
    if check:
        raise ValueError(f"Unexpected value (value={value}, ref={ref})")
    selector = InstSelector(m.value_utils.make_selector(value), ref.name)
    return selector.select(inst)


@dataclasses.dataclass
class SignalPathQuery:
    src: m.Bit
    dst: m.Bit
    thru: Optional[List[m.Circuit]] = None


class _BackwardsPathTracer:
    def __init__(self, ckt: m.DefineCircuitKind):
        self._ckt = ckt

    def _descend(self, ckt: m.DefineCircuitKind) -> bool:
        return m.isdefinition(ckt)

    def run(self, bit: m.Bit):
        if not self._descend(self._ckt):
            paths = []
            for port in self._ckt.interface.outputs():
                for src in m.as_bits(port):
                    paths.append(TopSignalPath(src, bit))
            return paths
        dst = bit
        data = {}
        work = [bit]
        while work:
            bit = work.pop()
            driver = bit.value()
            assert driver is not None
            ref = find_inst_ref(driver)
            if ref is None:  # defn ref
                ref = find_defn_ref(driver)
                assert ref is not None
                data[bit] = driver
                continue
            inst = ref.inst
            assert inst in self._ckt.instances
            it = _BackwardsPathTracer(type(inst))
            defn_bit = _inst_port_to_defn_port(driver, ref)
            paths = it.run(defn_bit)
            paths = list(map(
                lambda path: InternalSignalPath(
                    _defn_port_to_inst_port(path.src, inst),
                    _defn_port_to_inst_port(path.dst, inst),
                    path.path),
                paths))
            data[bit] = paths
            work += list(set(path.src for path in paths))

        out = []

        def _assemble(bit, curr):
            paths = data[bit]
            if isinstance(paths, m.Type):
                out.append(TopSignalPath(paths, dst, curr))
                return
            for path in paths:
                _assemble(path.src, [path] + curr)

        _assemble(dst, [])

        return out


@validator
def validate_query(query: SignalPathQuery, ckt: m.DefineCircuitKind):
    assert isinstance(query.src, m.Out(m.Bit))
    assert isinstance(query.dst, m.In(m.Bit))
    for value in (query.src, query.dst):
        ref = find_defn_ref(value)
        assert ref is not None and ref.defn is ckt
    if not query.thru:
        return
    for inst in query.thru:
        assert inst in ckt.instances


def _filter_instances(path: SignalPath, insts: Set[m.Circuit]):
    if not insts:  # early exit if @insts is empty
        return
    for bit in (path.src, path.dst):
        ref = find_inst_ref(path.src)
        if ref is None:
            continue
        try_call(lambda: insts.remove(ref.inst), KeyError)
    if path.path is None:
        return
    for sub_path in path.path:
        _filter_instances(sub_path, insts)


def _path_is_thru(path: TopSignalPath, thru: List[m.Circuit]):
    insts = set(thru)
    _filter_instances(path, insts)
    return len(insts) == 0


def generate_paths(
        ckt: m.DefineCircuitKind,
        query: SignalPathQuery) -> List[TopSignalPath]:
    valid = validate_query(query, ckt)
    if not valid:
        valid.throw()
    it = _BackwardsPathTracer(ckt)
    paths = it.run(query.dst)
    paths = filter(lambda p: p.src is query.src, paths)
    if query.thru:
        paths = filter(lambda p: _path_is_thru(p, query.thru), paths)
    return list(paths)
