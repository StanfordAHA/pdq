import pytest
import random

import magma as m

from pdq.circuit_tools.circuit_primitives import *
from pdq.common.algorithms import only


def _check_unordered_set_identical(a, b):
    assert set(map(id, a)) == set(map(id, b))


@pytest.mark.parametrize("T,height", [(m.Array[10, m.Bits[6]], 16)])
def test_mux(T, height):
    Mux = m.Mux(T=T, height=height)
    Mux = type(only(Mux.instances))
    width = T.flat_length()
    assert isinstance(Mux.I.data, m.Array[height, m.Array[width, m.Bit]])
    index = random.randrange(0, width)
    expected = [Mux.I.data[i][index] for i in range(height)]
    expected += list(Mux.I.sel)
    got = get_primitive_drivers(Mux.O[index])
    _check_unordered_set_identical(expected, got)
