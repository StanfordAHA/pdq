import magma as m
m.config.set_debug_mode(True)
m.config.config.disable_smart_naming = True

from magma_riscv_mini.riscv_mini.core import Core
from pdq.circuit_tools.circuit_utils import find_instances_name_equals
from pdq.common.algorithms import only


Core32 = Core(x_len=32)
inst_path = "Datapath_inst0/CSRGen_inst0/Mux2xBits32_inst32"
port_path = "Datapath_inst0/CSRGen_inst0/Mux2xBits32_inst32/O[23]"


def find_inst(defn, path, sep="/"):
    parts = path.split(sep)
    curr = defn
    while parts:
        inst_name = parts.pop(0)
        inst = only(find_instances_name_equals(curr, inst_name))
        curr = type(inst)
    return inst


inst = find_inst(Core32, inst_path)
print (inst.debug_info)
