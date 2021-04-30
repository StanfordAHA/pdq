import argparse
import functools
import importlib
import inspect
import logging


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
    try:
        gen.__init__
    except AttributeError:
        gen_sig = inspect.signature(gen)
    else:
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
