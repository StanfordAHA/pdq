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
    with open("garnet.py") as f:
        exec(f.read())
        kwargs = dict(add_pd=False, interconnect_only=True, standalone=True)
        gen = Garnet(1, 1, **kwargs)
    Garnet = gen.circuit()
Interconnect = type(only(Garnet.instances))
Tile_PE = type(only(find_instances_name_equals(Interconnect, "Tile_X00_Y00")))
PE = type(only(find_instances_name_equals(Tile_PE, "PE_inst0")))
CB_bit0 = type(only(find_instances_name_equals(Tile_PE, "CB_bit0")))
CB_bit1 = type(only(find_instances_name_equals(Tile_PE, "CB_bit1")))
CB_bit2 = type(only(find_instances_name_equals(Tile_PE, "CB_bit2")))
CB_data0 = type(only(find_instances_name_equals(Tile_PE, "CB_data0")))
CB_data1 = type(only(find_instances_name_equals(Tile_PE, "CB_data1")))
CB_data1 = type(only(find_instances_name_equals(Tile_PE, "CB_data1")))
SB_ID0_5TRACKS_B16_PE = type(
    only(find_instances_name_equals(Tile_PE, "SB_ID0_5TRACKS_B16_PE")))
