import dataclasses
from typing import Optional, Tuple

from pdq.circuit_tools.signal_path import ScopedBit


ValueList = Tuple[ScopedBit]


@dataclasses.dataclass(frozen=True)
class PartialExtractQuery:
    from_list: Tuple[ScopedBit] = tuple()
    to_list: Tuple[ScopedBit] = tuple()
    through_lists: Tuple[Tuple[ScopedBit]] = tuple()


def query_is_empty(query: PartialExtractQuery) -> bool:
    if query.from_list or query.to_list:
        return False
    if query.through_lists and any(query.through_lists):
            return False
    return True
