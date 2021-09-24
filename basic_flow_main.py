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

def parse_setup_rpt(lines):
    paths = []
    cur_path = []
    in_path = False
    hit_slack = True
    last_cell = ""
    for line in lines:
        line = line.strip()
        if in_path and "data arrival time" in line:
            in_path = False
            paths.append(cur_path)
            cur_path = []
        if in_path and not " (net)" in line and not "input external delay" in line:
            name = line[:line.index(" (")]
            cell = line[line.index("(") + 1:line.index(")")]
            # every real cell has an entry for both the input port and output port; skip the output
            if "_" in cell:
                if cell == last_cell:
                    last_cell = ""
                    continue
                else:
                    last_cell = cell
            split = list(filter(lambda x: x != '', line.split(" ")))
            split.reverse() # look from the end
            # index of "r" or "f" character
            ref_idx = next(i for i, e in enumerate(split) if len(e) == 1)
            try:
                incr = float(split[ref_idx + 2])
            except ValueError:
                incr = float(split[ref_idx + 3]) # try the next one
            cur_path.append((name, incr, cell))
        if not in_path and not hit_slack and "slack" in line:
            hit_slack = True # make sure we have really left the path
        if not in_path and hit_slack and ("clock network delay" in line or "input external delay" in line):
            in_path = True
            hit_slack = False
  
    return paths

# cross of size and buf/not buf
def get_features(paths):
    import itertools
    features = []
    for p in paths:
        f = {(buf, size): 0 for (buf, size) in itertools.product((True, False), (1, 2, 4, 8, 16, 32))}
        for _, _, cell in p:
            if "_" not in cell:
                continue
            name, size = cell.split("_")
            size = int(size[1:])
            buf = (name == "BUF")
            f[(buf, size)] += 1
        features.append(f)
    return features

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
    feature_map = {}
    while True:
        tried_clocks.append(flow_opts.clock_period)
        main_opts = dataclasses.replace(main_opts, build_dir=('build_' + str(flow_opts.clock_period)))
        flow = make_basic_flow(ckt, flow_opts)
        flow.build(pathlib.Path(main_opts.build_dir))

        syn_step = flow.get_step("synopsys-dc-synthesis")
        syn_step.run()
        timing = syn_step.get_report(f"{ckt.name}.mapped.timing.setup.rpt")
        feature_map[flow_opts.clock_period] = get_features(parse_setup_rpt(open(timing, 'r').readlines()))
        if terminate:
            break
        has_violated = len(get_keyword_lines(timing, "VIOLATED")) > 0
        if has_violated:
            min_clock = flow_opts.clock_period
        else:
            max_clock = flow_opts.clock_period
        flow_opts = dataclasses.replace(flow_opts, clock_period=(min_clock+max_clock)/2)
        if flow_opts.clock_period < 1.05 * min_clock: # within 20%
            terminate = True
            flow_opts = dataclasses.replace(flow_opts, clock_period=min_clock)
            if has_violated: # we just computed the result with min_clock, so break now
                break

    print("List of tried clocks: " + str(tried_clocks))
    for (k, v) in feature_map.items():
        print("Features for clock " + str(k))
        for ff in v:
            print(list(ff.values()))
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
