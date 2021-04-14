import dataclasses
from typing import Callable, Optional, Union

import magma as m

from common.algorithms import only


def find_instances_by_name(ckt: m.DefineCircuitKind, name: str):
    return [inst for inst in ckt.instances if name in inst.name]


def find_ref(
        ref: m.ref.Ref,
        condition: Callable[[m.ref.Ref], bool]) -> Optional[m.ref.Ref]:
    if condition(ref):
        return ref
    if ref is None:
        return None
    return find_ref(ref.parent(), condition)


def find_inst_ref(value: m.Type):
    return find_ref(value.name, lambda r: isinstance(r, m.InstRef))


def find_defn_ref(value: m.Type):
    return find_ref(value.name, lambda r: isinstance(r, m.DefnRef))


def _lookup_renamed_port(
        defn_or_inst: Union[m.Circuit, m.DefineCircuitKind], name: str) -> str:
    """Function to un-map renamed ports on circuits"""
    # NOTE(rsetaluri): This functionality should ideally be provided by circuit
    # directly.
    try:
        defn_or_inst.renamed_ports
    except AttributeError:
        return name
    for k, v in defn_or_inst.renamed_ports.items():
        if v == name:
            return k
    return name


@dataclasses.dataclass(frozen=True)
class InstSelector(m.value_utils.TupleSelector):
    def _select(self, value: m.Circuit):
        key = _lookup_renamed_port(value, self.key)
        return value.interface.ports[key]


@dataclasses.dataclass(frozen=True)
class DefnSelector(m.value_utils.TupleSelector):
    def _select(self, value: m.DefineCircuitKind):
        key = _lookup_renamed_port(value, self.key)
        return value.interface.ports[key]


@dataclasses.dataclass(frozen=True)
class PlacedInstSelector(m.value_utils.Selector):
    inst: str

    def _select(self, defn: m.DefineCircuitKind):
        return only(find_instances_by_name(defn, self.inst))

    def __str__(self):
        return f".{self.inst}{self._child_str()}"


def make_port_selector(value: m.Type):
    ref = find_ref(
        value.name,
        lambda r: isinstance(r, m.InstRef) or isinstance(r, m.DefnRef))
    if ref is None:
        raise ValueError("{value} is not a port")
    try:
        inst = ref.inst
    except AttributeError:
        pass
    else:
        return PlacedInstSelector(
            InstSelector(
                m.value_utils.make_selector(value),
                ref.name),
            inst.name)
    defn = ref.defn
    return DefnSelector(m.value_utils.make_selector(value), ref.name)
