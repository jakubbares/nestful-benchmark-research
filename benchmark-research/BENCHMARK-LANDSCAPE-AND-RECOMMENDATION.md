# Agentic Benchmarks for the PhD — Landscape + What We Should Build

*Research compiled 2026-06-10. Grounds: `the-goal-rrlm-beamer-v3.pptx`, `mental-operations-research/0-idea.md`, `claims-audit/*`. Five parallel deep-research sweeps over ~90 benchmarks (deep-research/web agents, long-context aggregation, reasoning-trace diagnostics, auto-research/science agents, general agentic + RL environments).*

---

## 0. The thesis the benchmark has to serve

The proposal's spine (from the deck + Idea Zero): an **RL-trained recursive agent (RRLM)** that learns to **select → compose → sequence "mental operations"** — where each operation can *open up into fetch + process + reason + verify* (i.e. a tool call / recursive self-call) — **instrumented by a diagnostic taxonomy** of how it reasons, applied to an **auto-research agent** (Mode A: global/aggregate QA over a paper corpus; Mode B: propose & run experiments). The deck already commits (Slide 7 Y2, Slide 25) to *"build our own agent-reasoning + long-context benchmark."* This document says **what** that benchmark should be.

The benchmark must score four things current benchmarks score **separately, never together**:
1. **Aggregation** (global queries where RAG provably fails), not single-needle retrieval.
2. The **reasoning/operation trace**, not just the final answer.
3. **Cost** — accuracy on a quality-vs-compute Pareto frontier, because the whole RRLM economics argument is about cheap leaf calls.
4. **Recursion as a first-class action** — "call yourself / call a cheaper model" as a rewarded decision.

---

## 1. The landscape, in five families

### A. Deep-research / web-search agents
| Benchmark | What it is | Corpus | Scores trace? | Aggregation? |
|---|---|---|---|---|
| **GAIA** (2311.12983) | assistant Q&A, 466 q, exact-match | live web | no | mixed |
| **BrowseComp** (2504.12516) | hard multi-hop, exact-match | live web | no | single-needle (deep) |
| **BrowseComp-Plus** (2508.06600) | BrowseComp over **fixed ~100k-doc corpus**; separates retriever from reasoner | **fixed** | retrieval only | single-needle |
| **Mind2Web 2** (2506.21506) | long-horizon synthesis, tree-rubric Agent-as-Judge | live web | citations only | **yes** |
| **DeepResearch Bench** (2506.11763) | PhD-level report gen, RACE+FACT judges | live web | citations only | **yes** |
| **FRAMES** (2409.12941) | integrate **2–15 docs**, oracle ceiling 73% | **fixed (Wiki)** | no | **yes** |
| **Seal-0** (2506.01062) | conflicting-evidence robustness, best o3 17% | live | no | reconcile |
| **ResearcherBench** | frontier-AI research Qs, coverage+faithfulness | live | citations | yes |

**Template to copy:** BrowseComp-Plus's *fixed corpus + retriever/reasoner split* (reproducibility) and DeepResearch Bench's *RACE+FACT* split (answer quality vs citation faithfulness).
**Universal gap:** every one scores the **final answer** (or at best output-side citation faithfulness); **none scores the internal reasoning process**, none is cost-bounded.

### B. Long-context / corpus-level aggregation — *the "RAG fails on global queries" evidence*
| Benchmark | Aggregation order | Headline result |
|---|---|---|
| **GlobalQA / GlobalRAG** (2510.26205) | **O(n)/O(n²)**: count, extremum, sort, top-k | strongest RAG baseline = **1.51 F1** (catastrophic) → tool pipeline 6.63 |
| **Oolong** (2511.02817) | O(n) classify-then-count over every chunk | **GPT-5 / Claude-Sonnet-4 / Gemini-2.5-Pro all <50%** at 128K |
| **NoCha** (2406.16264) | global book reasoning vs local pairs | best model **55.8%**, open models at chance on *global* pairs |
| **Loong** (2406.17419) | Spotlight O(1) / Compare O(n²) / Cluster O(n) | escalating-order multi-doc, no-noise |
| **SummHay** (2407.01370) | O(n) coverage + citation | both long-ctx LLMs (<20%) and RAG below human (~56%) |
| **Michelangelo Latent-List** (2409.12640) | O(n) sequential execution | a code interpreter solves trivially; LLMs degrade to 1M tokens |
| **GraphRAG Local→Global** (2404.16130) | global theme/sensemaking | argues this is QFS, *not retrieval* — RAG cannot do it |
| **RULER** (2404.06654) | CWE/FWE O(n) counting | "claimed 32K ≠ effective 32K" |
| **BABILong** (2406.10149) | counting/lists in noise to 10M | RAG ≈60% & length-independent on O(1); breaks on O(n) |

**This family is the empirical backbone of the deck's core claim.** GlobalQA's 1.51 F1 and Oolong's <50% are the cleanest published "RAG/long-context fails on aggregation" numbers — cite them on Slides 4 & 14.
**Gap:** none varies aggregation **order as a controlled axis over a fixed corpus**, none is **cost-bounded**, none exposes the **operation structure**.
*(Correction to our note files: "OOLONG-Pairs" is not a real subtask — Oolong's splits are synth/real; the "1,001 pairs" benchmark is **NoCha**. The RL global-RAG method is a separate paper, 2510.20548.)*

### C. Reasoning-trace / process diagnostics — *the instrument half (Slides 5–6, 9–10)*
- **Camp 1 — step-correctness PRMs** (PRM800K 2305.20050, Math-Shepherd 2312.08935, ProcessBench 2412.06559, PRMBench 2501.03124, MR-Ben 2406.13975, REVEAL 2402.00559). Labels steps right/wrong, **already feeds RL** — but **single-model, text-only MATH CoT**; "is this step correct," not "what *kind* of thinking is this."
- **Camp 2 — cognitive-operation taxonomies** (the real precedent for our taxonomy):
  - **Cognitive Foundations** (2511.16660) — 28 cognitive elements, ~192K traces, GPT-4.1 auto-labeller, PPMI(element→success); meta-cognition rare (~20%) but predictive; **test-time scaffolding +66.7%**. Our **nearest competitor on the diagnostic half** — but pure single-model CoT, **no reported classifier-vs-human agreement** (a rigour gap we can fill), non-agentic.
  - **Gandhi "Cognitive Behaviors"** (2503.01307) — verification/backtracking/subgoaling/backward-chaining; **priming these behaviours causally unlocks RL self-improvement**. The load-bearing precedent that *operation taxonomy → RL gains*. Still math (Countdown), not agentic.
  - **Thought Anchors** (2506.19143) — counterfactual resampling finds *which* steps matter (planning/backtracking dominate). Gives us a **causal** method, not just correlation.
- **Camp 3 — agentic-trace diagnostics** (the frontier, mostly late-2025/2026):
  - **AgentProcessBench** (2603.14465) — first human step-level effectiveness labels on **real tool-using traces** (GAIA, τ²-bench, BFCL); κ=0.767, step-skill↔outcome r=0.814. **Closest existing artifact** — but labels *effectiveness*, not an **operation taxonomy**, and does **not** drive RL.
  - **Who&When** (2505.00212), **AgentRx** (2602.02475), **AgenTracer** (2509.03312) — agentic, but framed as **failure attribution** ("which step broke / who's to blame"), not a *positive* taxonomy → success → RL loop.
- **Faithfulness caveat** (Turpin 2305.04388; Anthropic <20% faithfulness): free-text CoT lies. **This is an argument *for* the agentic framing** — tool calls are externally grounded and verifiable where CoT is not.

**The empty quadrant:** *operation taxonomy (Camp 2) × real agentic traces (Camp 3) × validated labeller × predictive-of-success × fed into RL.* No artifact occupies it.

### D. Auto-research / science agents — *the application target*
- **Mode A (corpus QA):** Qasper (single-paper), SPIQA/M3SciQA (multimodal, small clusters), PaperQA2/LitQA2 (live APIs, *not* fixed/reproducible), **PaperArena** (2510.10909 — cross-paper tool reasoning, best agent 38.78%), **CorpusQA** (2601.14952 — true **10M-token global/aggregate** corpus QA, *but LLM-judge-scored, no trace, brand-new*).
- **Mode B (run experiments):** MLE-bench (2410.07095), PaperBench (2504.01848, 8,316 rubric nodes — *not solo-buildable*), RE-Bench (2411.15114, clean human-vs-agent), ScienceAgentBench (2410.05080), CORE-Bench (2409.11363), SUPER (2409.07440), DiscoveryWorld (2406.06769 — cheap simulation), SciCode (2407.13168, Claude 3.5 only 4.6%).
- **Holistic:** **AstaBench** (2510.21652) — 2,400+ problems, reproducible scientific-search environment, **cost-controlled scoring**. The closest single artifact to the whole auto-research vision; the cost-control design is the one to emulate.

**Gap:** no benchmark couples **global/aggregate QA over a *frozen* paper corpus** with a **reasoning-trace diagnostic**, under **cost bounds**, with **objectively computable** ground truth.

### E. General agentic + RL environments — *the training ground*
- **Verifiable-reward RL environments (reusable):** SWE-Gym (2412.21139) → R2E-Gym/SWE-Universe; **AppWorld** (2407.18901, state unit-tests + collateral-damage penalty); **Aviary** (2412.21154 — scientific LDP/POMDP gym, *explicitly shows small trained agents beat frontier zero-shot at lower cost* — the most thesis-aligned env); AgentGym-RL, RAGEN/StarPO, Search-R1.
- **RL infra:** **verl** (2409.19256) and **SkyRL** (2511.16108) are the backbones (RRLM itself is SkyRL). **ART+RULER** = LLM-judge relative reward if we want learned rewards.
- **Cost-frontier evaluation:** **HAL** (2510.11977) — the canonical accuracy-vs-cost Pareto leaderboard (Cost-Per-Success); finding: cheap models dominate the frontier, more reasoning effort *hurt* accuracy in 21/36 runs. Also OSWorld-Human (step efficiency), SWE-Lancer (success→$), M3ToolEval (turn counts).
- **Reliability:** τ-bench/τ²-bench `pass^k` metric (same task solved on *all* k trials) — a metric worth borrowing.

**Gap:** **no environment treats "recurse / spawn sub-agent / call a cheaper model" as a first-class rewarded action on a cost-vs-quality frontier.** Pieces exist (verl/SkyRL + AppWorld/Aviary + HAL); the composition is open.

---

## 2. The convergent gap (all five sweeps agree)

> **Every benchmark in the field scores ONE of {final answer, aggregation, trace, cost}. None scores their conjunction. The conjunction is exactly the RRLM thesis.**

- Deep-research benchmarks: answer-only, not cost-bounded, not trace-scored.
- Aggregation benchmarks: prove RAG fails globally, but in-context only, no cost axis, no structure.
- Trace benchmarks: taxonomy exists but on math CoT; agentic-trace work is failure-attribution only, no RL loop.
- Auto-research benchmarks: closest is CorpusQA (no trace, LLM-judge) / AstaBench (cost-aware, no aggregate-QA-+-trace coupling).
- RL environments: no first-class recursion action, no cost-frontier reward.

This is unusually clean white space for a PhD: the gap isn't "do X better," it's "X has never been measured."

---

## 3. Recommendation — build TWO coupled deliverables (one programme)

These map 1:1 onto the deck's existing timeline and are the *same* artifact viewed from two ends.

### Deliverable 1 (Year 1, the wedge) — **Agentic Operation-Trace Diagnostic + Taxonomy**
*The instrument from Slides 5–6 / 9–10. Lead with this — it's falsifiable, solo-buildable, and de-risks everything.*

- **Substrate:** real agentic traces — Claude / Cursor / RLM / SWE-agent / WebArena / τ²-bench / AgentTrek (2412.09605, 10k web-agent trajectories ready to annotate).
- **Build:** port Cognitive Foundations' 28-element taxonomy into an **agentic operation taxonomy** (decompose, retrieve-via-tool, compare, hypothesise, verify-against-environment, backtrack, abstract, plan, replan, **recurse/self-call**, **delegate-to-cheaper-model**) defined over tool-use traces.
- **The rigour others skip:** report **human↔LLM-labeller agreement** (κ) — the exact thing Cognitive Foundations omits.
- **Predictive validity:** show which operation *sequences* correlate with (PPMI) and **causally drive** (Thought-Anchors-style counterfactual resampling) task success — and extend AgentProcessBench's r=0.814 from a binary "effective" label to *typed* operations.
- **Why it wins:** it is the first taxonomy × **agentic** traces × validated labeller × success-prediction. AgentProcessBench has the agentic traces but no taxonomy; Cognitive Foundations has the taxonomy but no agentic traces and no validation.
- **Y1 paper** = exactly the deck's "Trace diagnostic tool + ops taxonomy."

### Deliverable 2 (Year 2, the headline benchmark) — **Cost-Bounded Aggregate-QA-over-a-Frozen-Corpus, with Gold Operation Traces**
*Working name placeholder: **CORE-Agg** (Corpus-level Operation-traced Recursive Evaluation). This is the "agent-reasoning benchmark dataset" of Slide 7.*

Four design decisions, each chosen to occupy the empty quadrant:

1. **Frozen corpus, not live web.** Freeze a mid-size domain slice of arXiv (e.g. the agent/RLM literature — *dogfoodable*, CIIRC-relevant). Reproducible and contamination-controlled — the BrowseComp-Plus discipline. *(Live benchmarks GAIA/BrowseComp/Mind2Web-2 become secondary validation only.)*
2. **Questions generated at controlled aggregation order O(1)/O(n)/O(n²)** — single fact / count-filter-extremum / pairwise-compare-sort — **with programmatically computable ground truth.** This is the decisive advantage over CorpusQA and BixBench/PaperBench: answers are **objectively checkable**, sidestepping LLM-judge reliability, *and* it lets you plot the deck's O(1)/O(n)/O(n²) "gap grows with order" curve (Slide 14) as a first-class result.
3. **Cost-metered → score on an accuracy-vs-cost Pareto frontier** (HAL's Cost-Per-Success), not raw accuracy. This is the only way to give the RRLM credit for being *cheaper*, not just more accurate — the entire leaf-call economics argument (Slides 13, 15).
4. **Gold evidence set + gold operation trace per question** → the benchmark *natively* feeds Deliverable 1's diagnostic and serves as a **verifiable-reward RL environment** for the RRLM. "Recurse / call cheaper model" is a first-class scored action (the gap from family E).

This single benchmark stresses **all four** of long-context, aggregation, recursion+tools, and operation-tracing **simultaneously** — which is precisely what Idea Zero (`0-idea.md` §"Why this domain is the right choice") demands.

### What to REUSE (don't rebuild) — your baseline + infrastructure stack
- **External baselines / validation:** BrowseComp-Plus, FRAMES, GlobalQA, Oolong, Loong, SummHay, Michelangelo (aggregation); AgentProcessBench, ProcessBench (trace); PaperArena, AstaBench, CorpusQA (auto-research). Run against these to prove generality.
- **RL training:** SkyRL / verl backbone (RRLM already uses SkyRL); Aviary as the scientific-gym precedent; AppWorld for the collateral-damage reward idea.
- **Cost methodology:** HAL's Cost-Per-Success + Pareto frontier; τ²-bench `pass^k` reliability metric.

---

## 4. Why this is the right benchmark (one paragraph for the committee)

The auto-research agent is not an arbitrary application — it is the *only* target that forces all four uninstrumented axes into one task: a frozen paper corpus is too big for context (long-context), global questions break RAG (aggregation), answering them needs recurse-grep-compute-aggregate (recursion + tools), and a paper-research trace is exactly what the diagnostic taxonomy is built to read (operation-tracing). Every existing benchmark measures one axis; building the corpus-level, aggregation-ordered, cost-metered, trace-instrumented benchmark over a frozen arXiv slice gives the PhD a deliverable that (a) is objectively scorable, (b) is solo-buildable (synthetic-but-verifiable questions, not 8,316 expert rubric nodes), (c) doubles as the RRLM's RL training environment, and (d) is the natural home for the Year-1 diagnostic instrument. The contribution is not "higher accuracy" — it is **"measurably better reasoning structure per unit of compute, on queries that defeat RAG, with the structure made visible."**

---

## 4b. Locked decisions (2026-06-10) — corpus = AI/RLM literature; scope = Mode A **and** Mode B

**Corpus:** a frozen slice of the **agent / recursive-LM / RL-for-LLM literature** (the ~90 papers in this very landscape + their reference closure, ~1–3k papers). Dogfoodable, CIIRC-relevant, and you can personally verify gold answers — which is what makes objective scoring credible.

**Scope:** build **both modes from day one**, but keep Mode B *cheap-to-grade* so it stays solo-feasible. The trick is that **both modes share one substrate and one trace format**, so Mode B is an extension of Mode A, not a second project:

- **Mode A — aggregate corpus QA (the objectively-scored core).** O(1)/O(n)/O(n²) questions with programmatic ground truth over the frozen corpus. This carries the headline numbers and the cost-frontier curve.
- **Mode B — propose & run experiments, made tractable.** Do **not** rebuild MLE-bench/PaperBench (8,316 rubric nodes, GPU farms). Instead scope Mode B as **micro-experiments with checkable outcomes**, three escalating tiers so you can ship Tier 1 in Y2 and grow:
  1. **Tier 1 — reproduce-a-number (objective).** "From paper X's setup, run the provided/derivable code and recover the reported metric within tolerance." Borrow the CORE-Bench/SUPER pattern: pass = number matches. Buildable from the corpus's own released code; **no GPUs beyond small models** if you pick CPU/small-model papers (the RRLM/SkyRL ecosystem has many).
  2. **Tier 2 — design-then-run a controlled ablation (objective-ish).** "Given finding F, design and execute the experiment that confirms/refutes it." Scored on whether the executed result moves in the predicted direction + a rubric on design validity (AAAR-style ExperimentDesign).
  3. **Tier 3 — open proposal (judged, Y3+).** Sakana-AI-Scientist-style, graded by RE-Bench-style human/LLM review. Optional stretch.
- **Why both fit one PhD:** Mode A's gold *operation trace* and Mode B's *experiment trace* use the **same operation taxonomy** (Deliverable 1), so the diagnostic instrument scores both, and the RRLM trains on both with the same SkyRL harness. Mode B Tier 1 reuses Mode A's frozen corpus + the papers' own code — almost no new annotation. Keep Mode B's headline claim narrow ("agents can recover N reported results under a cost budget"); let Mode A carry the aggregation/cost-frontier science.
- **Grading cost guard:** every Mode B tier must have a *programmatic* pass signal (number-match or direction-match) as its primary metric; LLM/human judging is secondary. This is what keeps it from becoming PaperBench.

## 5. Risks / honest caveats
- **Auto-labeller reliability** (Deliverable 1) — must validate vs human labels; the deck already flags this (Slide 25). This is the make-or-break.
- **Synthetic-question realism** (Deliverable 2) — programmatic ground truth risks artificiality; mitigate with a natural-question subset judged like FRAMES/SummHay, and report the gap.
- **Kill experiment first** (from `0-idea.md`): if a trained select-compose-sequence policy does **not** beat fixed-library Self-Discover / single-template BoT on the agentic benchmark, the Idea-Zero contribution collapses. Build the benchmark *first* precisely so this is testable in Y1–Y2.
- **Scope discipline:** Mode B (run experiments) is heavy (MLE-bench/PaperBench scale). Keep the *headline* benchmark on Mode A (aggregate corpus QA); treat Mode B as a Year-3 extension validated on RE-Bench/ScienceAgentBench rather than rebuilt.

---

## 6. arXiv index (load-bearing)
GlobalQA 2510.26205 · Oolong 2511.02817 · NoCha 2406.16264 · Loong 2406.17419 · SummHay 2407.01370 · Michelangelo 2409.12640 · GraphRAG 2404.16130 · RULER 2404.06654 · BABILong 2406.10149 · BrowseComp-Plus 2508.06600 · FRAMES 2409.12941 · Mind2Web2 2506.21506 · DeepResearch Bench 2506.11763 · Seal-0 2506.01062 · Cognitive Foundations 2511.16660 · Gandhi Cognitive Behaviors 2503.01307 · Thought Anchors 2506.19143 · ROSCOE 2212.07919 · ProcessBench 2412.06559 · PRMBench 2501.03124 · AgentProcessBench 2603.14465 · Who&When 2505.00212 · AgentRx 2602.02475 · AgentTrek 2412.09605 · Turpin 2305.04388 · PaperArena 2510.10909 · CorpusQA 2601.14952 · AstaBench 2510.21652 · RE-Bench 2411.15114 · ScienceAgentBench 2410.05080 · PaperBench 2504.01848 · MLE-bench 2410.07095 · DiscoveryWorld 2406.06769 · Aviary 2412.21154 · SWE-Gym 2412.21139 · AppWorld 2407.18901 · HAL 2510.11977 · τ-bench 2406.12045 · verl 2409.19256 · SkyRL 2511.16108.
