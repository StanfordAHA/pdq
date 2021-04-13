import argparse
import importlib
import inspect
import logging
import pathlib
import tempfile

import magma as m

from generate_testbench import generate_testbench
from report_parsing.parsers import parse_dc_area
from report_parsing.parsers import parse_dc_timing
from report_parsing.parsers import parse_ptpx_power
from flow_tools.templated_flow_builder import *


_FLOW_DIR = pathlib.Path("flow")
_BUILD_DIR = pathlib.Path("build")


def _make_flow(ckt, opts):
    clk = m.get_default_clocks(ckt)[m.Clock]
    clk_name = clk if clk is None else f"'{clk.name.name}'"
    construct_opts = {
        "design_name": ckt.name,
        "clock_period": opts["clock_period"],
        "clock_net": clk_name,
    }
    builder = TemplatedFlowBuilder()
    builder.set_flow_dir(_FLOW_DIR)
    builder.add_template(
        FileTemplate(
            builder.get_relative("construct.py.tpl"),
            builder.get_relative("construct.py"),
            construct_opts))
    # TODO(rsetaluri,alexcarsello): Make pins non-design specific.
    builder.add_template(
        FileTemplate(
            builder.get_relative("query.tcl.tpl"),
            _BUILD_DIR / "query.tcl",
            dict(from_pin="I0[8]", to_pin="*")))
    with tempfile.TemporaryDirectory() as directory:
        design_basename = f"{directory}/design"
        m.compile(design_basename, ckt, coreir_libs={"float_DW"})
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


def _main(ckt, opts):
    flow = _make_flow(ckt, opts)
    flow.build(_BUILD_DIR)
    syn_step = flow.get_step("synopsys-dc-synthesis")
    syn_step.run()

    area_report = parse_dc_area(
        syn_step.get_report(f"{ckt.name}.mapped.area.rpt"))
    print ("=========== AREA REPORT =======================")
    for k, v in area_report.items():
        print (f"{k}: {v}")
    print ("===============================================")

    timing_report = parse_dc_timing(
        syn_step.get_report(f"{ckt.name}.mapped.timing.setup.rpt"))
    print ("=========== TIMING REPORT =======================")
    for k1, d in timing_report.items():
        for k2, v in d.items():
            print (f"{k1} -> {k2}: {v}")
    print ("===============================================")

    timing_query_step = flow.get_step("synopsys-dc-query")
    timing_query_step.run()
    timing_query_report = parse_dc_timing(
        timing_query_step.get_report("timing_query.rpt"))
    print ("=========== TIMING QUERY REPORT =======================")
    for k1, d in timing_query_report.items():
        for k2, v in d.items():
            print (f"{k1} -> {k2}: {v}")
    print ("===============================================")

    power_step = flow.get_step("synopsys-ptpx-gl")
    power_step.run()
    power_report = parse_ptpx_power(
        power_step.get_report(f"{ckt.name}.power.hier.rpt"))


    print ("=========== POWER REPORT =======================")
    for k1, d in power_report.items():
        print(f"{k1}:")
        for k2, v in d.items():
            print (f"  {k2}: {v}")
    print ("===============================================")


def _make_params(gen, args):
    if args.params is None:
        return {}
    gen_sig = inspect.signature(gen.__init__)
    parser = argparse.ArgumentParser(add_help=False, prog=gen.__name__)
    for gen_sig_param in gen_sig.parameters.values():
        if gen_sig_param.name == "self":
            continue
        kwargs = {}
        if gen_sig_param.annotation is not inspect.Parameter.empty:
            kwargs["type"] = gen_sig_param.annotation
        if gen_sig_param.default is not inspect.Parameter.empty:
            kwargs["default"] = gen_sig_param.default
        parser.add_argument(f"-{gen_sig_param.name}", **kwargs)
    params = ["-" + p for p in args.params.split(",")]
    return vars(parser.parse_args(params))


def _get_ckt(args):
    py_module = importlib.import_module(args.package)
    if args.module is not None:
        return getattr(py_module, args.module)
    if args.generator is not None:
        gen = getattr(py_module, args.generator)
        params = _make_params(gen, args)
        logging.info(f"Generator params {params}")
        return gen(**params)
    raise NotImplementedError()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=str)
    ckt_group = parser.add_mutually_exclusive_group(required=True)
    ckt_group.add_argument("--module", type=str)
    ckt_group.add_argument("--generator", type=str)
    parser.add_argument("--params", type=str)
    opts_group = parser.add_argument_group("opts")
    opts_group.add_argument("--clock_period", type=float, default=2.0)
    args = parser.parse_args()
    ckt = _get_ckt(args)
    opts_keys = list(action.dest for action in opts_group._group_actions)
    opts = {k: getattr(args, k) for k in opts_keys}
    logging.info(f"Running with opts {opts}")
    _main(ckt, opts)
