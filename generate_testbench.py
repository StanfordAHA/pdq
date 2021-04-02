import fault
import magma as m


def _make_random(T):
    if issubclass(T, m.Digital):
        return fault.random_bit()
    if issubclass(T, m.Bits):
        return fault.random_bv(T.N)
    if issubclass(T, m.Array):
        return [_make_random(T.T) for _ in range(T.N)]
    raise NotImplementedError()


def generate_uniform_random_stimulus(ckt, num_cycles=1, **kwargs):
    tester = fault.Tester(ckt, **kwargs)
    for _ in range(num_cycles):
        # TODO(rsetaluri): Handle mixed type ports.
        for port in ckt.interface.ports.values():
            if not port.is_output() or port.is_clock():
                continue
            tester.poke(port, _make_random(type(port)))
        tester.step(2)
    return tester


def generate_testbench(ckt):
    tester = generate_uniform_random_stimulus(ckt)
    tester.compile_and_run(
        "system-verilog",
        simulator="vcs",
        dump_waveforms=True,
        waveform_type="vcd")
