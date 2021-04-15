import magma as m

from designs.one_bit_alu import OneBitAlu
from pdq.common.algorithms import only
from pdq.circuit_tools.circuit_utils import find_instances_by_name
from pdq.circuit_tools.partial_extract import partial_extract, SignalPath


class SimpleAlu(m.Circuit):
    io = m.IO(
        a=m.In(m.UInt[4]),
        b=m.In(m.UInt[4]),
        opcode=m.In(m.UInt[2]),
        out=m.Out(m.UInt[4]))

    io.out @= m.mux([io.a + io.b, io.a - io.b, io.a, io.b], io.opcode)


def test_basic():
    xor = only(find_instances_by_name(OneBitAlu, "xor"))
    mux = only(find_instances_by_name(OneBitAlu, "Mux"))
    path = [
        (xor.I0, xor.O),
        (mux.I2, mux.O),
    ]
    path = SignalPath(
        src=OneBitAlu.a,
        dst=OneBitAlu.out,
        path=path,
    )

    Partial = partial_extract(OneBitAlu, path)

    # Check that there are only 2 instances.
    assert len(Partial.instances) == 2
    new_xor = only(find_instances_by_name(Partial, "xor"))
    new_mux = only(find_instances_by_name(Partial, "Mux"))
    assert new_xor.name == xor.name
    assert type(new_xor) is type(xor)
    assert new_mux.name == mux.name
    assert type(new_mux) is type(mux)

    # Check the connections along the desired timing path.
    assert new_xor.I0.trace() is Partial.partial_src_pin__
    assert new_mux.I2.trace() is new_xor.O
    assert Partial.partial_dst_pin__.trace() is new_mux.O


def test_bits_select():
    add = only(find_instances_by_name(SimpleAlu, "add"))
    mux = only(find_instances_by_name(SimpleAlu, "Mux"))
    path = [
        (add.I0[0], add.O[0]),
        (mux.I0[0], mux.O[0]),
    ]
    path = SignalPath(
        src=SimpleAlu.a[0],
        dst=SimpleAlu.out[0],
        path=path,
    )

    Partial = partial_extract(SimpleAlu, path)

    # Check that there are only 2 instances.
    assert len(Partial.instances) == 2
    new_add = only(find_instances_by_name(Partial, "add"))
    new_mux = only(find_instances_by_name(Partial, "Mux"))
    assert new_add.name == add.name
    assert type(new_add) is type(add)
    assert new_mux.name == mux.name
    assert type(new_mux) is type(mux)

    # Check the connections along the desired timing path.
    assert new_add.I0[0].trace() is Partial.partial_src_pin__
    assert new_mux.I0[0].trace() is new_add.O[0]
    assert Partial.partial_dst_pin__.trace() is new_mux.O[0]
