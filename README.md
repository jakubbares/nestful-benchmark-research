# NESTFUL Benchmark Research

Reproduction and extension of the [NESTFUL](https://arxiv.org/abs/2409.03797) nested
function-calling benchmark (IBM, 2024) — matched-infrastructure evaluation of four models
(Qwen3-4B-Instruct, Qwen3-4B-Thinking, Hammer2.0-7b, xLAM-7b-fc-r) on the full 1,861-sample
dataset, plus an evidence-based prompt fix validated with paired significance testing.

## Start here

- **[`nestful-qwen3-4b/nestful_explorer.html`](nestful-qwen3-4b/nestful_explorer.html)** —
  the interactive dashboard. Self-contained, no server needed: download and open directly in
  a browser. Every sample, every run, every prompt, per-sample execution diagnosis, and a
  paper-vs-reproduction comparison.
- **[`nestful-qwen3-4b/REPORT.md`](nestful-qwen3-4b/REPORT.md)** — the full written report:
  results tables, significance tests, error taxonomy, methodology, and an explicit record of
  what was checked, what broke, and how it was fixed along the way.

## Layout

```
benchmark-research/    Landscape survey of function-calling benchmarks + a synthetic
                        NESTFUL-style dataset generator (motivation for this work)
nestful-qwen3-4b/
  REPORT.md             Full writeup
  nestful_explorer.html The dashboard
  scripts/               Inference harness (vLLM) used to generate every run
  viewer/                Dashboard build pipeline (score_all.py -> build_payload.py ->
                          assemble.py) and its own correctness test suite
```

Raw per-sample model outputs and rebuild intermediates aren't committed here (kept out to
keep the repo small) — the dashboard already embeds everything needed to browse every result,
and `viewer/README.md` documents how to regenerate it from a fresh model run.
