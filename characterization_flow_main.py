import argparse
import dataclasses
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
import csv


@dataclasses.dataclass
class _MainOpts:
    build_dir: str = "build/"
    clock_period_start: float = 10.0
    step: float = 1.0


def _main(ckt, flow_opts: BasicFlowOpts, main_opts: _MainOpts):
    met_timing = True
    clock_period = main_opts.clock_period_start
    period_area_list = []
    while met_timing and clock_period > 0:
        flow_opts.clock_period = clock_period 
        flow = make_basic_flow(ckt, flow_opts)
        flow.build(pathlib.Path(main_opts.build_dir))

        syn_step = flow.get_step("synopsys-dc-synthesis")
        syn_step.run()

        area_report = parse_dc_area(
            syn_step.get_report(f"{ckt.name}.mapped.area.rpt"))
       
        # Did we meet timing at this clock period? 
        if "VIOLATED" in open(syn_step.get_report(f"{ckt.name}.mapped.timing.setup.rpt")).read():
            met_timing = False
        else:
            area = area_report[ckt.name]
            period_area_list.append((clock_period, area))
            clock_period -= main_opts.step

    with open(f"{ckt.name}_char.csv",'w') as out:
        csv_out = csv.writer(out, lineterminator='\n')
        csv_out.writerow(('period','area'))
        for row in period_area_list:
            csv_out.writerow(row)


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
