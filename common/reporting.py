def make_header(s: str, width: int = 80, pad: bool = True, fillchar = "="):
    if pad:
        s = f" {s} "
    return s.center(width, fillchar)
