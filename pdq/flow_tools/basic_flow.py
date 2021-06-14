import dataclasses
import pathlib
import tempfile
import os

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


def _get_macro_files(path):
    """Takes in a path and gets all macro files present there."""
    macro_file_list = []
    # If it's a file, copy it and add it to the filename list.
    if os.path.isfile(path):
        if path.lower().endswith(('.db', '.lef', '.v')):
            macro_file_list.append(path)
    # If it's a directory, recursively search for macro files.
    elif os.path.isdir(path):
        for f in os.listdir(path):
            macro_file_list += _get_macro_files(os.path.join(path, f))

    return macro_file_list


def make_basic_flow(ckt: m.DefineCircuitKind, opts: BasicFlowOpts):
    # First, parse the macro args and copy all the files to the macro node.
    macro_path_list = [s.strip() for s in opts.macros.split(",")]
    macro_file_list = []
    for path in macro_path_list:
        macro_file_list += _get_macro_files(path)

    macro_file_basenames = [os.path.basename(f) for f in macro_file_list]
                
    clk = m.wire_clock.get_default_clocks(ckt)[m.Clock]
    clk_name = clk if clk is None else f"'{clk.name.name}'"
    construct_opts = {
        "design_name": ckt.name,
        "clock_period": opts.clock_period,
        "clock_net": clk_name,
        "explore": opts.explore,
        "adk_name": opts.adk_name,
        "macro_files": macro_file_basenames,
    }
    builder = TemplatedFlowBuilder()
    builder.set_flow_dir(_BASIC_FLOW_FLOW_DIR)
    builder.add_template(
        FileTemplate(
            builder.get_relative("construct.py.tpl"),
            builder.get_relative("construct.py"),
            construct_opts))

    # Copy all macro files to macro node
    for path in macro_file_list:
        builder.add_template(
            FileCopy(
                path,
                builder.get_relative(f"macros/{os.path.basename(path)}")))

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
