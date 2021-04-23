from typing import Any, Callable, Iterable


def only(lst: Iterable):
    err = f"iterable expected to have exactly one element; got {lst}"
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


def try_call(fn: Callable[[], Any], ExceptionType: Any):
    if ExceptionType is None:
        ExceptionType = BaseException
    try:
        ret = fn()
    except ExceptionType:
        pass
    else:
        return ret
