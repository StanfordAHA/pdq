import argparse
import logging
import pathlib

from pdq.common.reporting import make_header
from pdq.common.main_utils import (
    add_design_arguments, parse_design_args, slice_args, add_opt_arguments,
    parse_opt_args)
from pdq.flow_tools.basic_flow import BasicFlowOpts, make_basic_flow
from pdq.report_parsing.parsers import parse_dc_area
from pdq.report_parsing.parsers import parse_dc_timing
from pdq.report_parsing.parsers import parse_ptpx_power


def _main(ckt, flow_opts: BasicFlowOpts):
    flow = make_basic_flow(ckt, flow_opts)
    flow.build(pathlib.Path("build/"))

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
    flow_opts_grp = add_opt_arguments(parser, BasicFlowOpts)
    args = parser.parse_args()
    ckt = parse_design_args(slice_args(args, design_grp))
    flow_opts = parse_opt_args(slice_args(args, flow_opts_grp), BasicFlowOpts)
    logging.info(f"Running with flow_opts {flow_opts}")
    _main(ckt, flow_opts)
