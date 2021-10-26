import magma as m

from pdq.circuit_tools.graph_view_utils import make_scoped_bit


def test_make_scoped_bit():

    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit))
        x = ~io.I
        io.O @= x

    class Top(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit))
        io.O @= Foo(name="foo")(io.I)

    def do(d, s):
        sb = make_scoped_bit(d, s)
        assert sb.scope.validate()
        print (str(sb.scope), repr(sb.value), str(sb))

    do(Top, "Top.I")
    do(Top, "Top.O")
    do(Top, "Top.foo.I")
    do(Top, "Top.foo.x")
