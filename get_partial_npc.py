import pdq
import magma as m
import subprocess

from pdq.circuit_tools.circuit_utils import find_instances_name_equals
from pdq.circuit_tools.graph_view import BitPortNode
from pdq.circuit_tools.partial_extract import extract_from_terminals
from pdq.circuit_tools.signal_path import Scope, ScopedBit

from magma_riscv_mini.riscv_mini.data_path import Datapath

import networkx as nx
from pdq.circuit_tools.graph_view_utils import materialize_graph

dp = Datapath(32)
bits = list(m.as_bits(dp.npc))
terms = [BitPortNode(ScopedBit(b, Scope(dp))) for b in bits]

new_terms = []
for term in terms:
    from pdq.circuit_tools.partial_extract import get_forward_terminals
    terms = get_forward_terminals(dp, term)
    print (term)
    for tt in terms:
        print (f"    {str(tt)}")
        new_terms.append(tt)
terms = new_terms

partial = extract_from_terminals(dp, terms) #, num_neighbors=0)

# V, E = materialize_graph(partial)
# G = nx.DiGraph()
# G.add_nodes_from(V)
# G.add_edges_from(E)
# nx.drawing.nx_pydot.write_dot(G, f"{partial.name}.txt")
# subprocess.run(f"dot {partial.name}.txt -Tpdf > {partial.name}.pdf",
#   shell=True, check=True)


m.compile("Partial", partial, inline=True)
