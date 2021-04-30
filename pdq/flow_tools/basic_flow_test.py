import pathlib
import pytest

from designs.registered_incrementer import RegisteredIncrementer
from pdq.flow_tools.basic_flow import (
    BasicFlowOpts, make_basic_flow, basic_flow_build_dir)


@pytest.mark.parametrize("design", [RegisteredIncrementer(8)])
def test_basic_flow(design):
    opts = BasicFlowOpts()
    flow = make_basic_flow(design, opts)
    flow.build(basic_flow_build_dir())
