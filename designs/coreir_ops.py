import operator

import magma as m


def _get_driver_instance(O):
    O = O.trace()
    return O.name.inst


def binary_op(width: int, op: str):
    T = m.UInt[width]
    op = getattr(operator, op)

    class _Tmp(m.Circuit):
        io = m.IO(I0=m.In(T), I1=m.In(T), O=m.Out(T)) + m.ClockIO()
        io.O @= op(io.I0, io.I1)
        name = f"{_get_driver_instance(io.O).name}_wrapper"

    return _Tmp
