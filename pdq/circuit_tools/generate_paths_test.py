import pytest

from designs.simple_alu import SimpleAlu
from pdq.circuit_tools.circuit_utils import find_instances_by_name
from pdq.circuit_tools.generate_paths import SignalPathQuery, generate_paths
from pdq.circuit_tools.signal_path import SignalPath, paths_equal, validate_path
from pdq.common.algorithms import only


class _GeneratePathsTest:
    def __init__(self):
        self.ckt = SimpleAlu
        self._instance_cache = {}

    def generate_paths(self, query):
        self.paths = generate_paths(self.ckt, query)
        # Check that all the paths returned are valid paths w.r.t. ckt.
        assert all(validate_path(path, self.ckt) for path in self.paths)

    def get_instance(self, name):
        try:
            return self._instance_cache[name]
        except KeyError:
            pass
        inst = only(find_instances_by_name(self.ckt, name))
        self._instance_cache[name] = inst
        return inst

    def pop_path(self, path):
        # Since the set of paths returned by generate_paths can be in any order,
        # we do the following: for each path we expect to be returned, find it's
        # index in the returned list, and remove it. Then, at the end, we expect
        # the list to be empty.
        idx = only((
            i for i, p in enumerate(self.paths) if paths_equal(p, path)))
        self.paths.pop(idx)


@pytest.fixture
def generate_paths_test():
    return _GeneratePathsTest()


def test_basic(generate_paths_test):
    query = SignalPathQuery(SimpleAlu.a[0], SimpleAlu.out[0])
    generate_paths_test.generate_paths(query)

    # Grab the internal instances of SimpleAlu for checking the paths.
    units = (generate_paths_test.get_instance(name) for name in ("add", "sub"))
    mux = generate_paths_test.get_instance("Mux")

    # Check all the paths through the functional units (add, sub).
    for i, unit in enumerate(units):
        for j, bit in enumerate(unit.O):
            mux_in = getattr(mux, f"I{i}")
            path = SignalPath(
                src=SimpleAlu.a[0],
                dst=SimpleAlu.out[0],
                path=[(unit.I0[0], bit),
                      (mux_in[j], mux.O[0])])
            generate_paths_test.pop_path(path)

    # Check the passthrough path.
    generate_paths_test.pop_path(
        SignalPath(
            src=SimpleAlu.a[0],
            dst=SimpleAlu.out[0],
            path=[(mux.I2[0], mux.O[0])]))

    # Check that we've found all the paths.
    assert len(generate_paths_test.paths) == 0


def test_thru(generate_paths_test):
    adder = generate_paths_test.get_instance("add")
    query = SignalPathQuery(SimpleAlu.a[0], SimpleAlu.out[0], [adder])
    generate_paths_test.generate_paths(query)

    mux = generate_paths_test.get_instance("Mux")

    # Check the path through the add.
    for j, bit in enumerate(adder.O):
        mux_in = getattr(mux, f"I{0}")
        path = SignalPath(
            src=SimpleAlu.a[0],
            dst=SimpleAlu.out[0],
            path=[(adder.I0[0], bit),
                  (mux_in[j], mux.O[0])])
        generate_paths_test.pop_path(path)

    # Check that we've found all the paths.
    assert len(generate_paths_test.paths) == 0
