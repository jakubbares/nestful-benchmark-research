# Synthetic NESTFUL-Style Tasks — Graph-First Generation

Ten nested function-calling tasks generated the opposite way round from how a
benchmark is usually written. Instead of taking a question and asking a model to
decompose it, each task starts as a **directed acyclic graph of tool calls** —
nodes are invocations, edges carry the output of one call into a named parameter
of a later one — and the natural-language query is written afterwards, to fit the
graph that already exists.

Output is schema-identical to
[`benchmark-research/datasets/nestful`](../datasets/nestful) (IBM NESTFUL,
[arXiv:2409.03797](https://arxiv.org/abs/2409.03797v3)), so the same scorer runs
over both without modification.

## Why Graph-First

Writing the question first and mining the answer out of it inherits whatever
reasoning shape the question already suggests, and the "gold" sequence is only as
correct as the annotator. Starting from the graph inverts both problems:

- **Topology is a design parameter, not an accident.** Depth, width, fan-out,
  fan-in and cross-family edges are chosen before any prose exists, so coverage of
  hard structures is deliberate rather than whatever the source corpus happened to
  contain. NESTFUL's own math half is 88% chains over `add`/`subtract`/
  `multiply`/`divide`; a generator that samples graphs is not stuck there.
- **The gold answer is observed, not asserted.** Every tool is a real Python
  function, so the graph is *executed* and the answer is whatever came out. There
  is no annotator to disagree with.
- **Difficulty is dialable.** Node count, depth, catalogue size, distractor ratio,
  and whether edges cross the two tool families are independent knobs.

The cost is that step 5 — turning an executed graph into a query somebody would
plausibly ask — still needs judgement. That step is isolated in `queries.py` and
guarded by automated checks (below), so it is the only place a human or an LLM
enters the loop.

## Pipeline

```
graphs.py          1. write the DAG            nodes = tool calls, edges = value flow
graph_builder.py   2. validate                 acyclic, every parameter bound, single sink
                   3. topologically sort       -> the linear NESTFUL `output` sequence
                   4. execute                  real Python impls -> `gold_answer`
queries.py         5. verbalise                the only human/LLM step
build_dataset.py   6. build the catalogue      used tools + seeded distractors, shuffled
                   7. check + emit             parquet / jsonl / GRAPHS.md
```

Labels are assigned in topological order (`$var_1` for the math family, `$var1`
for the coding family, matching NESTFUL), and a reference's suffix is taken from
the *producing* tool's `output_parameters` — `$var_1.result$` for a math tool,
`$var1.output_0$` for a coding tool.

## What Is Checked Before A Task Ships

`build_dataset.py` refuses to emit a task that fails any of these:

| Check | Catches |
|---|---|
| Graph is acyclic with exactly one sink | ill-formed task with no single answer |
| Every parameter in the tool spec is bound | under-specified calls |
| No forward references in the linearised sequence | bad topological order |
| Every called tool is present in the offered catalogue | unanswerable task |
| Catalogue strictly larger than the set of called tools | task with no distractors |
| Every literal leaf of the graph appears in the query | query that under-determines the answer |
| No intermediate value appears in the query | query that leaks the computation |
| Serialised sequence re-executes to the same gold answer | serialisation bug |

The literal-coverage check matches numbers on word boundaries (so `0` is not
satisfied by `40`, nor `2` by `2.0`), and where a query legitimately states a
literal in words — "three eighths" for `3` and `8`, "pipe-separated" for `"|"` —
that surface form has to be declared explicitly in `LITERAL_ALIASES`. Every
escape hatch is visible in one table rather than hidden in a fuzzy matcher.

The re-execution check is the important one: it walks the *serialised* JSON,
resolves `$label.field$` references itself, and never touches the in-memory graph,
so a bug in linearisation or reference formatting cannot pass silently.

`test_guards.py` injects one fault per guard and asserts each one fires, so the
table above is tested rather than claimed.

## The Ten Graphs

| id | family | nodes | edges | depth | width | topology | catalogue | gold |
|---|---|---|---|---|---|---|---|---|
| syn-001 | math | 3 | 2 | 3 | 1 | chain | 10 | `400.0` |
| syn-002 | math | 4 | 4 | 3 | 2 | diamond, fan-out at n1 | 11 | `0.7142857142857143` |
| syn-003 | math | 5 | 6 | 5 | 1 | fan-out star, n1 feeds 3 consumers | 12 | `25.0` |
| syn-004 | math | 6 | 5 | 4 | 3 | convergent tree, 3 independent roots | 13 | `102` |
| syn-005 | math | 6 | 5 | 6 | 1 | deep chain | 12 | `25.971200000000007` |
| syn-006 | code | 4 | 3 | 4 | 1 | chain, string→array→array | 14 | `[42, 23, 18]` |
| syn-007 | code | 5 | 5 | 5 | 1 | diamond, one root reaches the sink by two disjoint paths | 15 | `[119, 119]` |
| syn-008 | code | 5 | 5 | 5 | 1 | diamond on strings | 14 | `'<a href="nested-api-calls-planning">…</a>'` |
| syn-009 | code | 5 | 5 | 5 | 1 | computed value lands on a scalar index parameter | 15 | `'22\|31\|9'` |
| syn-010 | mixed | 6 | 6 | 5 | 2 | fan-out + fan-in crossing the tool families | 16 | `205.44` |

Full diagrams, traces and queries: [GRAPHS.md](GRAPHS.md).

Three structures here are rare or absent in NESTFUL itself and are the point of
generating rather than sampling:

- **syn-009** routes a computed *integer* into `swap_by_index`'s `j` parameter. The
  model cannot treat "which position" as a constant it can read off the prompt.
- **syn-010** crosses the math and coding families mid-sequence, so the reference
  suffix changes from `.output_0$` to `.result$` partway through. A model that
  pattern-matches the suffix instead of reading `output_parameters` fails it.
- **syn-007** reaches the sink from a single root along two disjoint paths, so a
  model that collapses the graph to a chain drops an edge.

## Regenerating

```bash
pip install pyarrow                    # only needed for the parquet output
python build_dataset.py
```

Deterministic: distractors are drawn with a per-task fixed seed and `sample_id`s
are UUID5 over a fixed namespace, so a rebuild is byte-identical.

```
data/synthetic_nestful_v1.parquet   NESTFUL schema exactly: sample_id, input, output, tools, gold_answer (all strings)
data/synthetic_nestful_v1.jsonl     the same rows plus graph_stats, graph_edges, mermaid, trace, literal_query
GRAPHS.md                           per-task diagram, query, trace, gold answer
```

`inspect_graphs.py` prints every graph, its edge list and its executed trace
without writing anything — useful while designing new topologies.

## Files

| file | role |
|---|---|
| `tools_library.py` | 57 tools: NESTFUL catalogue spec + real Python implementation + phrase template |
| `graph_builder.py` | `CallGraph`: validation, topological sort, execution, mermaid, linearisation |
| `graphs.py` | the ten DAGs — written before any query text existed |
| `queries.py` | the authored queries and the declared literal surface forms |
| `build_dataset.py` | catalogue assembly, the checks, and the emitters |
| `inspect_graphs.py` | dry-run viewer |
| `test_guards.py` | negative tests: injects one fault per guard, asserts each fires |

## Scaling Past Ten

`graphs.py` is currently hand-written, which is what makes the ten topologies
deliberate. Two extensions keep the guarantees intact:

1. **Sample graphs instead of writing them.** Draw a topology (chain / diamond /
   tree / star), then fill it by type-matching: a node's parameter can take an edge
   from any earlier node whose `output_parameters` type is compatible. Every check
   in the table above still applies, so malformed samples are dropped rather than
   shipped.
2. **Automate step 5.** Given the topology, the tool specs and the executed trace,
   a model writes the query; the literal-coverage, no-leak and re-execution checks
   then reject queries that under-determine or over-determine the answer. This is
   the only step where an LLM is load-bearing, and it is the step with the
   strongest automated guard.

The literal-coverage check is the piece that makes automation safe: it is what
stops a generated query from quietly omitting an input the answer depends on.
