import functools
import itertools
import numpy

import hwtypes as ht
import pysmt.shortcuts as smt
import pysmt.logics


def apply_binop_as_unop(op, x):
    size = len(x)
    assert (size % 2) == 0
    mid = int(size / 2)
    return op(x[:mid], x[mid:])


def binop_to_unop(op):
    return functools.partial(apply_binop_as_unop, op)


def test_op(op, M, N, m, n):
    assert m in range(M)
    assert n in range(N)
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
