import dataclasses
from types import SimpleNamespace
from typing import List

import magma as m

from pdq.common.algorithms import only
from pdq.circuit_tools.circuit_utils import (
    DefnSelector, make_port_selector, find_inst_ref)
from pdq.circuit_tools.signal_path import TopSignalPath, InternalSignalPath


def _retarget_selector(selector, *keys):
    return type(selector)(selector.child, *keys)


def _partial_extract_internal(
        path: InternalSignalPath, context: List[m.Circuit], state):
    ref = find_inst_ref(path.src)
    inst = ref.inst
    context += [inst]
    if path.path is not None:
        for sub_path in path.path:
            _partial_extract_internal(sub_path, context, state)
        return
    inst_name = f"{'__'.join(inst.name for inst in context)}"
    state.instances[inst_name] = type(inst)
    selector = _retarget_selector(make_port_selector(path.src), inst_name)
    state.connections.append((state.curr, selector))
    selector = _retarget_selector(make_port_selector(path.dst), inst_name)
    state.curr = selector
    for port_name, port in inst.interface.ports.items():
        for bit in m.as_bits(port):
            if bit is path.src or bit is path.dst:
                continue
            new_port_name = f"lifted_port_{len(state.ports)}__"
            selector = _retarget_selector(make_port_selector(bit), inst_name)
            state.ports[new_port_name] = type(bit)
            state.connections.append((
                selector, DefnSelector(None, new_port_name)))


def partial_extract(ckt: m.DefineCircuitKind, path: TopSignalPath):
    SRC_PIN_NAME = "partial_src_pin__"
    DST_PIN_NAME = "partial_dst_pin__"
    valid = path.validate(ckt)
    if not valid:
        valid.throw()
    state = SimpleNamespace(ports={}, instances={}, connections=[], curr=None)
    state.ports[SRC_PIN_NAME] = type(path.src).flip()
    state.ports[DST_PIN_NAME] = type(path.dst).flip()
    state.curr = DefnSelector(None, SRC_PIN_NAME)
    if path.path is not None:
        for sub_path in path.path:
            _partial_extract_internal(sub_path, [], state)
    state.connections.append((state.curr, DefnSelector(None, DST_PIN_NAME)))

    partial_ckt_name = f"Partial_{ckt.name}"

    class _Partial(m.Circuit):
        io = m.IO(**{name: T for name, T in state.ports.items()})

        _container = SimpleNamespace()
        _container.interface = SimpleNamespace(ports=io.ports)
        _container.instances = []
        for name, T in state.instances.items():
            inst = T(name=name)
            _container.instances.append(inst)
        for src, dst in state.connections:
            m.wire(src.select(_container), dst.select(_container))

        # This has to be last in order to avoid other 'name's in the namespace
        # from over-writing the name.
        name = partial_ckt_name

    return _Partial
