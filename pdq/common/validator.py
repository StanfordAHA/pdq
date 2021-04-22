import dataclasses
import functools
import logging
from typing import Optional


_live_validator = False


class _ValidatorContext:
    def __enter__(*args, **kwargs):
        global _live_validator
        assert not _live_validator
        _live_validator = True

    def __exit__(*args, **kwargs):
        global _live_validator
        assert _live_validator
        _live_validator = False


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
    def _wrapper(*args, **kwargs) -> Optional[ValidatorResult]:
        global _live_validator
        if _live_validator:
            fn(*args, **kwargs)
            return
        with _ValidatorContext():
            try:
                fn(*args, **kwargs)
            except AssertionError as e:
                return ValidatorResult.make_error(e)
            return ValidatorResult.make_ok()

    return _wrapper
