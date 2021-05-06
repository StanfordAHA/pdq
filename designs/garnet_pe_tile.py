import contextlib
import os
import sys

from pdq.common.algorithms import only
from pdq.circuit_tools.circuit_utils import find_instances_name_equals


@contextlib.contextmanager
def _pushd(new_dir):
    prev_dir = os.getcwd()
    prev_path = sys.path.copy()
    os.chdir(new_dir)
    sys.path.append(".")
    try:
        yield
    finally:
        os.chdir(prev_dir)
        sys.path = prev_path


with _pushd("garnet"):
    with open("garnet.py") as _f:
        exec(_f.read())
        _kwargs = dict(add_pd=False, interconnect_only=True, standalone=True)
        _gen = Garnet(1, 1, **_kwargs)
    _Garnet = _gen.circuit()
_Interconnect = type(only(_Garnet.instances))
_Tile_PE = type(only(find_instances_name_equals(_Interconnect, "Tile_X00_Y00")))

# Make component(s) public.
Tile_PE = _Tile_PE
