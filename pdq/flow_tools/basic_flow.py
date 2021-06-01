import dataclasses
import pathlib
import tempfile

import magma as m

from pdq.flow_tools.templated_flow_builder import (
    TemplatedFlowBuilder, FileTemplate, FileCopy)
from pdq.circuit_tools.generate_testbench import generate_testbench


_BASIC_FLOW_FLOW_DIR = pathlib.Path("basic_flow")


@dataclasses.dataclass(frozen=True)
class BasicFlowOpts:
    clock_period: float = 2.0
    explore: bool = False
    inline: bool = False
    adk_name: str = 'freepdk-45nm'
    macros: str = ""


def parse_macro_arg(macro_arg: str):
    macro_list = [s.strip() for s in macro_arg.split(",")]
    return macro_list


def make_basic_flow(ckt: m.DefineCircuitKind, opts: BasicFlowOpts):
    clk = m.get_default_clocks(ckt)[m.Clock]
    clk_name = clk if clk is None else f"'{clk.name.name}'"
    construct_opts = {
        "design_name": ckt.name,
        "clock_period": opts.clock_period,
        "clock_net": clk_name,
        "explore": opts.explore,
        "adk_name": opts.adk_name,
        "macro_files": parse_macro_arg(opts.macros),
    }
    builder = TemplatedFlowBuilder()
    builder.set_flow_dir(_BASIC_FLOW_FLOW_DIR)
    builder.add_template(
        FileTemplate(
            builder.get_relative("construct.py.tpl"),
            builder.get_relative("construct.py"),
            construct_opts))
    # TODO(rsetaluri,alexcarsello): Make pins non-design specific.
    builder.add_template(
        FileTemplate(
            builder.get_relative("query.tcl.tpl"),
            builder.get_relative("synopsys-dc-query/scripts/query.tcl"),
            {"from": "I0[8]", "to": "*"}))
    with tempfile.TemporaryDirectory() as directory:
        design_basename = f"{directory}/design"
        m.compile(
            design_basename, ckt, coreir_libs={"float_DW"}, inline=opts.inline)
        builder.add_template(
            FileCopy(
                f"{design_basename}.v",
                builder.get_relative("rtl/design.v")))
        generate_testbench(ckt, directory)
        builder.add_template(
            FileCopy(
                f"{directory}/{ckt.name}_tb.sv",
                builder.get_relative("testbench/testbench.sv")))
        return builder.build()
