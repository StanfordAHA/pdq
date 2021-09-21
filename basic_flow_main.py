import argparse
import dataclasses
import logging
import pathlib

import magma as m
from pdq.common.reporting import make_header
from pdq.common.main_utils import (
    add_design_arguments, parse_design_args, slice_args, add_opt_arguments,
    parse_opt_args)
from pdq.flow_tools.basic_flow import BasicFlowOpts, make_basic_flow
from pdq.report_parsing.parsers import parse_dc_area
from pdq.report_parsing.parsers import parse_dc_timing
from pdq.report_parsing.parsers import parse_ptpx_power
from pdq.report_parsing.parsers import get_keyword_lines
from pdq.circuit_tools.graph_view import BitPortNode
from pdq.circuit_tools.partial_extract import extract_from_terminals
from pdq.circuit_tools.signal_path import Scope, ScopedBit


@dataclasses.dataclass
class _MainOpts:
    build_dir: str = "build/"
    skip_power: bool = False
    sweep_clock: bool = False
    partial_endpoint: str = ""


def _main(ckt, flow_opts: BasicFlowOpts, main_opts: _MainOpts):
    if main_opts.partial_endpoint != "":
        bits = list(m.as_bits(eval(main_opts.partial_endpoint)))
        terms = [BitPortNode(ScopedBit(b, Scope(ckt))) for b in bits]
        ckt = extract_from_terminals(ckt, terms)
    min_clock = 0
    max_clock = flow_opts.clock_period
    flow_opts = flow_opts if not main_opts.sweep_clock else dataclasses.replace(flow_opts,
        clock_period=(min_clock+max_clock)/2)
    terminate = not main_opts.sweep_clock
    tried_clocks = []
    while True:
        tried_clocks.append(flow_opts.clock_period)
        flow = make_basic_flow(ckt, flow_opts)
        flow.build(pathlib.Path(main_opts.build_dir))

        syn_step = flow.get_step("synopsys-dc-synthesis")
        syn_step.run()
        if terminate:
            break
        timing = syn_step.get_report(f"{ckt.name}.mapped.timing.setup.rpt")
        has_violated = len(get_keyword_lines(timing, "VIOLATED")) > 0
        if has_violated:
            min_clock = flow_opts.clock_period
        else:
            max_clock = flow_opts.clock_period
        flow_opts = dataclasses.replace(flow_opts, clock_period=(min_clock+max_clock)/2)
        if flow_opts.clock_period < 1.2 * min_clock: # within 20%
            terminate = True
            flow_opts = dataclasses.replace(flow_opts, clock_period=min_clock)
            if has_violated: # we just computed the result with min_clock, so break now
                break

    print("List of tried clocks: " + str(tried_clocks))
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

    if not main_opts.skip_power:
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
    main_opts_grp = add_opt_arguments(parser, _MainOpts)
    args = parser.parse_args()
    ckt = parse_design_args(slice_args(args, design_grp))
    flow_opts = parse_opt_args(slice_args(args, flow_opts_grp), BasicFlowOpts)
    main_opts = parse_opt_args(slice_args(args, main_opts_grp), _MainOpts)
    logging.info(f"Running with flow_opts {flow_opts}")
    logging.info(f"Running with main_opts {main_opts}")
    _main(ckt, flow_opts, main_opts)
