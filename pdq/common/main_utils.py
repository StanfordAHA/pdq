import argparse
import dataclasses
import functools
import importlib
import inspect
import logging
from typing import Any, Tuple, Optional


class _ParseArgError(BaseException):
    pass


class _NoArgError(_ParseArgError):
    pass


class _ArgValueError(_ParseArgError):
    pass


class _WrappedNamespace(argparse.Namespace):
    def __getattribute__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            raise _NoArgError() from None


def _arg_parser(fn):

    @functools.wraps(fn)
    def _wrapper(args: argparse.Namespace):
        args = _WrappedNamespace(**vars(args))
        return fn(args)

    return _wrapper


def _parse_gen_params(gen, args: argparse.Namespace):
    if args.params is None:
        return {}
    # NOTE(rsetaluri): We need to do this check because of how inspect.signature
    # deals with metaclasses. Specifically, for Generator2 subclasses, it grabs
    # the metaclass's __call__ function which is generic (instead of the class's
    # __init__ function).
    if inspect.isclass(gen):
        gen_sig = inspect.signature(gen.__init__)
    else:
        gen_sig = inspect.signature(gen)
    parser = argparse.ArgumentParser(add_help=False, prog=gen.__name__)
    for gen_sig_param in gen_sig.parameters.values():
        if gen_sig_param.name == "self":
            continue
        kwargs = {}
        if gen_sig_param.annotation is not inspect.Parameter.empty:
            kwargs["type"] = gen_sig_param.annotation
        if gen_sig_param.default is not inspect.Parameter.empty:
            kwargs["default"] = gen_sig_param.default
        else:
            kwargs["required"] = True
        parser.add_argument(f"-{gen_sig_param.name}", **kwargs)
    params = ["-" + p for p in args.params.split(",")]
    return vars(parser.parse_args(params))


def slice_args(args: argparse.Namespace, grp):
    keys = (action.dest for action in grp._group_actions)
    return argparse.Namespace(**{k: getattr(args, k) for k in keys})


def add_design_arguments(parser: argparse.ArgumentParser):
    design_grp = parser.add_argument_group("design")
    design_grp.add_argument("--package", type=str, required=True)
    name_grp = design_grp.add_mutually_exclusive_group(required=True)
    name_grp.add_argument("--module", type=str)
    name_grp.add_argument("--generator", type=str)
    design_grp.add_argument("--params", type=str)
    return design_grp


@_arg_parser
def parse_design_args(args: argparse.Namespace):
    if args.package is None:
        raise _ArgValueError()
    py_module = importlib.import_module(args.package)
    if args.module is not None:
        return getattr(py_module, args.module)
    if args.generator is not None:
        gen = getattr(py_module, args.generator)
        params = _parse_gen_params(gen, args)
        logging.info(f"Generator params {params}")
        return gen(**params)
    raise _ArgValueError()


def _try_get_default(field: dataclasses.Field) -> Tuple[bool, Any]:
    if field.default is not dataclasses.MISSING:
        return True, field.default
    if field.default_factory is not dataclasses.MISSING:
        return True, field.default_factory
    return False, None


def _add_bool_field(grp, field: dataclasses.Field) -> None:
    assert field.type is bool
    has_default, default_value = _try_get_default(field)
    if not has_default:
        sub_grp = grp.add_mutually_exclusive_group(required=True)
        sub_grp.add_argument(f"--{field.name}", action="store_true")
        sub_grp.add_argument(f"--no-{field.name}", action="store_false")
        return
    if not isinstance(default_value, bool):
        raise TypeError("Expected bool default value, got {default_value}")
    if default_value:
        action = "store_false"
        name = f"--no-{field.name}"
    else:
        action = "store_true"
        name = f"--{field.name}"
    grp.add_argument(
        name,
        action=action,
        dest=field.name,
        help=f"(default {field.name}={default_value})")


def add_opt_arguments(
        parser: argparse.ArgumentParser, cls: type, name: Optional[str] = None):
    if not dataclasses.is_dataclass(cls) or not isinstance(cls, type):
        raise TypeError(f"Expected dataclass, got {cls} ({type(cls)})")
    if name is None:
        name = cls.__name__
    grp = parser.add_argument_group(name)
    fields = dataclasses.fields(cls)
    for field in fields:
        if field.type is bool:
            _add_bool_field(grp, field)
            continue
        kwargs = {"type": field.type}
        has_default, default_value = _try_get_default(field)
        if not has_default:
            kwargs["required"] = False
        else:
            kwargs["help"] = f"(default={default_value})"
        grp.add_argument(f"--{field.name}", **kwargs)
    return grp


def parse_opt_args(args: argparse.Namespace, cls: type):
    if not dataclasses.is_dataclass(cls) or not isinstance(cls, type):
        raise TypeError(f"Expected dataclass, got {cls} ({type(cls)})")
    opts = {}
    fields = dataclasses.fields(cls)
    for field in fields:
        try:
            opt = getattr(args, field.name)
        except AttributeError:
            pass
        else:
            if opt is not None:
                opts[field.name] = opt
                continue
        has_default, _ = _try_get_default(field)
        if not has_default:
            raise RuntimeError(f"Missing opt '{field.name}'")
    return cls(**opts)
