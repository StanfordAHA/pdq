import atexit
import csv
import dataclasses
import functools
import itertools
import numpy
import os
import pathlib
from typing import Callable, Optional, TypeVar

import hwtypes as ht
import pysmt.shortcuts as smt
import pysmt.logics


_T = TypeVar("T")
_UnaryCallable = Callable[[_T], _T]
_BinaryCallable = Callable[[_T, _T], _T]


class _TestOpCache:
    _shared = dict(
        _cache=None,
        _filename=pathlib.Path(".pdq/test_op_cache.csv"),
        _modified=False)

    def __init__(self):
        self.__dict__ = self._shared

    @staticmethod
    def _initialize_cache(filename):
        cache = {}
        try:
            with open(filename, "r") as f:
                reader = csv.reader(f)
                for *k, v in reader:
                    k[0] = WrappedOp(k[0])
                    k[1:] = list(map(int, k[1:]))
                    k = tuple(k)
                    cache[k] = bool(int(v))
        except FileNotFoundError:
            pass
        return cache

    def writeback(self):
        if not self._modified:
            return
        dir_name = self._filename.parts[0]
        if not os.path.isdir(dir_name):
            os.mkdir(dir_name)
        with open(self._filename, "w") as f:
            writer = csv.writer(f)
            for k, v in self._cache.items():
                k = list(k)
                k[0] = k[0].name
                writer.writerow(k + [int(v)])

    def get_or_set(self, key, evaluator):
        if self._cache is None:
            self._cache = _TestOpCache._initialize_cache(self._filename)
        try:
            value = self._cache[key]
        except KeyError:
            value = evaluator(key)
            self._cache[key] = value
            self._modified = True
        return value


def _wrap_test_op(fn):
    cache = _TestOpCache()
    atexit.register(lambda: cache.writeback())

    def _evaluator(key):
        return fn(*key)

    @functools.wraps(fn)
    def _wrapped(*key):
        return cache.get_or_set(key, _evaluator)

    return _wrapped


@dataclasses.dataclass(frozen=True)
class WrappedOp:
    name: str
    op: Optional[_UnaryCallable] = None

    def __call__(self, x: _T) -> _T:
        return self.op(x)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: 'WrappedOp') -> bool:
        if not isinstance(other, WrappedOp):
            return NotImplemented
        return self.name == other.name


def apply_binop_as_unop(op: _BinaryCallable, x: _T) -> _T:
    size = len(x)
    assert (size % 2) == 0
    mid = int(size / 2)
    return op(x[:mid], x[mid:])


def binop_to_unop(op: _BinaryCallable) -> _UnaryCallable:
    return functools.partial(apply_binop_as_unop, op)


@_wrap_test_op
def test_op(op: WrappedOp, M: int, N: int, m: int, n: int):
    if not isinstance(op, WrappedOp):
        raise TypeError(op)
    if m not in range(M):
        raise ValueError((m, M))
    if n not in range(N):
        raise ValueError((n, N))
    x = ht.SMTBitVector[M]()
    x0 = x & ~ht.SMTBitVector[M](1 << m)
    x1 = x | ht.SMTBitVector[M](1 << m)
    l = op(x0)
    r = op(x1)
    assert type(l) is type(r)
    is_bit_output = isinstance(l, ht.SMTBit)
    if is_bit_output:
        assert N == 1  # assert n in [0, N] guarantees n == 0
        f = (op(x0) == op(x1))
    else:
        f = (op(x0)[n] == op(x1)[n])
    with smt.Solver("z3", logic=pysmt.logics.BV) as solver:
        solver.add_assertion((~f).value)
        return solver.solve()
