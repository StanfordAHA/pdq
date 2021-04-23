from designs.one_bit_alu import OneBitAlu
from designs.simple_alu import SimpleAlu
from magma_examples.magma_examples.shift_register import ShiftRegister
from pdq.common.algorithms import only
from pdq.circuit_tools.circuit_utils import find_instances_by_name
from pdq.circuit_tools.partial_extract import partial_extract
from pdq.circuit_tools.signal_path import TopSignalPath, InternalSignalPath


def test_basic():
    xor = only(find_instances_by_name(OneBitAlu, "xor"))
    mux = only(find_instances_by_name(OneBitAlu, "Mux"))
    path = TopSignalPath(
        src=OneBitAlu.a,
        dst=OneBitAlu.out,
        path=[
            InternalSignalPath(
                src=xor.I0,
                dst=xor.O),
            InternalSignalPath(
                src=mux.I2,
                dst=mux.O)
        ]
    )

    Partial = partial_extract(OneBitAlu, path)

    # Check that there are only 2 instances.
    assert len(Partial.instances) == 2
    new_xor = only(find_instances_by_name(Partial, "xor"))
    new_mux = only(find_instances_by_name(Partial, "Mux"))
    assert new_xor.name == xor.name
    assert type(new_xor) is type(xor)
    assert new_mux.name == mux.name
    assert type(new_mux) is type(mux)

    # Check the connections along the desired timing path.
    assert new_xor.I0.trace() is Partial.partial_src_pin__
    assert new_mux.I2.trace() is new_xor.O
    assert Partial.partial_dst_pin__.trace() is new_mux.O


def test_bits_select():
    add = only(find_instances_by_name(SimpleAlu, "add"))
    mux = only(find_instances_by_name(SimpleAlu, "Mux"))

    path = TopSignalPath(
        src=SimpleAlu.a[0],
        dst=SimpleAlu.out[0],
        path=[
            InternalSignalPath(
                src=add.I0[0],
                dst=add.O[0]),
            InternalSignalPath(
                src=mux.I0[0],
                dst=mux.O[0])
        ]
    )

    Partial = partial_extract(SimpleAlu, path)

    # Check that there are only 2 instances.
    assert len(Partial.instances) == 2
    new_add = only(find_instances_by_name(Partial, "add"))
    new_mux = only(find_instances_by_name(Partial, "Mux"))
    assert new_add.name == add.name
    assert type(new_add) is type(add)
    assert new_mux.name == mux.name
    assert type(new_mux) is type(mux)

    # Check the connections along the desired timing path.
    assert new_add.I0[0].trace() is Partial.partial_src_pin__
    assert new_mux.I0[0].trace() is new_add.O[0]
    assert Partial.partial_dst_pin__.trace() is new_mux.O[0]


def test_hierarchical():
    regs = find_instances_by_name(ShiftRegister, "Register_inst")
    regs = list(sorted(regs, key=lambda r: r.name))

    def _get_sub_reg(reg):
        return only(find_instances_by_name(type(reg), "reg_"))

    path = TopSignalPath(
        src=ShiftRegister.I,
        dst=ShiftRegister.O,
        path = [
            InternalSignalPath(
                src=regs[0].I,
                dst=regs[0].O),
            InternalSignalPath(
                src=regs[1].I,
                dst=regs[1].O,
                path=[
                    InternalSignalPath(
                        src=_get_sub_reg(regs[1]).I[0],
                        dst=_get_sub_reg(regs[1]).O[0])
                ]
            ),
            InternalSignalPath(
                src=regs[2].I,
                dst=regs[2].O),
            InternalSignalPath(
                src=regs[3].I,
                dst=regs[3].O,
                path=[
                    InternalSignalPath(
                        src=_get_sub_reg(regs[3]).I[0],
                        dst=_get_sub_reg(regs[3]).O[0])
                ]
            ),
        ]
    )

    Partial = partial_extract(ShiftRegister, path)

    # Check the instances.
    assert len(Partial.instances) == 4
    expected_insts = {
        "Register_inst0": type(regs[0]),
        "Register_inst1__reg_P1_inst0": type(_get_sub_reg(regs[1])),
        "Register_inst2": type(regs[2]),
        "Register_inst3__reg_P1_inst0": type(_get_sub_reg(regs[3]))
    }
    new_insts = {name: only(find_instances_by_name(Partial, name))
                 for name in expected_insts}
    for name, T in expected_insts.items():
        assert new_insts[name].name == name
        assert type(new_insts[name]) is T

    # Check the connections along the extracted path.
    insts = list(new_insts.values())
    assert insts[0].I.trace() is Partial.partial_src_pin__
    assert insts[1].I[0].trace() is insts[0].O
    assert insts[2].I.trace() is insts[1].O[0]
    assert insts[3].I[0].trace() is insts[2].O
    assert Partial.partial_dst_pin__.trace() is insts[3].O[0]
