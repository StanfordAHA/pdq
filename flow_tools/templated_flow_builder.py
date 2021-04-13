import abc
import dataclasses
import logging
import pathlib
import shutil
from typing import Dict

import jinja2

from flow_tools.flow_wrapper import FlowWrapperInterface, StagedFlowWrapper


class TemplateAction(abc.ABC):
    @abc.abstractmethod
    def __call__(self):
        raise NotImplementedError()


@dataclasses.dataclass
class FileTemplate(TemplateAction):
    tpl_filename: str
    dst_filename: str
    opts: Dict

    def __call__(self):
        logging.info(f"Templating {self.tpl_filename} into {self.dst_filename} "
                     f"with opts {self.opts}")
        with open(self.tpl_filename, "r") as f:
            tpl = jinja2.Template(f.read())
        with open(self.dst_filename, "w") as f:
            f.write(tpl.render(**self.opts))


@dataclasses.dataclass
class FileCopy(TemplateAction):
    src_filename: str
    dst_filename: str

    def __call__(self):
        logging.info(f"Copying {self.src_filename} into {self.dst_filename}")
        shutil.copyfile(self.src_filename, self.dst_filename)


class TemplatedFlowBuilder:
    def __init__(self):
        self._flow_dir = None
        self._templates = []
        self._built = False

    def __repr__(self):
        cls = type(self)
        return (f"{cls.__name__}(dir={repr(self._flow_dir)}, "
                f"templates={self._templates})")

    def set_flow_dir(self, dir_: str):
        self._flow_dir = pathlib.Path(dir_)

    def add_template(self, tpl: TemplateAction):
        self._templates.append(tpl)

    def build(self) -> FlowWrapperInterface:
        if self._built:
            raise RuntimeError("Can not call build() multiple times")
        flow_wrapper = self._build()
        self._built = True
        return flow_wrapper

    def get_relative(self, path: str) -> pathlib.Path:
        return self._flow_dir / pathlib.Path(path)

    def _build(self) -> FlowWrapperInterface:
        logging.info(f"Building templated flow in {self._flow_dir}")
        for tpl in self._templates:
            tpl()
        return StagedFlowWrapper(self._flow_dir, [])
