import argparse
import logging
import pathlib

from pdq.common.reporting import make_header
from pdq.common.main_utils import (
    add_design_arguments, parse_design_args, slice_args)
from pdq.flow_tools.basic_flow import make_basic_flow, BasicFlowOpts
from pdq.report_parsing.parsers import parse_dc_area
from pdq.report_parsing.parsers import parse_dc_timing
from pdq.report_parsing.parsers import parse_ptpx_power


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    design_grp = add_design_arguments(parser)
    opts_grp = parser.add_argument_group("opts")
    opts_grp.add_argument("--clock_period", type=float, default=2.0)
    args = parser.parse_args()
    ckt = parse_design_args(slice_args(args, design_grp))
    opts = vars(slice_args(args, opts_grp))
    logging.info(f"Running with opts {opts}")
    _main(ckt, opts)
