from typing import List


def only(l: List):
    if len(l) != 1:
        raise ValueError("list should have only one element")
    return l[0]
