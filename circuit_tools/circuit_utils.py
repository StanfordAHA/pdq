from typing import Callable, Optional

import magma as m


def find_instances_by_name(ckt: m.DefineCircuitKind, name: str):
    return [inst for inst in ckt.instances if name in inst.name.lower()]


def find_ref(
        ref: m.ref.Ref,
        condition: Callable[[m.ref.Ref], bool]) -> Optional[m.ref.Ref]:
    if condition(ref):
        return ref
    if ref is None:
        return None
    find_ref(ref.parent())
