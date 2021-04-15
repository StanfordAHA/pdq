from typing import Iterable


def only(lst: Iterable):
    err = f"iterable expected to have exactly one element; got {lst}"
    it = iter(lst)
    try:
        value = next(it)
    except StopIteration:
        raise ValueError(err)
    try:
        next(it)
    except StopIteration:
        return value
    else:
        raise ValueError(err)
