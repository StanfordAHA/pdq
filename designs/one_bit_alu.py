import magma as m


class OneBitAlu(m.Circuit):
    io = m.IO(
        a=m.In(m.Bit),
        b=m.In(m.Bit),
        opcode=m.In(m.Bits[2]),
        out=m.Out(m.Bit))

    values = [
        io.a | io.b,
        io.a & io.b,
        io.a ^ io.b,
        ~(io.a & io.b),
    ]

    io.out @= m.mux(values, io.opcode)
