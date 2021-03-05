import pathlib
import shutil
import subprocess
import tempfile

from registered_incrementer import *


_FLOW_DIR = pathlib.Path("flow")
_DST_FILENAME = _FLOW_DIR / pathlib.Path("rtl/design.v")
_BUILD_DIR = pathlib.Path("build")


def _mflowgen_run(design_dir, build_dir):
    cmd = ["mflowgen", "run", "--design", str(design_dir.resolve())]    
    subprocess.run(cmd, cwd=str(build_dir.resolve()))


def _main():
    ckt = RegisteredIncrementer(32)
    with tempfile.TemporaryDirectory() as directory:
        src_basename = f"{directory}/design"
        m.compile(src_basename, ckt)
        shutil.copyfile(f"{src_basename}.v", _DST_FILENAME)
    _mflowgen_run(design_dir=_FLOW_DIR, build_dir=_BUILD_DIR)


if __name__ == "__main__":
    _main()
