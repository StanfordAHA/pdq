import dataclasses
from typing import List, Tuple

import magma as m

from pdq.circuit_tools.circuit_utils import find_defn_ref, find_inst_ref
from pdq.common.validator import validator


# NOTE(rsetaluri): We set eq=False because calling == might cause an equality
# circuit to be instanced. Instead, use the 'paths_equal' method.
@dataclasses.dataclass(frozen=True, eq=False)
class SignalPath:
    src: m.Bit
    dst: m.Bit
    path: List[Tuple[m.Bit, m.Bit]]

    def __eq__(self, _):
        raise NotImplementedError(f"{type(self)} does not support __eq__")


def paths_equal(l: SignalPath, r: SignalPath):
    return (
        (l.src is r.src) and
        (l.dst is r.dst) and
        (len(l.path) == len(r.path)) and
        (all(in0 is in1 and out0 is out1
             for ((in0, out0), (in1, out1)) in zip(l.path, r.path))))


@validator
def validate_path(path: SignalPath, ckt: m.DefineCircuitKind):
    assert isinstance(path.src, m.Out(m.Bit))
    assert isinstance(path.dst, m.In(m.Bit))
    for value in (path.src, path.dst):
        ref = find_defn_ref(value)
        assert ref is not None and ref.defn is ckt
    src = path.src
    for in_pin, out_pin in path.path:
        assert in_pin.trace() is src
        inst = None
        for value in (in_pin, out_pin):
            ref = find_inst_ref(value)
            assert ref is not None and ref.inst in ckt.instances
            assert inst is None or inst is ref.inst
            inst = ref.inst
        src = out_pin
