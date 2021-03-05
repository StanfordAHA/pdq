import pathlib
import shutil
import subprocess
import sys
import tempfile

import jinja2

from registered_incrementer import *


_FLOW_DIR = pathlib.Path("flow")
_DST_FILENAME = _FLOW_DIR / pathlib.Path("rtl/design.v")
_BUILD_DIR = pathlib.Path("build")
_CONSTRUCT_TPL_FILENAME = _FLOW_DIR / pathlib.Path("construct.py.tpl")
_CONSTRUCT_OUT_FILENAME = _FLOW_DIR / pathlib.Path("construct.py")


def _generate_construct(tpl_filename, out_filename, opts):
    with open(tpl_filename, "r") as f:
        tpl = jinja2.Template(f.read())
    with open(out_filename, "w") as f:
        f.write(tpl.render(**opts))


def _mflowgen_run(design_dir, build_dir):
    cmd = ["mflowgen", "run", "--design", str(design_dir.resolve())]
    subprocess.run(cmd, cwd=str(build_dir.resolve()))


def _main(opts):
    ckt = RegisteredIncrementer(**opts)
    with tempfile.TemporaryDirectory() as directory:
        src_basename = f"{directory}/design"
        m.compile(src_basename, ckt)
        shutil.copyfile(f"{src_basename}.v", _DST_FILENAME)
    _generate_construct(_CONSTRUCT_TPL_FILENAME, _CONSTRUCT_OUT_FILENAME, opts)
    _mflowgen_run(design_dir=_FLOW_DIR, build_dir=_BUILD_DIR)


if __name__ == "__main__":
    opts = {"width": 32}
    if len(sys.argv > 1):
        opts["width"] = sys.argv[1]
    _main()
