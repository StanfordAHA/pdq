import pathlib
import shutil
import subprocess
import sys
import tempfile

import jinja2

from registered_incrementer import *
from report_parsing.parse_dc_area import parse_dc_area


_FLOW_DIR = pathlib.Path("flow")
_DST_FILENAME = _FLOW_DIR / "rtl/design.v"
_BUILD_DIR = pathlib.Path("build")
_CONSTRUCT_TPL_FILENAME = _FLOW_DIR / "construct.py.tpl"
_CONSTRUCT_OUT_FILENAME = _FLOW_DIR / "construct.py"
_SYN_RUN_STEP = "synopsys-dc-synthesis"
_SYN_RUN_STEP_NUMBER = 4


def _generate_construct(tpl_filename, out_filename, opts):
    with open(tpl_filename, "r") as f:
        tpl = jinja2.Template(f.read())
    with open(out_filename, "w") as f:
        f.write(tpl.render(**opts))


def _mflowgen_run(design_dir, build_dir, run_step=None):
    cmd = ["mflowgen", "run", "--design", str(design_dir.resolve())]
    cwd = str(build_dir.resolve())
    subprocess.run(cmd, cwd=cwd)
    if run_step is None:
        return
    cmd = ["make", str(run_step)]
    subprocess.run(cmd, cwd=cwd)


def _get_area_report(build_dir, design_name):
    report_dir = build_dir / "reports"
    area_report_filename = report_dir / f"{design_name}.mapped.area.rpt"
    return parse_dc_area(area_report_filename)


def _main(opts):
    ckt = RegisteredIncrementer(**opts)
    with tempfile.TemporaryDirectory() as directory:
        src_basename = f"{directory}/design"
        m.compile(src_basename, ckt)
        shutil.copyfile(f"{src_basename}.v", _DST_FILENAME)
    _generate_construct(_CONSTRUCT_TPL_FILENAME, _CONSTRUCT_OUT_FILENAME, opts)
    _mflowgen_run(
        design_dir=_FLOW_DIR, build_dir=_BUILD_DIR, run_step=_SYN_RUN_STEP)
    syn_step_dir = f"{_SYN_RUN_STEP_NUMBER}-{_SYN_RUN_STEP}"
    syn_build_dir = _BUILD_DIR / syn_step_dir
    area_report = _get_area_report(syn_build_dir, ckt.name)
    print ("=========== AREA REPORT =======================")
    for k, v in area_report.items():
        print (f"{k}: {v}")
    print ("===============================================")


if __name__ == "__main__":
    opts = {"width": 32}
    if len(sys.argv) > 1:
        opts["width"] = sys.argv[1]
    _main(opts)
