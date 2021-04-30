import abc
import dataclasses
import logging
import pathlib
import subprocess
import sys
from typing import List, Union
import weakref
import yaml


@dataclasses.dataclass
class StepWrapper:
    name: str
    number: int

    def __post_init__(self):
        self._flow = None

    def bind(self, flow: 'FlowWrapperInterface'):
        if self._flow is not None:
            raise RuntimeError("Step already bound")
        self._flow = weakref.ref(flow)

    @property
    def bound(self) -> bool:
        return self._flow is not None

    @property
    def flow(self) -> 'FlowWrapperInterface':
        if self._flow is None:
            raise RuntimeError("Can not get flow of unbound step")
        return self._flow()

    def run(self, **kwargs):
        self._flow()._run_step(self, **kwargs)

    def get_build_dir(self):
        return self._flow()._get_build_dir_of_step(self)

    def get_report(self, report_name):
        return self.get_build_dir() / "reports" / report_name


@dataclasses.dataclass
class FlowWrapperInterface(abc.ABC):
    design_dir: pathlib.Path
    steps: List[StepWrapper]

    @abc.abstractmethod
    def build(self, build_dir: pathlib.Path):
        raise NotImplementedError()

    def get_step(self, name_or_number: Union[int, str]) -> StepWrapper:
        if isinstance(name_or_number, int):
            return self.steps[name_or_number]
        name_to_number = {step.name: step.number for step in self.steps}
        return self.steps[name_to_number[name_or_number]]

    def _run_step(self, step: StepWrapper, **kwargs):
        logging.info(f"Running step {step.name}")
        # By default, we want to use shell=True, so we need to adjust command.
        opts = kwargs.copy()
        shell = opts.setdefault("shell", True)
        cmd = ["make", step.name]
        if shell:
            cmd = " ".join(cmd)
        self._run_build_cmd(cmd, **opts)

    def _get_build_dir_of_step(self, step: StepWrapper) -> pathlib.Path:
        build_dir = pathlib.Path(self._get_build_dir())
        return build_dir / f"{step.number}-{step.name}"

    def _get_build_dir(self):
        return self._build_dir

    def _set_build_dir(self, build_dir):
        self._build_dir = build_dir

    def _run_build_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, cwd=self._get_build_dir(), **kwargs)


@dataclasses.dataclass
class StagedFlowWrapper(FlowWrapperInterface):
    def build(self, build_dir: pathlib.Path):
        self._set_build_dir(str(build_dir.resolve()))
        cmd = ["mflowgen", "run", "--design", str(self.design_dir.resolve())]
        self._run_build_cmd(cmd)
        self._populate_steps()

    def _populate_steps(self):
        self.steps.clear()
        ret = self._run_build_cmd(["make", "list"], capture_output=True)
        targets = yaml.safe_load(ret.stdout)["Targets"]
        for dct in targets:
            assert len(dct) == 1
            number, name = list(dct.items())[0]
            assert number == len(self.steps)
            step = StepWrapper(name, number)
            step.bind(self)
            self.steps.append(step)
