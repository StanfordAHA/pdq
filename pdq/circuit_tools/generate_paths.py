import dataclasses
from typing import List, Optional, Set, Tuple

import magma as m

from pdq.circuit_tools.circuit_utils import find_defn_ref, find_inst_ref
from pdq.circuit_tools.signal_path import (
    SignalPath, TopSignalPath, InternalSignalPath)
from pdq.common.algorithms import try_call
from pdq.common.validator import validator


@dataclasses.dataclass
class SignalPathQuery:
    src: m.Bit
    dst: m.Bit
    thru: Optional[List[m.Circuit]] = None


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

    paths = []

    def _generate(path: List[Tuple[m.Bit, m.Bit]]):
        bit, _ = path[0]
        driver = bit.value()
        if driver is None:
            return
        ref = find_inst_ref(driver)
        if ref is None:
            ref = find_defn_ref(driver)
            if ref is None:
                raise RuntimeError(f"Unexpected ref: {ref}")
            assert ref.defn is ckt
            if driver is query.src:
                paths.append(path)
            return
        inst = ref.inst
        assert inst in ckt.instances
        for port in inst.interface.inputs():
            for new_bit in m.as_bits(port):
                new_path = [(new_bit, driver)] + path
                _generate(new_path)

    _generate([(query.dst, None)])

    paths = ((InternalSignalPath(src, dst) for src, dst in path)
             for path in paths)
    paths = (TopSignalPath(query.src, query.dst, list(path)[:-1]) for path in paths)
    if query.thru:
        paths = filter(lambda p: _path_is_thru(p, query.thru), paths)
    return list(paths)
