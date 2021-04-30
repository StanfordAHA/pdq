import dataclasses
import pathlib
import tempfile

import magma as m

from pdq.flow_tools.templated_flow_builder import (
    TemplatedFlowBuilder, FileTemplate, FileCopy)
from pdq.circuit_tools.generate_testbench import generate_testbench


_BASIC_FLOW_FLOW_DIR = pathlib.Path("basic_flow")
_BASIC_FLOW_BUILD_DIR = pathlib.Path("build")


def basic_flow_build_dir():
    return _BASIC_FLOW_BUILD_DIR


@dataclasses.dataclass(frozen=True)
class BasicFlowOpts:
    clock_period: float = 2.0
    inline: bool = False


def make_basic_flow(ckt: m.DefineCircuitKind, opts: BasicFlowOpts):
    clk = m.get_default_clocks(ckt)[m.Clock]
    clk_name = clk if clk is None else f"'{clk.name.name}'"
    construct_opts = {
        "design_name": ckt.name,
        "clock_period": opts.clock_period,
        "clock_net": clk_name,
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
            _BASIC_FLOW_BUILD_DIR / "query.tcl",
            dict(from_pin="I0[8]", to_pin="*")))
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
