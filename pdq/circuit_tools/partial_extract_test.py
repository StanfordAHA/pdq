import tempfile

import magma as m
import magma.testing

from pdq.circuit_tools.graph_view import BitPortNode
from pdq.circuit_tools.partial_extract import extract_partial
from pdq.circuit_tools.partial_extract_query import (
    PartialExtractQuery, query_is_empty)
from pdq.circuit_tools.signal_path import Scope, ScopedBit


class _Foo(m.Circuit):
    io = m.IO(
        I0=m.In(m.Bits[2]),
        I1=m.In(m.Bits[2]),
        I2=m.In(m.Bit),
        O=m.Out(m.Bits[4]))
    f = m.register(io.I0) | m.register(io.I1)
    io.O[0] @= f[0]
    io.O[1] @= ~io.I0[0]
    io.O[2] @= io.I2
    io.O[3] @= io.I2


m.passes.clock.WireClockPass(_Foo).run()


def test_basic():
    ckt = _Foo
    to_list = tuple(ScopedBit(o, Scope(ckt)) for o in ckt.O[:2])
    q = PartialExtractQuery(to_list=to_list)
    assert not query_is_empty(q)
    ckt_partial = extract_partial(ckt, q)

    with tempfile.TemporaryDirectory() as directory:
        basename = f"{directory}/{ckt_partial.name}"
        m.compile(basename, ckt_partial, inline=True)
        gold = "golds/partial_extract_basic.v"
        assert m.testing.utils.check_files_equal(
            __file__, f"{basename}.v", gold)
