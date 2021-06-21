import pytest

from designs.simple_alu import SimpleAlu
from pdq.circuit_tools.circuit_utils import find_instances_name_substring
from pdq.circuit_tools.generate_paths import SignalPathQuery, generate_paths
from pdq.circuit_tools.signal_path import (
    TopSignalPath, InternalSignalPath, paths_equal)
from pdq.common.algorithms import only


class _GeneratePathsTest:
    def __init__(self):
        self.ckt = SimpleAlu
        self._instance_cache = {}

    def generate_paths(self, query):
        self.paths = generate_paths(self.ckt, query)
        # Check that all the paths returned are valid paths w.r.t. ckt.
        for path in self.paths:
            v = path.validate(self.ckt)
            if not v:
                v.throw()
        assert all(path.validate(self.ckt) for path in self.paths)

    def get_instance(self, name, ckt=None):
        if ckt is None:
            ckt = self.ckt
        key = ckt, name
        try:
            return self._instance_cache[key]
        except KeyError:
            pass
        inst = only(find_instances_name_substring(ckt, name))
        self._instance_cache[key] = inst
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
    mux_prim = generate_paths_test.get_instance("mux", type(mux))

    # Check all the paths through the functional units (add, sub).
    for i, unit in enumerate(units):
        mux_in = getattr(mux, f"I{i}")
        path = TopSignalPath(
            src=SimpleAlu.a[0],
            dst=SimpleAlu.out[0],
            path=[
                InternalSignalPath(
                    src=unit.I0[0],
                    dst=unit.O[0]),
                InternalSignalPath(
                    src=mux_in[0],
                    dst=mux.O[0],
                    path=[
                        InternalSignalPath(
                            src=mux_prim.I.data[i][0],
                            dst=mux_prim.O[0])
                    ]
                )
            ]
        )
        generate_paths_test.pop_path(path)

    # Check the passthrough path.
    generate_paths_test.pop_path(
        TopSignalPath(
            src=SimpleAlu.a[0],
            dst=SimpleAlu.out[0],
            path=[
                InternalSignalPath(
                    src=mux.I2[0],
                    dst=mux.O[0],
                    path=[
                        InternalSignalPath(
                            src=mux_prim.I.data[2][0],
                            dst=mux_prim.O[0])
                    ]
                )
            ]
        ))

    # Check that we've found all the paths.
    assert len(generate_paths_test.paths) == 0


def test_thru(generate_paths_test):
    adder = generate_paths_test.get_instance("add")
    query = SignalPathQuery(SimpleAlu.a[0], SimpleAlu.out[0], [adder])
    generate_paths_test.generate_paths(query)

    mux = generate_paths_test.get_instance("Mux")
    mux_prim = generate_paths_test.get_instance("mux", type(mux))

    # Check the path through the add.
    mux_in = getattr(mux, f"I{0}")
    path = TopSignalPath(
        src=SimpleAlu.a[0],
        dst=SimpleAlu.out[0],
        path=[
            InternalSignalPath(
                src=adder.I0[0],
                dst=adder.O[0]),
            InternalSignalPath(
                src=mux_in[0],
                dst=mux.O[0],
                path=[
                    InternalSignalPath(
                        src=mux_prim.I.data[0][0],
                        dst=mux_prim.O[0])
                ]
            )
        ]
    )
    generate_paths_test.pop_path(path)

    # Check that we've found all the paths.
    assert len(generate_paths_test.paths) == 0
