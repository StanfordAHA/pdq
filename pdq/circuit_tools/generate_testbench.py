import fault
import magma as m


def _make_random(T):
    if issubclass(T, m.Digital):
        return fault.random_bit()
    if issubclass(T, m.Bits):
        return fault.random_bv(T.N)
    if issubclass(T, m.Array):
        return [_make_random(T.T) for _ in range(T.N)]
    if issubclass(T, m.Tuple):
        return {k: _make_random(T) for k, T in T.field_dict.items()}
    raise NotImplementedError()


def _update_clock(ckt, kwargs):
    if "clock" in kwargs:
        return True
    clk = m.passes.clock.get_all_output_clocks_in_defn(ckt)[m.Clock]
    if clk is None:
        return False
    kwargs["clock"] = clk
    return True


def generate_uniform_random_stimulus(ckt, num_cycles=1, **kwargs):
    clocked = _update_clock(ckt, kwargs)
    tester = fault.Tester(ckt, **kwargs)
    step_fn = lambda: tester.step(2) if clocked else tester.eval
    for _ in range(num_cycles):
        # TODO(rsetaluri): Handle mixed type ports.
        for port in ckt.interface.ports.values():
            if not port.is_output() or port.is_clock():
                continue
            tester.poke(port, _make_random(type(port)))
        step_fn()
    return tester


def generate_testbench(ckt, directory):
    tester = generate_uniform_random_stimulus(ckt)
    tester.compile_and_run(
        "system-verilog",
        directory=directory,
        simulator="vcs",
        dump_waveforms=True,
        waveform_type="vcd",
        skip_run=True,
        skip_compile=True)
