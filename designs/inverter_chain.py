import magma as m


class InverterChain(m.Generator2):
    def __init__(self, length: int, fanout: int = 0):
        self.io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit))
        self.io += m.IO(**{f"fanout_{i}": m.Out(m.Bit)
                           for i in range(length * fanout)})

        index = 0
        curr = self.io.I
        for _ in range(length):
            curr = ~curr
            for _ in range(fanout):
                out = getattr(self.io, f"fanout_{index}")
                out @= curr
                index += 1
        self.io.O @= curr
