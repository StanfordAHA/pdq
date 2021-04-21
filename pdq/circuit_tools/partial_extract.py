from types import SimpleNamespace

import magma as m

from pdq.common.algorithms import only
from pdq.circuit_tools.circuit_utils import (
    DefnSelector, make_port_selector, find_instances_by_name)
from pdq.circuit_tools.signal_path import SignalPath, validate_path


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
