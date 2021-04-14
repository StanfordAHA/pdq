import argparse
import importlib
import inspect
import logging
import pathlib

from common.reporting import make_header
from flow_tools.basic_flow import make_basic_flow, BasicFlowOpts
from report_parsing.parsers import parse_dc_area
from report_parsing.parsers import parse_dc_timing
from report_parsing.parsers import parse_ptpx_power


def _main(ckt, opts):
    opts = BasicFlowOpts(
        pathlib.Path("flow"),
        pathlib.Path("build"),
        ckt, opts.get("clock_period"))
    flow = make_basic_flow(opts)
    flow.build(opts.build_dir)

    syn_step = flow.get_step("synopsys-dc-synthesis")
    syn_step.run()

    area_report = parse_dc_area(
        syn_step.get_report(f"{ckt.name}.mapped.area.rpt"))
    print (make_header("AREA REPORT"))
    for k, v in area_report.items():
        print (f"{k}: {v}")
    print (make_header("", pad=False))

    timing_report = parse_dc_timing(
        syn_step.get_report(f"{ckt.name}.mapped.timing.setup.rpt"))
    print (make_header("TIMING REPORT"))
    for k1, d in timing_report.items():
        for k2, v in d.items():
            print (f"{k1} -> {k2}: {v}")
    print (make_header("", pad=False))

    timing_query_step = flow.get_step("synopsys-dc-query")
    timing_query_step.run()
    timing_query_report = parse_dc_timing(
        timing_query_step.get_report("timing_query.rpt"))
    print (make_header("TIMING QUERY REPORT"))
    for k1, d in timing_query_report.items():
        for k2, v in d.items():
            print (f"{k1} -> {k2}: {v}")
    print (make_header("", pad=False))

    power_step = flow.get_step("synopsys-ptpx-gl")
    power_step.run()
    power_report = parse_ptpx_power(
        power_step.get_report(f"{ckt.name}.power.hier.rpt"))
    print (make_header("POWER REPORT"))
    for k1, d in power_report.items():
        print(f"{k1}:")
        for k2, v in d.items():
            print (f"  {k2}: {v}")
    print (make_header("", pad=False))


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
