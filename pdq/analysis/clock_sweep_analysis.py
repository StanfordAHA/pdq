import abc
import dataclasses
import glob
import itertools
import numpy as np
import os
import pathlib
import re
from typing import Any, Dict, List, Tuple, Union

from pdq.flow_tools.flow_wrapper import StagedFlowWrapper
from pdq.report_parsing.parsers import parse_dc_timing, parse_dc_timing_full


Numeric = Union[int, float]


@dataclasses.dataclass
class Gate:
    label: str
    type: str
    size: int


def _make_gate(pin: str, type: str) -> Gate:
    if type in ("in",):
        return None
    label = pin.split("/")[-2]
    type, size = type.split("_")
    assert size[0] == "X"
    size = int(size[1:])
    return Gate(label, type, size)


def path_to_gate_list(path: List[Tuple[str, int, str]]) -> List[Gate]:
    gates = (_make_gate(p, t) for p, _, t in path)
    gates = filter(lambda g: g is not None, gates)
    return list(gates)


class FeatureSetInterface(abc.ABC):
    @abc.abstractmethod
    def populate_from_gates(self, gates: List[Gate]):
        raise NotImplementedError()

    @abc.abstractmethod
    def as_dict(self) -> Dict[Any, Numeric]:
        raise NotImplementedError()

    @abc.abstractmethod
    def as_vector(self) -> List[Numeric]:
        raise NotImplementedError()

    def __repr__(self) -> str:
        return repr(self.as_vector())


class SimpleFeatureSet(FeatureSetInterface):
    KEYS = {
        "gate_type": ("buf", "logic"),
        "count_type": ("X1", "X2", "X4", "X8", "X16", "X32", "total")
    }

    def __init__(self):
        self._features = {
            key: 0
            for key in itertools.product(*SimpleFeatureSet.KEYS.values())
        }

    def populate_from_gates(self, gates: List[Gate]):
        for gate in gates:
            if gate.type == "BUF":
                gate_type = "buf"
            else:
                gate_type = "logic"
            count_type = f"X{gate.size}"
            assert (gate_type, count_type) in self._features
            self._features[(gate_type, count_type)] += 1
            count_type = "total"
            assert (gate_type, count_type) in self._features
            self._features[(gate_type, count_type)] += 1

    def as_dict(self) -> Dict[Any, Numeric]:
        return self._features.copy()

    def as_vector(self) -> List[Numeric]:
        return list(self._features.values())


class _FlowWrapper(StagedFlowWrapper):
    def __init__(self, build_dir: pathlib.Path):
        super().__init__("", [])
        self._set_build_dir(build_dir)
        self._populate_steps()
    
    def build(self, build_dir: pathlib.Path):
        raise TypeError("Unsupported method")


@dataclasses.dataclass(frozen=True)
class TrainingExample:
    feature_set: FeatureSetInterface
    output: Numeric
    metadata: Dict = dataclasses.field(default_factory=dict)


def get_examples_from_clock_sweep(
        module_name: str, directory: str) -> List[TrainingExample]:
    directory = directory.rstrip("/")
    basename = f"{directory}/{module_name}"
    output_directories = glob.glob(f"{basename}_*")
    output_directories = filter(os.path.isdir, output_directories)
    examples = []
    for output_directory in output_directories:
        pattern = f"{basename}_(?P<clk>.*)"
        match = re.match(pattern, output_directory)
        assert match is not None
        clk = float(match.groupdict()["clk"])
        flow = _FlowWrapper(pathlib.Path(output_directory))
        syn_step = flow.get_step("synopsys-dc-synthesis")
        rpt_filename = syn_step.get_report(
            f"{module_name}.mapped.timing.setup.rpt")
        rpt = list(zip(
            parse_dc_timing(rpt_filename),
            parse_dc_timing_full(rpt_filename)))
        for i, ((_, _, slack, data_arrival_time), path) in enumerate(rpt):
            slack, data_arrival_time = map(float, (slack, data_arrival_time))
            gates = path_to_gate_list(path)
            feature_set = SimpleFeatureSet()
            feature_set.populate_from_gates(gates)
            break
        metadata = {
            "path_number": i,
            "module_name": module_name,
            "clk": clk,
            "slack": slack,
            "data_arrival_time": data_arrival_time
        }
        examples.append(
            TrainingExample(feature_set, data_arrival_time, metadata=metadata))
    examples = list(sorted(examples, key=lambda e: e.metadata["clk"]))
    for example in examples:
        if example.metadata["slack"] < 0:
            tipping = example.metadata["data_arrival_time"]
            break
    examples = [dataclasses.replace(example, output=(example.output - tipping))
                for example in examples]
    return examples


def correlate_examples(examples: List[TrainingExample]) -> List[Numeric]:
    A = [example.feature_set.as_vector() for example in examples]
    y = [example.output for example in examples]
    A = np.asmatrix(A)
    y = np.array(y)
    x, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    x = x / np.linalg.norm(x)
    return list(x)
