import magma as m
from magma.primitives.mux import CoreIRCommonLibMuxN

from pdq.circuit_tools.circuit_utils import find_defn_ref
from pdq.common.algorithms import first


def _get_mux_drivers(ckt, name, sel):
    assert name == "out"
    assert isinstance(sel, m.value_utils.ArraySelector)
    assert sel.child is None
    N = ckt.coreir_genargs["N"]
    return [ckt.I.data[i][sel.index] for i in range(N)] + list(ckt.I.sel)


def _is_binop(ckt):
    return ckt.coreir_lib == "coreir" and ckt.coreir_name in ("add", "sub")


def _get_binop_drivers(ckt, name, sel):
    assert name == "out"
    assert isinstance(sel, m.value_utils.ArraySelector)
    assert sel.child is None
    return [ckt.I0[sel.index], ckt.I1[sel.index]]


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
_primitive_drivers_database.add_property(_is_binop, _get_binop_drivers)


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
