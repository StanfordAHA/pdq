import pathlib
import pytest

from flow_tools.basic_flow import BasicFlowOpts, make_basic_flow
from designs.registered_incrementer import RegisteredIncrementer


@pytest.mark.parametrize("design", [RegisteredIncrementer(8)])
def test_basic_flow(design):
    opts = BasicFlowOpts(pathlib.Path("flow"), pathlib.Path("build"), design)
    flow = make_basic_flow(opts)
    flow.build(opts.build_dir)
