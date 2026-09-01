"""Assemble the synthetic NESTFUL-style dataset from the call graphs.

    python build_dataset.py

Emits, next to this file:
    data/synthetic_nestful_v1.parquet   NESTFUL schema, drop-in for the scorer
    data/synthetic_nestful_v1.jsonl     same rows + graph metadata + trace
    GRAPHS.md                           per-task mermaid diagram, trace, sequence
"""

import json
import os
import re
import random
import uuid

from graph_builder import Ref
from graphs import GRAPHS
from queries import LITERAL_ALIASES, QUERIES
from tools_library import TOOLS

HERE = os.path.dirname(os.path.abspath(__file__))
# fixed namespace -> stable sample_ids across regenerations
NS = uuid.UUID("6f3c1d54-9a0e-4f7b-9a2c-0d1e2f3a4b5c")


# ---------------------------------------------------------------- catalogue
def build_catalogue(graph, seed):
    """Used tools + plausible distractors, shuffled, as NESTFUL shows them."""
    used = sorted({n["tool"] for n in graph.nodes.values()})
    if graph.family == "mixed":
        pool = [t for t in TOOLS]
    else:
        pool = [t for t, v in TOOLS.items() if v["family"] == graph.family]
    distractors = sorted(set(pool) - set(used))
    rng = random.Random(seed)
    rng.shuffle(distractors)
    n_extra = max(0, graph.n_catalogue_tools - len(used))
    names = used + distractors[:n_extra]
    rng.shuffle(names)
    return [TOOLS[n]["spec"] for n in names], names


# ------------------------------------------------- independent re-execution
def reexecute(sequence):
    """Execute the *serialised* call list, resolving $label.field$ references.

    Deliberately does not touch the CallGraph objects, so a serialisation bug
    cannot hide behind the in-memory graph.
    """
    env = {}

    def resolve(v):
        if isinstance(v, str) and v.startswith("$") and v.endswith("$"):
            label, field = v[:-1].rsplit(".", 1)
            return env[label][field]
        if isinstance(v, list):
            return [resolve(x) for x in v]
        if isinstance(v, dict):
            return {k: resolve(x) for k, x in v.items()}
        return v

    last = None
    for call in sequence:
        tool = TOOLS[call["name"]]
        kwargs = {k: resolve(v) for k, v in call["arguments"].items()}
        last = tool["impl"](**kwargs)
        env[call["label"]] = {tool["out_key"]: last}
    return last


# ------------------------------------------------------------------- checks
def check(graph, sequence, catalogue_names, query, gold, values):
    gid = graph.graph_id
    assert query, "{}: no query authored".format(gid)
    # every referenced label is defined by an earlier call
    seen = set()
    for call in sequence:
        for v in call["arguments"].values():
            if isinstance(v, str) and v.startswith("$") and v.endswith("$"):
                label = v[:-1].rsplit(".", 1)[0]
                assert label in seen, "{}: forward reference {}".format(gid, v)
        seen.add(call["label"])
    # the catalogue really offers every tool the answer needs
    for call in sequence:
        assert call["name"] in catalogue_names, "{}: {} missing from catalogue".format(
            gid, call["name"])
    # and it offers distractors too, or the task is trivial
    assert len(catalogue_names) > len({c["name"] for c in sequence}), \
        "{}: catalogue has no distractors".format(gid)
    # every literal leaf of the graph is mentioned in the query, either verbatim
    # (numbers matched on word boundaries, so 0 is not satisfied by "40") or via
    # a declared surface form such as "three eighths" for 3 and 8
    q = query.lower()
    aliases = LITERAL_ALIASES.get(gid, {})
    for node in graph.nodes.values():
        for param, val in node["args"].items():
            if isinstance(val, Ref) or isinstance(val, bool) or isinstance(val, dict):
                continue  # edges carry no literal; booleans and dicts are prose-reformatted
            hashable = not isinstance(val, (list, dict, set))
            if hashable and any(a.lower() in q for a in aliases.get(val, [])):
                continue
            if isinstance(val, (int, float)):
                forms = {str(val)}
                if isinstance(val, float) and val == int(val):
                    forms.add(str(int(val)))
                # "2.0" must still match at a sentence end, but 0 must not
                # match inside 40, nor 100 inside 1000, nor 2 inside 2.0
                pat = r"(?<![\w.]){}(?!\d)(?!\.\d)(?!\w)"
                if not any(re.search(pat.format(re.escape(f)), q) for f in forms):
                    raise AssertionError("{}: literal {!r} ({}) absent from query".format(
                        gid, val, param))
            elif str(val).lower() not in q:
                raise AssertionError("{}: literal {!r} ({}) absent from query".format(
                    gid, val, param))
    # no intermediate value is stated in the query - the model has to compute
    # every one of them, so the query cannot short-circuit the graph
    sink = graph.sinks()[0]
    for node_id, val in values.items():
        if node_id == sink or isinstance(val, bool):
            continue
        if isinstance(val, (int, float)):
            forms = {str(val)}
            if isinstance(val, float) and val == int(val):
                forms.add(str(int(val)))
            hit = any(re.search(r"(?<![\w.]){}(?!\d)(?!\.\d)(?!\w)".format(re.escape(f)), q)
                      for f in forms)
        else:
            hit = str(val).lower() in q
        if hit:
            raise AssertionError("{}: query leaks intermediate {} = {!r}".format(
                gid, node_id, val))

    # gold answer survives a JSON round trip and re-execution
    assert reexecute(json.loads(json.dumps(sequence))) == gold, \
        "{}: re-execution disagrees with gold".format(gid)


# -------------------------------------------------------------------- build
def main():
    rows, meta_rows, doc = [], [], []
    for i, g in enumerate(GRAPHS):
        g.validate()
        gold, values = g.execute()
        sequence = g.to_sequence()
        catalogue, names = build_catalogue(g, seed=1000 + i)
        query = QUERIES.get(g.graph_id)
        check(g, sequence, names, query, gold, values)

        sample_id = str(uuid.uuid5(NS, g.graph_id))
        rows.append({
            "sample_id": sample_id,
            "input": query,
            "output": json.dumps(sequence),
            "tools": json.dumps(catalogue),
            "gold_answer": repr(gold),
        })
        labels = g.labels()
        meta_rows.append(dict(rows[-1], **{
            "graph_id": g.graph_id,
            "family": g.family,
            "motif": g.motif,
            "graph_stats": g.stats(),
            "graph_edges": g.to_edge_list(),
            "mermaid": g.to_mermaid(),
            "literal_query": g.literal_query(),
            "trace": {labels[n]: repr(values[n]) for n in g.topo_order()},
            "n_catalogue_tools": len(catalogue),
        }))

        s = g.stats()
        doc.append(
            "## {} - {}\n\n"
            "`{}` | family **{}** | {} nodes, {} edges, depth {}, width {} | "
            "catalogue {} tools ({} distractors)\n\n"
            "**Call graph**\n\n```mermaid\n{}\n```\n\n"
            "**Query (authored from the executed graph)**\n\n> {}\n\n"
            "**Executed trace**\n\n```\n{}\n```\n\n"
            "**Gold answer** — `{}`\n".format(
                g.graph_id, g.motif, sample_id, g.family, s["nodes"], s["edges"],
                s["depth"], s["width"], len(catalogue),
                len(catalogue) - len({c["name"] for c in sequence}),
                g.to_mermaid(), query,
                "\n".join("{:7} {:24} = {}".format(labels[n], g.nodes[n]["tool"],
                                                   repr(values[n]))
                          for n in g.topo_order()),
                repr(gold)))

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    jsonl = os.path.join(HERE, "data", "synthetic_nestful_v1.jsonl")
    with open(jsonl, "w") as f:
        for r in meta_rows:
            f.write(json.dumps(r) + "\n")

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.Table.from_pylist(
            rows, schema=pa.schema([(k, pa.string()) for k in
                                    ["sample_id", "input", "output", "tools", "gold_answer"]]))
        pq.write_table(table, os.path.join(HERE, "data", "synthetic_nestful_v1.parquet"))
        parquet_note = "data/synthetic_nestful_v1.parquet"
    except ImportError:
        parquet_note = "(pyarrow not installed - parquet skipped)"

    with open(os.path.join(HERE, "GRAPHS.md"), "w") as f:
        f.write("# Synthetic NESTFUL-style tasks - call graphs\n\n"
                "Generated by `build_dataset.py`. Each task was produced graph-first: the "
                "DAG below was written and executed, and only then was the query written to "
                "fit it.\n\n" + "\n".join(doc))

    print("{} tasks -> {}, {}, GRAPHS.md".format(len(rows), parquet_note,
                                                 "data/synthetic_nestful_v1.jsonl"))
    for m in meta_rows:
        s = m["graph_stats"]
        print("  {:8} {:6} n={} e={} depth={} width={} tools={} gold={}".format(
            m["graph_id"], m["family"], s["nodes"], s["edges"], s["depth"], s["width"],
            m["n_catalogue_tools"], m["gold_answer"][:34]))


if __name__ == "__main__":
    main()
