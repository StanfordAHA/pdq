import magma as m


class RegisteredIncrementer(m.Generator2):
    def __init__(self, width: int):
        self.name = f"RegisteredIncrementer{width}"
        T = m.UInt[width]
        self.io = m.IO(I0=m.In(T), I1=m.In(T), O=m.Out(T)) + m.ClockIO()
        sum_ = m.register(self.io.I0) + self.io.I1
        self.io.O @= sum_
        

if __name__ == "__main__":
    ckt = RegisteredIncrementer(32)
    m.compile("design", ckt)
