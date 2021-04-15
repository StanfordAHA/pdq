import magma as m


class SimpleAlu(m.Circuit):
    io = m.IO(
        a=m.In(m.UInt[4]),
        b=m.In(m.UInt[4]),
        opcode=m.In(m.UInt[2]),
        out=m.Out(m.UInt[4]))

    io.out @= m.mux([io.a + io.b, io.a - io.b, io.a, io.b], io.opcode)
