"""Print each graph, its linearised sequence and its executed trace."""
import json
from graphs import GRAPHS
from graph_builder import CallGraph

for g in GRAPHS:
    g.validate()
    gold, values = g.execute()
    labels = g.labels()
    print("=" * 78)
    print(g.graph_id, "|", g.family, "|", g.motif)
    print("stats:", g.stats())
    print("edges:")
    for e in g.to_edge_list():
        print("   ", e)
    print("trace:")
    for n in g.topo_order():
        print("   {:6} {:24} = {}".format(labels[n], g.nodes[n]["tool"], repr(values[n])[:90]))
    print("GOLD:", repr(gold))
    print("literal query:", g.literal_query())
