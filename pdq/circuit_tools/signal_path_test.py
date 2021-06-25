import magma as m

from pdq.circuit_tools.circuit_utils import (
    find_instances_name_substring, find_instances_type)
from pdq.circuit_tools.signal_path import (
    InternalSignalPath, TopSignalPath)
from pdq.common.algorithms import only


class _Accum(m.Circuit):
    T = m.UInt[16]
    io = m.IO(I=m.In(T), O=m.Out(T)) + m.ClockIO()
    reg = m.Register(T)()
    accum = reg.O + io.I
    reg.I @= accum
    io.O @= accum


class _Top(m.Circuit):
    T = m.UInt[16]
    io = m.IO(
        I0=m.In(T),
        I1=m.In(T),
        O=m.Out(T),
    )
    io += m.ClockIO()
    out = _Accum()(io.I0)
    out |= (io.I0 & io.I1)
    io.O @= out


def test_internal_signal_path():
    # Validate internal path through and.
    and_inst = only(find_instances_name_substring(_Top, "and"))
    path = InternalSignalPath(
        src=and_inst.I0[0],
        dst=and_inst.O[0]
    )
    path.validate(_Top).throw()
    # Validate internal path through or.
    or_inst = only(find_instances_name_substring(_Top, "or"))
    path = InternalSignalPath(
        src=or_inst.I1[0],
        dst=or_inst.O[0]
    )
    path.validate(_Top).throw()


def test_top_signal_path():
    # Validate top-level path:
    #   I0[0] -> and.I0[0] -> and.O[0] -> or.I1[0] -> or.O[0] -> O[0]
    and_inst = only(find_instances_name_substring(_Top, "and"))
    or_inst = only(find_instances_name_substring(_Top, "or"))
    path = TopSignalPath(
        src=_Top.I0[0],
        dst=_Top.O[0],
        path=[
            InternalSignalPath(
                src=and_inst.I0[0],
                dst=and_inst.O[0]
            ),
            InternalSignalPath(
                src=or_inst.I1[0],
                dst=or_inst.O[0]
            )
        ]
    )
    path.validate(_Top).throw()
