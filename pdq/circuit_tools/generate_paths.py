import dataclasses
import random
from typing import List, Optional, Set, Tuple

import magma as m

from pdq.circuit_tools.circuit_primitives import get_primitive_drivers
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
            srcs = get_primitive_drivers(bit, allow_default=False)
            return [TopSignalPath(src, bit) for src in srcs]
        dst = bit
        data = {}
        work = [bit]
        while work:
            bit = work.pop()
            if bit in data:  # skip bits we've already seen
                continue
            driver = bit.value()
            # NOTE(rsetaluri): This is somewhat of a hack to support undriven
            # wires. We mock driving them with a constant so they get excluded
            # anyway. This is probably ok since unwired ports are usually clock
            # types which will be wired up later. Therefore, they are not
            # interesting data timing paths.
            if driver is None:  # hack!
                driver = m.GND
            assert driver is not None
            ref = find_inst_ref(driver)
            if ref is None:  # defn ref
                ref = find_defn_ref(driver)
                if ref is None:
                    assert driver.const()
                    data[bit] = driver
                    continue
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
            # NOTE(rsetaluri): Dict keys are used to mimic an ordered set.
            work += list({path.src: None for path in paths})

        out = []

        def _assemble(bit, curr):
            paths = data[bit]
            if isinstance(paths, m.Type):
                if paths.const():
                    return
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


def generate_random_path(ckt: m.DefineCircuitKind) -> TopSignalPath:
    it = _BackwardsPathTracer(ckt)
    outputs = sum(map(list, map(m.as_bits, ckt.interface.ports.values())), [])
    outputs = list(filter(lambda b: b.is_input(), outputs))
    while outputs:
        idx = random.randrange(0, len(outputs))
        dst = outputs.pop(idx)
        paths = it.run(dst)
        if not paths:
            continue
        return random.choice(paths)
    raise RuntimeError("No valid path found")
