import magma as m


class SimpleMultipler(m.Generator2):
    def __init__(self, width: int):
        self.name = f"SimpleMultipler{width}"
        T = m.UInt[width]
        self.io = m.IO(I0=m.In(T), I1=m.In(T), O=m.Out(T))
        self.io.O @= self.io.I0 * self.io.I1
