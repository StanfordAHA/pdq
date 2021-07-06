import abc
import dataclasses
import functools
from typing import List, Iterable, Union

import magma as m

from pdq.circuit_tools.circuit_utils import (
    find_ref, find_defn_ref, find_inst_ref)
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
    def extend(self, leaf: m.Circuit) -> 'ScopeInterface':
        raise NotImplementedError()

    @abc.abstractmethod
    def __equals__(self, other: 'ScopeInterface') -> bool:
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


@dataclasses.dataclass(frozen=True, eq=False)
class Scope(ScopeInterface):
    top: m.DefineCircuitKind
    path: List[m.Circuit] = dataclasses.field(default_factory=list)

    def root(self) -> m.DefineCircuitKind:
        return self.top

    def is_root(self) -> bool:
        return not self.path

    def leaf(self) -> Union[m.DefineCircuitKind, m.Circuit]:
        if not self.path:
            return self.top
        return self.path[-1]

    def extend(self, leaf: m.Circuit) -> 'Scope':
        path = self.path.copy()
        path.append(leaf)
        return Scope(self.top, path)

    def __equals__(self, other: 'Scope') -> bool:
        if not isinstance(other, Scope):
            return NotImplemented
        return (
            (self.top is other.top) and
            (len(self.path) == len(other.path)) and
            (all(x is y for x, y in zip(self.path, other.path))))

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


@dataclasses.dataclass(frozen=True, eq=False)
class ScopedValue:
    value: m.Type
    scope: ScopeInterface

    def __equals__(self, other: 'ScopedValue') -> bool:
        if not isinstance(other, ScopedValue):
            return NotImplemented
        return self.value is other.value and self.scope == other.scope

    def __str__(self):
        return f"{str(self.scope)}.{str(self.value)}"


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

    def __equals__(self, other: 'ScopeInterface') -> bool:
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
        # TODO(rsetaluri): Implement these^ two cases.
        raise NotImplementedError()
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


@dataclasses.dataclass(frozen=True, eq=False)
class BitSignalPath(SignalPathInterface):
    nodes: List[ScopedBit]

    def __iter__(self) -> Iterable[ScopedBit]:
        return iter(self.nodes)

    @validator
    def validate(self) -> None:
        prev = None
        for curr in self:
            curr.scope.validate()
            ref = find_defn_ref(curr.value)
            if ref is not None:  # top-level
                assert curr.scope.is_root()
                assert curr.scope.root() is ref.defn
            else:
                ref = find_inst_ref(curr.value)
                assert ref is not None
                assert ref.inst in curr.scope.leaf_type().instances
            if prev is not None:
                assert _is_driver(prev, curr)
            prev = curr
