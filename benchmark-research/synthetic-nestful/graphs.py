"""The ten call graphs.

These are written *first*, before any task text exists.  Each one is a DAG over
the tool library; the English query in ``queries.py`` was written afterwards by
reading the executed graph, never the other way round.

Topologies deliberately vary: pure chains, diamonds, fan-out stars, convergent
trees, an edge that lands on a scalar index parameter, and one graph whose
edges cross the math/code family boundary (so the reference suffix changes
mid-sequence: ``$var2.output_0$`` feeding a tool that emits ``$var4.result$``).
"""

from graph_builder import CallGraph

GRAPHS = []


def _g(*a, **kw):
    g = CallGraph(*a, **kw)
    GRAPHS.append(g)
    return g


# 01 - pure chain, depth 3 --------------------------------------------------
g = _g("syn-001", "math", "chain (depth 3, width 1)", n_catalogue_tools=10)
a = g.add("n1", "divide", arg_0=3, arg_1=8)
b = g.add("n2", "multiply", arg_0=a, arg_1=640)
g.add("n3", "subtract", arg_0=640, arg_1=b)

# 02 - diamond: one node fans out to two consumers that re-converge ---------
g = _g("syn-002", "math", "diamond (fan-out at n1, fan-in at n4)", n_catalogue_tools=11)
a = g.add("n1", "rectangle_area", arg_0=14, arg_1=9)
b = g.add("n2", "square_area", arg_0=6)
c = g.add("n3", "subtract", arg_0=a, arg_1=b)
g.add("n4", "divide", arg_0=c, arg_1=a)

# 03 - fan-out star: one root feeds three separate consumers ----------------
g = _g("syn-003", "math", "fan-out star (n1 feeds 3 consumers) + chain", n_catalogue_tools=12)
s = g.add("n1", "speed", arg_0=240, arg_1=3)
m = g.add("n2", "multiply", arg_0=s, arg_1=1.25)
d = g.add("n3", "subtract", arg_0=m, arg_1=s)
f = g.add("n4", "divide", arg_0=d, arg_1=s)
g.add("n5", "multiply", arg_0=f, arg_1=100)

# 04 - convergent tree: three independent roots merge (width 3) -------------
g = _g("syn-004", "math", "convergent tree (3 roots, width 3, depth 4)", n_catalogue_tools=13)
r1 = g.add("n1", "rectangle_area", arg_0=12, arg_1=5)
r2 = g.add("n2", "triangle_area", arg_0=10, arg_1=6)
r3 = g.add("n3", "circle_area", arg_0=2.0)
s1 = g.add("n4", "add", arg_0=r1, arg_1=r2)
s2 = g.add("n5", "add", arg_0=s1, arg_1=r3)
g.add("n6", "floor", arg_0=s2)

# 05 - deep chain, depth 6 --------------------------------------------------
g = _g("syn-005", "math", "deep chain (depth 6, width 1)", n_catalogue_tools=12)
v1 = g.add("n1", "multiply", arg_0=2500, arg_1=1.08)
v2 = g.add("n2", "multiply", arg_0=v1, arg_1=1.08)
v3 = g.add("n3", "multiply", arg_0=v2, arg_1=1.08)
v4 = g.add("n4", "subtract", arg_0=v3, arg_1=2500)
v5 = g.add("n5", "divide", arg_0=v4, arg_1=2500)
g.add("n6", "multiply", arg_0=v5, arg_1=100)

# 06 - chain over collections, depth 4 --------------------------------------
g = _g("syn-006", "code", "chain (depth 4) with type changes string->array->array", n_catalogue_tools=14)
p = g.add("n1", "parse_list_of_numbers", text="18, 7, 42, 7, 23, 42, 5")
d = g.add("n2", "dedupe_preserve_order", values=p)
s = g.add("n3", "sort_values", values=d, descending=True)
g.add("n4", "take_first_n", values=s, n=3)

# 07 - diamond where both incoming edges of the sink trace back to one root --
g = _g("syn-007", "code", "diamond (n1 reaches n3 by two disjoint paths)", n_catalogue_tools=15)
vals = g.add("n1", "get_dict_values",
             dictionary={"mon": 62, "tue": 48, "wed": 71, "thu": 39})
rev = g.add("n2", "reverse_list", values=vals)
z = g.add("n3", "zip_sum", list1=vals, list2=rev)
t = g.add("n4", "sort_values", values=z, descending=True)
g.add("n5", "take_first_n", values=t, n=2)

# 08 - diamond on strings: n3 feeds both the slug and the anchor text --------
g = _g("syn-008", "code", "diamond on strings (n3 fans out to n4 and n5)", n_catalogue_tools=14)
tok = g.add("n1", "tokenize_sentence",
            sentence="Nested API Calls, Nested API Planning!")
dd = g.add("n2", "dedupe_preserve_order", values=tok)
j = g.add("n3", "join_with_separator", items=dd, separator=" ")
slug = g.add("n4", "convert_to_url_slug", text=j)
g.add("n5", "format_html_link", text=j, url=slug)

# 09 - an edge that lands on a scalar index parameter ------------------------
g = _g("syn-009", "code", "fan-out where a computed index becomes an argument", n_catalogue_tools=15)
common = g.add("n1", "unique_common_values",
               list1=[3, 9, 14, 22, 7, 31], list2=[22, 5, 9, 40, 31])
srt = g.add("n2", "sort_values", values=common, descending=True)
idx = g.add("n3", "index_of", values=srt, target=22)
sw = g.add("n4", "swap_by_index", values=srt, i=0, j=idx)
g.add("n5", "join_with_separator", items=sw, separator="|")

# 10 - mixed families: edges cross code -> math -> code ----------------------
g = _g("syn-010", "mixed", "fan-out + fan-in crossing the code/math tool families",
       n_catalogue_tools=16)
p = g.add("n1", "parse_list_of_numbers", text="12, 19, 7, 24, 15, 9")
s = g.add("n2", "sum_list", values=p)
n = g.add("n3", "list_length", values=p)
m = g.add("n4", "divide", arg_0=s, arg_1=n)
sq = g.add("n5", "power", arg_0=m, arg_1=2)
g.add("n6", "round_to", value=sq, ndigits=2)
