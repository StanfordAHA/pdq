from typing import Any, Callable, Iterable, List


def only(lst: Iterable):
    it = iter(lst)
    try:
        value = next(it)
    except StopIteration:
        raise ValueError("Expected one element, got []") from None
    try:
        new_value = next(it)
    except StopIteration:
        return value
    else:
        msg = f"Expecte one element got {[value, new_value] + list(it)}"
        raise ValueError(msg)


def first(lst: Iterable):
    it = iter(lst)
    try:
        value = next(it)
    except StopIteration:
        raise ValueError("Expected at least one element, got []") from None
    return value


def try_call(fn: Callable[[], Any], ExceptionType: Any):
    if ExceptionType is None:
        ExceptionType = BaseException
    try:
        ret = fn()
    except ExceptionType:
        pass
    else:
        return ret


def remove_all(l: List, to_remove: Iterable):
    for ii in to_remove:
        l.remove(ii)
