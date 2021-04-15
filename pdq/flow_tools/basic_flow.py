import dataclasses
import pathlib
import tempfile

import magma as m

from pdq.flow_tools.templated_flow_builder import (
    TemplatedFlowBuilder, FileTemplate, FileCopy)
from pdq.circuit_tools.generate_testbench import generate_testbench


@dataclasses.dataclass(frozen=True)
class BasicFlowOpts:
    flow_dir: pathlib.Path
    build_dir: pathlib.Path
    ckt: m.DefineCircuitKind
    clock_period: float = 2.0


def make_basic_flow(opts: BasicFlowOpts):
    clk = m.get_default_clocks(opts.ckt)[m.Clock]
    clk_name = clk if clk is None else f"'{clk.name.name}'"
    construct_opts = {
        "design_name": opts.ckt.name,
        "clock_period": opts.clock_period,
        "clock_net": clk_name,
    }
    builder = TemplatedFlowBuilder()
    builder.set_flow_dir(opts.flow_dir)
    builder.add_template(
        FileTemplate(
            builder.get_relative("construct.py.tpl"),
            builder.get_relative("construct.py"),
            construct_opts))
    # TODO(rsetaluri,alexcarsello): Make pins non-design specific.
    builder.add_template(
        FileTemplate(
            builder.get_relative("query.tcl.tpl"),
            opts.build_dir / "query.tcl",
            dict(from_pin="I0[8]", to_pin="*")))
    with tempfile.TemporaryDirectory() as directory:
        design_basename = f"{directory}/design"
        m.compile(design_basename, opts.ckt, coreir_libs={"float_DW"})
        builder.add_template(
            FileCopy(
                f"{design_basename}.v",
                builder.get_relative("rtl/design.v")))
        generate_testbench(opts.ckt, directory)
        builder.add_template(
            FileCopy(
                f"{directory}/{opts.ckt.name}_tb.sv",
                builder.get_relative("testbench/testbench.sv")))
        return builder.build()
