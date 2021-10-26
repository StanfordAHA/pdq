import magma as m
import networkx as nx


class Circ(m.Circuit):
    T = m.Bits[4]
    io = m.IO(I=m.In(T), O=m.Out(T))
    x = io.I
    x = m.concat(x[:2], m.sint(x[2:]) + m.sint(x[:2]))
    x = m.register(m.register(x))
    io.O @= x


class Circ(m.Circuit):
    io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bits[2]))
    io.O[0] @= io.I
    io.O[1] @= 0


from pdq.circuit_tools.graph_view_utils import materialize_graph


v, e = materialize_graph(Circ)
g = nx.DiGraph()
g.add_nodes_from(v)
g.add_edges_from(e)
nx.drawing.nx_pydot.write_dot(g, "graph.txt")
