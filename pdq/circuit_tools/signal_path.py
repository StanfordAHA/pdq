import dataclasses
from typing import List, Tuple

import magma as m


@dataclasses.dataclass(frozen=True)
class SignalPath:
    src: m.Bit
    dst: m.Bit
    path: List[Tuple[m.Bit, m.Bit]]
