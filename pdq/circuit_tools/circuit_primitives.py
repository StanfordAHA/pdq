import functools
import operator

import magma as m
from magma.primitives.mux import CoreIRCommonLibMuxN
from magma.primitives.register import _CoreIRRegister

from pdq.circuit_tools.circuit_primitives_utils import (
    WrappedOp, binop_to_unop, test_op)
from pdq.circuit_tools.circuit_utils import find_defn_ref
from pdq.common.algorithms import first


################################################################################
# Mux primitives
################################################################################
def _get_mux_drivers(ckt, name, sel):
    assert name == "out"
    assert isinstance(sel, m.value_utils.ArraySelector)
    assert sel.child is None
    N = ckt.coreir_genargs["N"]
    return [ckt.I.data[i][sel.index] for i in range(N)] + list(ckt.I.sel)
################################################################################


################################################################################
# Register primitives
################################################################################
def _get_register_drivers(ckt, name, sel):
    assert name == "out"
    assert isinstance(sel, m.value_utils.ArraySelector)
    assert sel.child is None
    return []
################################################################################


################################################################################
# CoreIR op primitives
################################################################################
def _is_coreir_op(ckt):
    return ckt.coreir_lib == "corebit" or ckt.coreir_lib == "coreir"


def _get_coreir_op_drivers(ckt, name, sel):
    assert name == "out"
    op_name = ckt.coreir_name
    if ckt.coreir_lib == "corebit":
        assert type(sel) is m.value_utils.Selector
        assert sel.child is None
        if op_name == "undriven":
            return []
        if op_name == "not":
            return [ckt.I]
        return [ckt.I0, ckt.I1]
    assert ckt.coreir_lib == "coreir"
    if isinstance(sel, m.value_utils.ArraySelector):
        assert sel.child is None
        N = len(ckt.O)
        n = sel.index
    else:  # cmp op
        assert type(sel) is m.value_utils.Selector
        assert isinstance(ckt.O, m.Bit)
        N = 1
        n = 0
    if op_name == "orr":
        op = lambda x: functools.reduce(operator.or_, x)
    elif op_name == "andr":
        op = lambda x: functools.reduce(operator.and_, x)
    else:
        op = getattr(operator, m.primitive_to_python(op_name))
    if op_name in ("not", "neg", "orr", "andr"):
        inputs = list(ckt.I)
    else:
        inputs = list(m.concat(ckt.I0, ckt.I1))
        op = binop_to_unop(op)
    op = WrappedOp(op_name, op)
    M = len(inputs)
    tests = (test_op(op, M, N, m, n) for m in range(M))
    return [inputs[i] for i, t in enumerate(tests) if t]
################################################################################


class _PrimitiveDriversDatabase:
    def __init__(self):
        self._circuits = {}
        self._generators = {}
        self._properties = []

    def add_circuit(self, ckt, getter):
        self._circuits[ckt] = getter

    def add_generator(self, generator, getter):
        self._generators[generator] = getter

    def add_property(self, property_, getter):
        self._properties.append((property_, getter))

    def get(self, ckt, name, sel, allow_default):
        try:
            getter = self._circuits[ckt]
        except KeyError:
            pass
        else:
            return getter(ckt, name, sel)
        typ = type(ckt)
        if issubclass(typ, m.Generator2):
            try:
                getter = self._generators[typ]
            except KeyError:
                pass
            else:
                return getter(ckt, name, sel)
        try:
            _, getter = first(filter(lambda p: p[0](ckt), self._properties))
        except ValueError:
            pass
        else:
            return getter(ckt, name, sel)
        if not allow_default:
            raise KeyError(f"No entry found for {ckt}")
        # TODO(rsetaluri): Implement default behavior.
        raise NotImplementedError()


_primitive_drivers_database = _PrimitiveDriversDatabase()


_primitive_drivers_database.add_generator(CoreIRCommonLibMuxN, _get_mux_drivers)
_primitive_drivers_database.add_generator(
    _CoreIRRegister, _get_register_drivers)
_primitive_drivers_database.add_property(_is_coreir_op, _get_coreir_op_drivers)


def get_primitive_drivers(bit: m.Bit, allow_default: bool = True):
    if not isinstance(bit, m.In(m.Bit)):
        raise ValueError(f"Expected output bit, got: {type(bit)}")
    ref = find_defn_ref(bit)
    if ref is None:
        raise ValueError(f"Expected definition port, got {bit}")
    if not m.isprimitive(ref.defn):
        raise ValueError(f"Expected primitive, got {ref.defn}")
    sel = m.value_utils.make_selector(bit)
    return _primitive_drivers_database.get(
        ref.defn, ref.name, sel, allow_default)
