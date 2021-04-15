import dataclasses
from types import SimpleNamespace
from typing import Any, List, Tuple

import magma as m

from pdq.common.algorithms import only
from pdq.common.validator import validator
from pdq.circuit_tools.circuit_utils import (
    DefnSelector, find_inst_ref, find_defn_ref, make_port_selector,
    find_instances_by_name)


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


def partial_extract(ckt: m.DefineCircuitKind, path: SignalPath):
    valid = validate_path(path, ckt)
    if not valid:
        valid.throw()
    partial_ckt_name = f"Partial_{ckt.name}"
    instances = {}
    ports = {}
    connections = []
    ports["partial_src_pin__"] = None, type(path.src).flip()
    ports["partial_dst_pin__"] = None, type(path.dst).flip()
    src_selector = DefnSelector(None, "partial_src_pin__")
    dst_selector = DefnSelector(None, "partial_dst_pin__")
    curr_selector = src_selector
    for in_pin, out_pin in path.path:
        in_pin_selector = make_port_selector(in_pin)
        connections.append((curr_selector, in_pin_selector))
        curr_selector = make_port_selector(out_pin)
        inst = only(find_instances_by_name(ckt, in_pin_selector.inst))
        instances[inst.name] = type(inst)
        for port_name, port in inst.interface.ports.items():
            for bit in m.as_bits(port):
                if bit is in_pin or bit is out_pin:
                    continue
                new_port_name = f"lifted_port_{len(ports)}__"
                selector = make_port_selector(bit)
                ports[new_port_name] = selector, type(bit)
                connections.append((
                    selector, DefnSelector(None, new_port_name)))
    connections.append((curr_selector, dst_selector))

    class _Partial(m.Circuit):
        io = m.IO(**{name: T for name, (_, T) in ports.items()})

        _container = SimpleNamespace()
        _container.interface = SimpleNamespace(ports=io.ports)
        _container.instances = []
        for name, T in instances.items():
            inst = T(name=name)
            _container.instances.append(inst)
        for src, dst in connections:
            m.wire(src.select(_container), dst.select(_container))

        # This has to be last in order to avoid other 'name's in the namespace
        # from over-writing the name.
        name = partial_ckt_name

    return _Partial
