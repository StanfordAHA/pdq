import magma as m


def VerilogWrapper(filename: str) -> m.DefineCircuitKind:
    return m.define_from_verilog_file(filename)[0]
