from designs.simple_alu import SimpleAlu
from pdq.circuit_tools.circuit_utils import find_instances_by_name
from pdq.circuit_tools.generate_paths import SignalPathQuery, generate_paths
from pdq.circuit_tools.signal_path import SignalPath, paths_equal, validate_path
from pdq.common.algorithms import only


def test_basic():
    query = SignalPathQuery(SimpleAlu.a[0], SimpleAlu.out[0])
    paths = generate_paths(SimpleAlu, query)

    # Check that all the paths returned are valid paths w.r.t. SimpleAlu.
    assert all(validate_path(path, SimpleAlu) for path in paths)

    # Grab the internal instances of SimpleAlu for checking the paths.
    units = (only(find_instances_by_name(SimpleAlu, name))
             for name in ("add", "sub"))
    mux = only(find_instances_by_name(SimpleAlu, "Mux"))

    # Since the set of paths returned by generate_paths can be in any order, we
    # do the following: for each path we expect to be returned, find it's index
    # in the returned list, and remove it. Then, at the end, we expect the list
    # to be empty.

    def _find_and_remove(path: SignalPath):
        idx = only((i for i, p in enumerate(paths) if paths_equal(p, path)))
        paths.pop(idx)

    # Check all the paths through the functional units (add, sub).
    for i, unit in enumerate(units):
        for j, bit in enumerate(unit.O):
            mux_in = getattr(mux, f"I{i}")
            path = SignalPath(
                src=SimpleAlu.a[0],
                dst=SimpleAlu.out[0],
                path=[(unit.I0[0], bit),
                      (mux_in[j], mux.O[0])])
            _find_and_remove(path)

    # Check the passthrough path.
    _find_and_remove(
        SignalPath(
            src=SimpleAlu.a[0],
            dst=SimpleAlu.out[0],
            path=[(mux.I2[0], mux.O[0])]))

    # Check that we've found all the paths.
    assert len(paths) == 0
