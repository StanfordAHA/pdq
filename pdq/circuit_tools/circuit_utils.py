import dataclasses
import functools
from typing import Callable, Iterable, Optional, Union

import magma as m

from pdq.common.algorithms import only


def find_instances(
        ckt: m.DefineCircuitKind,
        fn: Callable[[m.Circuit], bool]) -> Iterable[m.Circuit]:
    return filter(fn, ckt.instances)


def find_instances_name(
        ckt: m.DefineCircuitKind,
        fn: Callable[[str], bool]) -> Iterable[m.Circuit]:
    return find_instances(ckt, lambda i: fn(i.name))


def find_instances_type(
        ckt: m.DefineCircuitKind,
        fn: Callable[[m.DefineCircuitKind], bool]) -> Iterable[m.Circuit]:
    return find_instances(ckt, lambda i: fn(type(i)))


def find_instances_name_equals(
        ckt: m.DefineCircuitKind, name: str) -> Iterable[m.Circuit]:
    return find_instances_name(ckt, lambda s: s == name)


def find_instances_name_substring(
        ckt: m.DefineCircuitKind, name_substr: str) -> Iterable[m.Circuit]:
    return find_instances_name(ckt, lambda s: name_substr in s)


def find_ref(
        ref: m.ref.Ref,
        condition: Callable[[m.ref.Ref], bool]) -> Optional[m.ref.Ref]:
    if condition(ref):
        return ref
    if ref is None:
        return None
    parent = ref.parent()
    if parent is ref:
        return None
    return find_ref(parent, condition)


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
        return only(find_instances_name_equals(defn, self.inst))

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
