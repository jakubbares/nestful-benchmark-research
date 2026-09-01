"""Call-graph -> NESTFUL sample.

The primary artifact of this generator is a *graph*, not a sentence.

A task is a directed acyclic graph whose nodes are tool invocations and whose
edges carry a value from the output of one call into a named parameter of a
later call.  Literal (user-supplied) arguments are the graph's leaves.

    literal --.
               >-- [multiply] --.
    literal --'                  >-- [subtract] -- ANSWER
               [rectangle_area]-'

From that graph everything else is derived, in this order:

    1. validate      - acyclic, every parameter bound, single sink
    2. topo-sort     - deterministic linear order  ->  the NESTFUL `output` list
    3. label         - $var_1 ... assigned in topological order
    4. execute       - run the real Python implementations  ->  `gold_answer`
    5. verbalise     - render the graph back into English  ->  the `input` query
    6. distract      - pad the tool catalogue with unused tools

Only step 5 needs a human/LLM in the loop; steps 1-4 and 6 are mechanical, and
because step 4 really executes, the gold answer is observed rather than
asserted.
"""

import json
from collections import defaultdict

from tools_library import TOOLS


class Ref:
    """An edge in the call graph: the output of ``node_id`` flows into a parameter."""

    __slots__ = ("node_id",)

    def __init__(self, node_id):
        self.node_id = node_id

    def __repr__(self):
        return "Ref({!r})".format(self.node_id)


class CallGraph:
    def __init__(self, graph_id, family, motif, n_catalogue_tools=12):
        self.graph_id = graph_id
        self.family = family            # "math" | "code" | "mixed"
        self.motif = motif              # human-readable topology description
        self.n_catalogue_tools = n_catalogue_tools
        self.nodes = {}                 # node_id -> {"tool":..., "args":{...}}
        self._order = []                # insertion order, tie-breaker for topo sort

    # -- construction ------------------------------------------------------
    def add(self, node_id, tool, **args):
        if node_id in self.nodes:
            raise ValueError("duplicate node id {!r}".format(node_id))
        if tool not in TOOLS:
            raise ValueError("unknown tool {!r}".format(tool))
        spec_params = set(TOOLS[tool]["spec"]["parameters"])
        if set(args) != spec_params:
            raise ValueError(
                "{}.{}: arguments {} do not match parameters {}".format(
                    self.graph_id, node_id, sorted(args), sorted(spec_params)))
        self.nodes[node_id] = {"tool": tool, "args": args}
        self._order.append(node_id)
        return Ref(node_id)

    # -- graph structure ---------------------------------------------------
    def edges(self):
        """[(src_node, dst_node, dst_param)] - the value-flow edges."""
        out = []
        for dst, node in self.nodes.items():
            for param, val in node["args"].items():
                if isinstance(val, Ref):
                    out.append((val.node_id, dst, param))
        return out

    def _preds(self):
        preds = {n: set() for n in self.nodes}
        for src, dst, _ in self.edges():
            preds[dst].add(src)
        return preds

    def topo_order(self):
        """Deterministic topological order: Kahn's algorithm, insertion-order tie-break."""
        preds = self._preds()
        succs = defaultdict(set)
        for src, dst, _ in self.edges():
            succs[src].add(dst)
        remaining = dict((n, set(p)) for n, p in preds.items())
        order = []
        while remaining:
            ready = [n for n in self._order if n in remaining and not remaining[n]]
            if not ready:
                raise ValueError("{}: call graph has a cycle".format(self.graph_id))
            pick = ready[0]
            order.append(pick)
            del remaining[pick]
            for s in succs[pick]:
                remaining.get(s, set()).discard(pick)
        return order

    def sinks(self):
        used = {src for src, _, _ in self.edges()}
        return [n for n in self._order if n not in used]

    def stats(self):
        order = self.topo_order()
        preds = self._preds()
        depth = {}
        for n in order:
            depth[n] = 1 + max([depth[p] for p in preds[n]], default=0)
        succ_count = defaultdict(int)
        for src, _, _ in self.edges():
            succ_count[src] += 1
        levels = defaultdict(int)
        for n, d in depth.items():
            levels[d] += 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges()),
            "depth": max(depth.values()),
            "width": max(levels.values()),
            "fan_out_nodes": sorted(n for n, c in succ_count.items() if c > 1),
            "fan_in_nodes": sorted(n for n in self.nodes if len(preds[n]) > 1),
            "roots": sorted(n for n in self.nodes if not preds[n]),
            "sinks": self.sinks(),
        }

    # -- validation --------------------------------------------------------
    def validate(self):
        self.topo_order()                      # raises on a cycle
        sinks = self.sinks()
        if len(sinks) != 1:
            raise ValueError("{}: expected exactly one sink, got {}".format(self.graph_id, sinks))
        for dst, node in self.nodes.items():
            for param, val in node["args"].items():
                if isinstance(val, Ref) and val.node_id not in self.nodes:
                    raise ValueError("{}.{}: dangling edge to {!r}".format(
                        self.graph_id, dst, val.node_id))
        return True

    # -- labelling & linearisation ----------------------------------------
    def _label_style(self):
        # math half of NESTFUL writes $var_1, the coding half writes $var1
        return "$var_{}" if self.family == "math" else "$var{}"

    def labels(self):
        style = self._label_style()
        return {n: style.format(i + 1) for i, n in enumerate(self.topo_order())}

    def to_sequence(self):
        """The NESTFUL `output` list - the graph flattened into a call sequence."""
        labels = self.labels()
        seq = []
        for n in self.topo_order():
            node = self.nodes[n]
            args = {}
            for param, val in node["args"].items():
                if isinstance(val, Ref):
                    src_tool = self.nodes[val.node_id]["tool"]
                    args[param] = "{}.{}$".format(labels[val.node_id],
                                                  TOOLS[src_tool]["out_key"])
                else:
                    args[param] = val
            if self.family == "math":
                seq.append({"name": node["tool"], "label": labels[n], "arguments": args})
            else:
                seq.append({"name": node["tool"], "arguments": args, "label": labels[n]})
        return seq

    # -- execution ---------------------------------------------------------
    def execute(self):
        """Run the graph for real. Returns (gold_answer, {node_id: value})."""
        values = {}
        for n in self.topo_order():
            node = self.nodes[n]
            kwargs = {}
            for param, val in node["args"].items():
                kwargs[param] = values[val.node_id] if isinstance(val, Ref) else val
            values[n] = TOOLS[node["tool"]]["impl"](**kwargs)
        return values[self.sinks()[0]], values

    # -- rendering ---------------------------------------------------------
    def to_mermaid(self):
        labels = self.labels()
        lines = ["graph LR"]
        for n in self.topo_order():
            lines.append('  {}["{} {}"]'.format(n, labels[n], self.nodes[n]["tool"]))
        for src, dst, param in self.edges():
            lines.append("  {} -->|{}| {}".format(src, param, dst))
        return "\n".join(lines)

    def to_edge_list(self):
        labels = self.labels()
        return ["{} ({}) --{}--> {} ({})".format(
            labels[s], self.nodes[s]["tool"], p, labels[d], self.nodes[d]["tool"])
            for s, d, p in self.edges()]

    def literal_query(self):
        """Mechanical verbalisation of the graph, straight from the phrase templates."""
        labels = self.labels()
        ordinal = {n: i + 1 for i, n in enumerate(self.topo_order())}
        clauses = []
        for n in self.topo_order():
            node = self.nodes[n]
            filled = {}
            for param, val in node["args"].items():
                if isinstance(val, Ref):
                    filled[param] = "the result of step {}".format(ordinal[val.node_id])
                else:
                    filled[param] = json.dumps(val) if not isinstance(val, str) else repr(val)
            clauses.append(TOOLS[node["tool"]]["phrase"].format(**filled))
        head = clauses[0][0].upper() + clauses[0][1:]
        return ". ".join([head] + ["Then " + c for c in clauses[1:]]) + "."
