import argparse
import importlib
import inspect
import pathlib
import shutil
import subprocess
import tempfile

import jinja2

from designs.registered_incrementer import *
from designs.simple_multiplier import *
from generate_testbench import generate_testbench
from report_parsing.parsers import parse_dc_area
from report_parsing.parsers import parse_dc_timing
from report_parsing.parsers import parse_ptpx_power


_FLOW_DIR = pathlib.Path("flow")
_DESIGN_FILENAME = _FLOW_DIR / "rtl/design.v"
_TESTBENCH_FILENAME = _FLOW_DIR / "testbench/testbench.sv"
_BUILD_DIR = pathlib.Path("build")
_CONSTRUCT_TPL_FILENAME = _FLOW_DIR / "construct.py.tpl"
_CONSTRUCT_OUT_FILENAME = _FLOW_DIR / "construct.py"
_QUERY_TPL_FILENAME = _FLOW_DIR / "query.tcl.tpl"
_QUERY_OUT_FILENAME = _BUILD_DIR / "query.tcl"
_SYN_RUN_STEP = "synopsys-dc-synthesis"
_SYN_RUN_STEP_NUMBER = 5
_SYN_QUERY_STEP = "synopsys-dc-query"
_SYN_QUERY_STEP_NUMBER = 6
_POWER_STEP = "synopsys-ptpx-gl"
_POWER_STEP_NUMBER = 9


def _render_template(tpl_filename, out_filename, opts):
    with open(tpl_filename, "r") as f:
        tpl = jinja2.Template(f.read())
    with open(out_filename, "w") as f:
        f.write(tpl.render(**opts))


def _run_step(build_dir, step):
    cwd = str(build_dir.resolve())
    cmd = ["make", str(step)]
    subprocess.run(cmd, cwd=cwd)


def _mflowgen_run(design_dir, build_dir, run_step=None):
    cmd = ["mflowgen", "run", "--design", str(design_dir.resolve())]
    cwd = str(build_dir.resolve())
    subprocess.run(cmd, cwd=cwd)
    if run_step is None:
        return
    _run_step(build_dir, run_step)


def _get_area_report(build_dir, design_name):
    report_dir = build_dir / "reports"
    area_report_filename = report_dir / f"{design_name}.mapped.area.rpt"
    return parse_dc_area(area_report_filename)


def _get_timing_report(build_dir, design_name):
    report_dir = build_dir / "reports"
    area_report_filename = report_dir / f"{design_name}.mapped.timing.setup.rpt"
    return parse_dc_timing(area_report_filename)

def _get_power_report(build_dir, design_name):
    report_dir = build_dir / "reports"
    power_report_filename = report_dir / f"{design_name}.power.hier.rpt"
    return parse_ptpx_power(power_report_filename)


def _post_synth_timing_query(build_dir, from_pin, to_pin):
    opts = {"from": from_pin, "to": to_pin}
    _render_template(_QUERY_TPL_FILENAME, _QUERY_OUT_FILENAME, opts)
    _run_step(build_dir, _SYN_QUERY_STEP)
    query_report = (f"{build_dir}/{_SYN_QUERY_STEP_NUMBER}-synopsys-dc-query/"
                    f"reports/timing_query.rpt")
    return parse_dc_timing(query_report)


def _main(ckt, opts):
    with tempfile.TemporaryDirectory() as directory:
        src_basename = f"{directory}/design"
        m.compile(src_basename, ckt)
        shutil.copyfile(f"{src_basename}.v", _DESIGN_FILENAME)
        generate_testbench(ckt, directory)
        shutil.copyfile(f"{directory}/{ckt.name}_tb.sv", _TESTBENCH_FILENAME)
    construct_opts = {
        "design_name": ckt.name,
        "clock_period": opts["clock_period"]
    }
    _render_template(
        _CONSTRUCT_TPL_FILENAME, _CONSTRUCT_OUT_FILENAME, construct_opts)
    _mflowgen_run(
        design_dir=_FLOW_DIR, build_dir=_BUILD_DIR, run_step=_SYN_RUN_STEP)
    syn_step_dir = f"{_SYN_RUN_STEP_NUMBER}-{_SYN_RUN_STEP}"
    syn_build_dir = _BUILD_DIR / syn_step_dir
    area_report = _get_area_report(syn_build_dir, ckt.name)
    print ("=========== AREA REPORT =======================")
    for k, v in area_report.items():
        print (f"{k}: {v}")
    print ("===============================================")
    timing_report = _get_timing_report(syn_build_dir, ckt.name)
    print ("=========== TIMING REPORT =======================")
    for k1, d in timing_report.items():
        for k2, v in d.items():
            print (f"{k1} -> {k2}: {v}")
    print ("===============================================")
    _run_step(_BUILD_DIR, _POWER_STEP)
    power_step_dir = f"{_POWER_STEP_NUMBER}-{_POWER_STEP}"
    power_build_dir = _BUILD_DIR / power_step_dir
    power_report = _get_power_report(power_build_dir, ckt.name)
    print ("=========== POWER REPORT =======================")
    for k1, d in power_report.items():
        print(f"{k1}:")
        for k2, v in d.items():
            print (f"  {k2}: {v}")
    print ("===============================================")
    # TODO(rsetaluri,alexcarsello): Make this non-design specific.
    timing_query_report = _post_synth_timing_query(_BUILD_DIR, "I0[8]", "*")
    print ("=========== TIMING QUERY REPORT =======================")
    for k1, d in timing_query_report.items():
        for k2, v in d.items():
            print (f"{k1} -> {k2}: {v}")
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
        print ("Generator params", params)
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
    print (f"Running with opts {opts}")
    _main(ckt, opts)
