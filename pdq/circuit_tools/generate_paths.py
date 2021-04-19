import dataclasses
from typing import List, Optional, Tuple

import magma as m

from pdq.circuit_tools.circuit_utils import find_defn_ref, find_inst_ref
from pdq.circuit_tools.signal_path import SignalPath
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


def _path_is_thru(path: SignalPath, thru: List[m.Circuit]):
    insts = set(thru)
    for in_pin, _ in path.path:
        ref = find_inst_ref(in_pin)
        try:
            insts.remove(ref.inst)
        except KeyError:
            pass
    return len(insts) == 0


def generate_paths(
        ckt: m.DefineCircuitKind, query: SignalPathQuery) -> List[SignalPath]:
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

    paths = (SignalPath(query.src, query.dst, path[:-1]) for path in paths)
    if query.thru:
        paths = filter(lambda p: _path_is_thru(p, query.thru), paths)
    return list(paths)
