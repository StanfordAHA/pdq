import dataclasses
import functools
import logging


@dataclasses.dataclass(frozen=True)
class ValidatorResult:
    ok: bool
    err: Exception = None

    def __bool__(self):
        return self.ok

    @classmethod
    def make_ok(cls):
        return cls(True)

    @classmethod
    def make_error(cls, err: Exception):
        return cls(False, err=err)

    def throw(self):
        if self.ok:
            logging.warning("Trying to throw from ok result; returning")
            return
        raise self.err


def validator(fn):

    @functools.wraps(fn)
    def _wrapper(*args, **kwargs) -> ValidatorResult:
        try:
            fn(*args, **kwargs)
        except AssertionError as e:
            return ValidatorResult.make_error(e)
        return ValidatorResult.make_ok()

    return _wrapper
