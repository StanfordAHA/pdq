import magma as m

from common.algorithms import only
from designs.one_bit_alu import OneBitAlu
from circuit_tools.circuit_utils import find_instances_by_name
from circuit_tools.partial_extract import partial_extract, SignalPath


def test_basic():
    xor = only(find_instances_by_name(OneBitAlu, "xor"))
    mux = only(find_instances_by_name(OneBitAlu, "mux"))
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
    xor = only(find_instances_by_name(Partial, "xor"))
    mux = only(find_instances_by_name(Partial, "mux"))

    # Check the connections along the desired timing path.
    assert xor.I0.trace() is Partial.a
    assert mux.I2.trace() is xor.O
    assert Partial.out.trace() is mux.O
