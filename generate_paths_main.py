import argparse

from pdq.common.main_utils import (
    add_design_arguments, parse_design_args, slice_args)
from pdq.circuit_tools.generate_paths import SignalPathQuery, generate_paths
from pdq.circuit_tools.signal_path import SignalPath


def _parse_query_args(ckt, args: argparse.Namespace):
    locals_ = locals().copy()
    locals_.update({ckt.name: ckt})
    # NOTE(rsetaluri): Needs to be "from_" and need to call getattr() (rather
    # than dot syntax) since "from" is a reserved kw.
    from_ = eval(getattr(args, "from"), globals(), locals_)
    to = eval(args.to, globals(), locals_)
    return SignalPathQuery(src=from_, dst=to)


def _add_query_arguments(parser: argparse.ArgumentParser):
    grp = parser.add_argument_group("query")
    grp.add_argument("-from", type=str, required=True)
    grp.add_argument("-to", type=str, required=True)
    return grp


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    design_grp = add_design_arguments(parser)
    query_grp = _add_query_arguments(parser)
    args = parser.parse_args()
    ckt = parse_design_args(slice_args(args, design_grp))
    query = _parse_query_args(ckt, slice_args(args, query_grp))
    paths = generate_paths(ckt, query)
    for path in paths:
        print (repr(path))
