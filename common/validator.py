import dataclasses
import functools


@dataclasses.dataclass(frozen=True)
class ValidatorResult:
    ok: bool
    msg: str = ""

    def __bool__(self):
        return self.ok

    @classmethod
    def make_ok(cls):
        return cls(True)

    @classmethod
    def make_error(cls, msg: str):
        return cls(False, msg=msg)


def validator(fn):

    @functools.wraps(fn)
    def _wrapper(*args, **kwargs) -> ValidatorResult:
        try:
            fn(*args, **kwargs)
        except AssertionError as e:
            return ValidatorResult.make_error(str(e))
        return ValidatorResult.make_ok()

    return _wrapper
