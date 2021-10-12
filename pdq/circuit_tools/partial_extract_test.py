import tempfile

import magma as m
import magma.testing

from pdq.circuit_tools.circuit_utils import find_instances_name_equals
from pdq.circuit_tools.graph_view import BitPortNode
from pdq.circuit_tools.partial_extract import extract_partial
from pdq.circuit_tools.partial_extract_query import (
    PartialExtractQuery, query_is_empty)
from pdq.circuit_tools.signal_path import Scope, ScopedBit
from pdq.common.algorithms import only


class _Basic(m.Circuit):
    name = "Basic"
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


class _Registered(m.Circuit):
    name = "Registered"
    io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit))
    io.O @= m.register(~m.register(io.I, name="reg0"), name="reg1")


m.passes.clock.WireClockPass(_Basic).run()
m.passes.clock.WireClockPass(_Registered).run()


def test_basic():
    ckt = _Basic
    to_list = tuple(ScopedBit(o, Scope(ckt)) for o in ckt.O[:2])
    q = PartialExtractQuery(to_list=to_list)
    assert not query_is_empty(q)
    ckt_partial = extract_partial(ckt, q, name="basic_partial")

    with tempfile.TemporaryDirectory() as directory:
        basename = f"{directory}/{ckt_partial.name}"
        m.compile(basename, ckt_partial, inline=True)
        gold = "golds/partial_extract_basic.v"
        assert m.testing.utils.check_files_equal(
            __file__, f"{basename}.v", gold)


def test_register_to_register():
    ckt = _Registered
    reg0 = only(find_instances_name_equals(ckt, "reg0"))
    reg1 = only(find_instances_name_equals(ckt, "reg1"))
    scope = Scope(ckt)
    through_lists = ((ScopedBit(reg0.O, scope),), (ScopedBit(reg1.I, scope),))
    q = PartialExtractQuery(through_lists=through_lists)
    assert not query_is_empty(q)
    ckt_partial = extract_partial(ckt, q, name="register_to_regsiter_partial")

    with tempfile.TemporaryDirectory() as directory:
        basename = f"{directory}/{ckt_partial.name}"
        m.compile(basename, ckt_partial, inline=True)
        gold = "golds/partial_extract_register_to_regsiter.v"
        assert m.testing.utils.check_files_equal(
            __file__, f"{basename}.v", gold)


def test_io_to_register():
    ckt = _Registered
    reg0 = only(find_instances_name_equals(ckt, "reg0"))
    scope = Scope(ckt)
    from_list = (ScopedBit(ckt.I, scope),)
    through_lists = ((ScopedBit(reg0.I, scope),),)
    q = PartialExtractQuery(from_list=from_list, through_lists=through_lists)
    assert not query_is_empty(q)
    ckt_partial = extract_partial(ckt, q, name="io_to_regsiter_partial")

    with tempfile.TemporaryDirectory() as directory:
        basename = f"{directory}/{ckt_partial.name}"
        m.compile(basename, ckt_partial, inline=True)
        gold = "golds/partial_extract_io_to_register.v"
        assert m.testing.utils.check_files_equal(
            __file__, f"{basename}.v", gold)
