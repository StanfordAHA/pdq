import dataclasses
from typing import Any, List, Tuple

import magma as m

from common.validator import validator
from circuit_tools.circuit_utils import find_ref


@dataclasses.dataclass(frozen=True)
class SignalPath:
    src: m.Bit
    dst: m.Bit
    path: List[Tuple[m.Bit, m.Bit]]


@validator
def validate_path(path: SignalPath, ckt: m.DefineCircuitKind):
    assert isinstance(path.src, m.Out(m.Bit))
    assert isinstance(path.dst, m.In(m.Bit))
    for value in (path.src, path.dst):
        ref = find_ref(value.name, lambda r: isinstance(r, m.DefnRef))
        assert ref is not None and ref.defn is ckt
    src = path.src
    for in_pin, out_pin in path.path:
        assert in_pin.trace() is src
        inst = None
        for value in (in_pin, out_pin):
            ref = find_ref(value.name, lambda r: isinstance(r, m.InstRef))
            assert ref is not None and ref.inst in ckt.instances
            assert inst is None or inst is ref.inst
            inst = ref.inst
        src = out_pin


def partial_extract(ckt: m.DefineCircuitKind, path: SignalPath):
    valid = validate_path(path, ckt)
    if not valid:
        raise ValueError(f"Invalid path: {path} ({valid.msg})")
    extra_ports = {}
    instances = []
    for in_pin, out_pin in path.path:
        inst = in_pin.name.inst
        for port in type(inst).interface.ports.values():
            name = port.name.name
            if name == in_pin.name.name or name == out_pin.name.name:
                continue
            extra_ports[(inst.name, name)] = type(port)

    class _Partial(m.Circuit):
        io = m.IO(**{f"{inst_name}_{port_name}": T.flip()
                     for (inst_name, port_name), T in extra_ports.items()})
        io += m.IO(**{
            path.src.name.name: type(path.src).flip(),
            path.dst.name.name: type(path.dst).flip()
        })
        curr = getattr(io, path.src.name.name)
        for in_pin, out_pin, in path.path:
            orig_inst = in_pin.name.inst
            inst = type(orig_inst)()

            # HACK!
            def _unmap_name(n):
                if n == "in0":
                    return "I0"
                if n == "in1":
                    return "I1"
                if n == "out":
                    return "O"
                return n

            m.wire(curr, getattr(inst, _unmap_name(in_pin.name.name)))
            curr = getattr(inst, _unmap_name(out_pin.name.name))

            for port in inst.interface.ports.values():
                name = port.name.name
                if name == in_pin.name.name or name == out_pin.name.name:
                    continue
                m.wire(port, getattr(io, f"{orig_inst.name}_{name}"))
        m.wire(curr, getattr(io, path.dst.name.name))
        name = f"Partial_{ckt.name}"

    return _Partial
