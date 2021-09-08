import abc
import dataclasses
import functools
from typing import Iterable, List, Optional, Tuple, Union

import magma as m

from pdq.circuit_tools.circuit_utils import (
    find_ref, find_defn_ref, find_inst_ref, inst_port_to_defn_port)
from pdq.common.validator import validator


class ScopeInterface(abc.ABC):
    @abc.abstractmethod
    def root(self) -> m.DefineCircuitKind:
        raise NotImplementedError()

    @abc.abstractmethod
    def is_root(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def leaf(self) -> Union[m.DefineCircuitKind, m.Circuit]:
        raise NotImplementedError()

    @abc.abstractmethod
    def pop(self) -> Tuple['Scope', m.Circuit]:
        raise NotImplementedError()

    @abc.abstractmethod
    def extend(self, leaf: m.Circuit) -> 'ScopeInterface':
        raise NotImplementedError()

    @abc.abstractmethod
    def __eq__(self, other: 'ScopeInterface') -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def __ne__(self, other: 'ScopeInterface') -> bool:
        raise NotImplementedError()

    @validator
    @abc.abstractmethod
    def validate(self) -> None:
        raise NotImplementedError()

    def leaf_type(self) -> m.DefineCircuitKind:
        leaf = self.leaf()
        if isinstance(leaf, m.DefineCircuitKind):
            return leaf
        assert isinstance(leaf, m.Circuit)
        return type(leaf)


@dataclasses.dataclass(frozen=True)
class Scope(ScopeInterface):
    top: m.DefineCircuitKind
    path: Tuple[m.Circuit] = dataclasses.field(default_factory=tuple)

    def root(self) -> m.DefineCircuitKind:
        return self.top

    def is_root(self) -> bool:
        return not self.path

    def leaf(self) -> Union[m.DefineCircuitKind, m.Circuit]:
        if not self.path:
            return self.top
        return self.path[-1]

    def pop(self) -> Tuple['Scope', m.Circuit]:
        if self.is_root():
            raise RuntimeError()
        path = list(self.path)
        leaf = path.pop()
        return Scope(self.top, tuple(path)), leaf

    def extend(self, leaf: m.Circuit) -> 'Scope':
        path = list(self.path)
        path.append(leaf)
        return Scope(self.top, tuple(path))

    def __eq__(self, other: 'Scope') -> bool:
        if not isinstance(other, Scope):
            return NotImplemented
        return (
            (self.top is other.top) and
            (len(self.path) == len(other.path)) and
            (all(x is y for x, y in zip(self.path, other.path))))

    def __ne__(self, other: 'Scope') -> bool:
        return not self == other

    def __str__(self):
        top = self.top.name
        if not self.path:
            return top
        return ".".join([top] + [i.name for i in self.path])

    @validator
    def validate(self) -> None:
        if not self.path:
            return
        curr = self.top
        for inst in self.path:
            assert inst in curr.instances
            curr = type(inst)


@dataclasses.dataclass(frozen=True)
class ScopedValue:
    value: m.Type
    scope: ScopeInterface

    @property
    def ref(self) -> Optional[Union[m.InstRef, m.DefnRef]]:
        try:
            return self._ref
        except AttributeError:
            pass
        inst = None
        defn = None
        ref = find_inst_ref(self.value)
        if ref is not None:
            inst = ref.inst
        else:
            ref = find_defn_ref(self.value)
            if ref is not None:
                defn = ref.defn
        # NOTE(rsetaluri): Using object.__setattr__ is technically unsafe on
        # frozen dataclasses, but we know this is just caching logic.
        object.__setattr__(self, "_ref", ref)
        object.__setattr__(self, "_inst", inst)
        object.__setattr__(self, "_defn", defn)
        return ref

    @property
    def defn(self) -> Optional[m.DefineCircuitKind]:
        try:
            return self._defn
        except AttributeError:
            pass
        ref = self.ref  # performs logic in ref() above
        return self._defn

    @property
    def inst(self) -> Optional[m.Circuit]:
        try:
            return self._inst
        except AttributeError:
            pass
        ref = self.ref  # performs logic in ref() above
        return self._inst

    def __eq__(self, other: 'ScopedValue') -> bool:
        if not isinstance(other, ScopedValue):
            return NotImplemented
        return self.value is other.value and self.scope == other.scope

    def __ne__(self, other: 'ScopedValue') -> bool:
        if not isinstance(other, ScopedValue):
            return NotImplemented
        return not self == other

    def __str__(self):
        if self.value.const():
            return str(self.value)
        if self.defn is not None:
            return f"{str(self.value)}"
        return f"{str(self.scope)}.{repr(self.value)}"


@dataclasses.dataclass(frozen=True, eq=False)
class ScopedBit(ScopedValue):
    value: m.Bit
    scope: ScopeInterface


class SignalPathInterface(abc.ABC):
    @abc.abstractmethod
    def __iter__(self) -> Iterable[ScopedValue]:
        raise NotImplementedError()

    @validator
    @abc.abstractmethod
    def validate(self) -> None:
        raise NotImplementedError()


def _is_driver(driver: ScopedBit, drivee: ScopedBit) -> bool:

    def _ref_test(ref):
        return isinstance(ref, (m.ref.InstRef, m.ref.DefnRef))
    
    driver_ref = find_ref(driver.value.name, _ref_test)
    drivee_ref = find_ref(drivee.value.name, _ref_test)

    if driver_ref is None or drivee_ref is None:
        raise ValueError(f"Unexpected values: {driver}, {drivee}")

    def _match(T0, T1):
        return isinstance(driver_ref, T0) and isinstance(drivee_ref, T1)

    # Check inst-to-inst connection case.
    if _match(m.ref.InstRef, m.ref.InstRef):
        # If @driver and @drivee are from the same instance, then we require
        # that (a) their scopes are the same and (b) there is a connection
        # between the two. We further split check (b) up into 2 cases:
        # primitives and non-primitives. In the primitive case, we can always
        # conservatively always return True (assuming @driver is an input and
        # @drivee is an output), or we can perform a rigorous check on the
        # primitive type. Otherwise (non-primitive), we check the definition
        # directly using trace().
        if driver_ref.inst is drivee_ref.inst:
            if driver.scope != drivee.scope:
                return False
            inst = driver_ref.inst
            defn = type(inst)
            if m.isdefinition(defn):  # non-primitive case
                # TODO(rsetaluri): Convert to defn value and check driver.
                raise NotImplementedError()
            # Primitive case: Only need to check for direction.
            # TODO(rsetaluri): Use SMT to verify in-out connection of prim.
            return driver.value.is_input() and drivee.value.is_output()
        # @driver and @drivee are from different instances. Now there are 2
        # cases:
        #   (a) inst-to-inst connection at the same level
        if driver.scope == drivee.scope:
            return drivee.value.trace() is driver.value
        #   (b) inst-to-inst connection at nested levels
        #       There are 2 (vaild) sub-cases here:
        #         (i) drivee is nested below driver
        if driver.scope.extend(driver.inst) == drivee.scope:
            defn_bit = inst_port_to_defn_port(driver.value, driver.ref)
            return drivee.value.trace() is defn_bit
        #         (ii) driver is nested below drivee
        elif drivee.scope.extend(drivee.inst) == driver.scope:
            defn_bit = inst_port_to_defn_port(drivee.value, drivee.ref)
            return defn_bit.trace() is driver.value
        else:
            return False
    # Check the defn-to-inst and inst-to-defn cases.
    if (_match(m.ref.DefnRef, m.ref.InstRef) or
        _match(m.ref.InstRef, m.ref.DefnRef)):
        # Both these cases are simple. First we check that the scopes are
        # equal. Next we can do a direct check with trace().
        if driver.scope != drivee.scope:
            return False
        return drivee.value.trace() is driver.value
    # TODO(retaluri): Implement the remaining cases.
    raise NotImplementedError(driver, drivee)


@dataclasses.dataclass(frozen=True)
class BitSignalPath(SignalPathInterface):
    nodes: List[ScopedBit]

    def __iter__(self) -> Iterable[ScopedBit]:
        return iter(self.nodes)

    @validator
    def validate(self) -> None:
        prev = None
        for curr in self:
            curr.scope.validate()
            if curr.defn is not None:  # top-level
                assert curr.scope.is_root()
                assert curr.scope.root() is curr.defn
            else:
                assert curr.inst is not None
                assert curr.inst in curr.scope.leaf_type().instances
            if prev is not None:
                assert _is_driver(prev, curr)
            prev = curr
