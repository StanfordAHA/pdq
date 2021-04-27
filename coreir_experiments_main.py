import argparse
import itertools
import logging
import pathlib
import subprocess

from designs.coreir_ops import binary_op
from pdq.flow_tools.basic_flow import (
    BasicFlowOpts, make_basic_flow, basic_flow_build_dir)


def _run_op(width: int, op: str, clock_period: float):
    ckt = binary_op(width, op)
    opts = BasicFlowOpts(
        clock_period=clock_period,
        inline=True)
    flow = make_basic_flow(ckt, opts)
    flow.build(basic_flow_build_dir())

    syn_step = flow.get_step("synopsys-dc-synthesis")
    logging.info(f"Running op={op}, width={width}, clk={clock_period}")
    syn_step.run(shell=False, check=True, capture_output=True)
    logging.info("Finished running")

    return flow, syn_step


def _main():
    subprocess.call("rm -rf build/*", shell=True)
    subprocess.call("mkdir -p reports/", shell=True)
    widths = itertools.chain(range(1, 2), range(2, 128, 2))
    ops = "add", "mul", "sub", "or_", "and_", "xor"
    clock_period = [float(i) for i in range(1, 11)]
    space = itertools.product(widths, ops, clock_period)
    for width, op, clock_period in space:
        flow, step = _run_op(width, op, clock_period)
        src = step.get_build_dir() / "reports"
        dst = pathlib.Path("reports") / f"reports.{width}-{op}-{clock_period}"
        logging.info(f"Copying {src} to {dst}")
        subprocess.call(f"cp -r {src} {dst}", shell=True)
        # A bit of a hack...
        flow._run_build_cmd(["make", "clean-all"])
        logging.info("Cleaned")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.INFO)
    _main()
