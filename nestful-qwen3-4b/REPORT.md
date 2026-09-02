# NESTFUL × Qwen3-4B — Reproduction Report (v6: parser-gap correction + checklist on all 4 models)

**Dates:** 2026-08-21 (initial inference), 2026-08-26 (validation + correction), 2026-08-26/27 (matched-infra rerun + audit fixes), 2026-08-30/31 (+xLAM-7b-fc-r, +Qwen3-4B-Thinking-2507), 2026-09-01 (+evidence-based output checklist), 2026-09-02 (+checklist on Qwen3-Instruct/Thinking, found + fixed a parser gap that affected every prior Qwen3-Instruct number)
**Models:** `Qwen/Qwen3-4B-Instruct-2507` @ `cdbee75f`, `Qwen/Qwen3-4B-Thinking-2507` @ `768f209d`, `MadeAgents/Hammer2.0-7b` @ `2e267cc2`, `Salesforce/xLAM-7b-fc-r` (all pinned)
**Benchmark:** NESTFUL, official GitHub code + data (github.com/IBM/NESTFUL), full dataset, 1861 samples

---

## v6 correction: a parsing gap silently understated every Qwen3-Instruct number in this report

Extending the v5 checklist experiment to Qwen3-Instruct produced a surprising result: Win Rate looked like it *dropped* under the checklist. Before reporting that, the raw generations were inspected directly — the same discipline that has driven every version of this report.

**What was found:** IBM's own official parser strips markdown fences with `generated_text.replace("```", "")`. That handles a bare ` ``` ` fence but leaves a language tag behind: ` ```json\n[...] ` becomes `json\n[...]` — not valid JSON, so `json.loads()` raises and the sample is scored as a parse failure. Qwen3-Instruct (never Hammer, xLAM, or Qwen3-Thinking) sometimes emits ` ```json `-tagged fences instead of bare ones — including in the **already-published** `qwen3_3shot` baseline (60/1861 = 3.2% of samples). This has been silently understating Qwen3-Instruct's Partial/Full/Win numbers in every version of this report since v1.

**The fix:** `score_all.py` now strips any ` ```<language> ` fence (regex `` ```[a-zA-Z]* ``), not just a bare ` ``` `, and the same fix went into the refusal-detection logic and `build_payload.py`'s F1 computation. **Verified inert everywhere it should be:** re-scored all 15 runs with the fix and diffed against the unpatched numbers — Hammer, xLAM, and Qwen3-Thinking runs are exactly 0.0000 different on every metric; only the four Qwen3-Instruct(-based) runs changed.

**Corrected numbers** (previously published → corrected, 3-shot):

| Metric | qwen3_3shot (published) | qwen3_3shot (corrected) | Δ |
|---|---|---|---|
| Partial Acc | 0.290 | 0.320 | +3.0pp |
| Full Acc | 0.207 | 0.234 | +2.7pp |
| Win Rate | 0.318 | 0.342 | +2.4pp |
| Parse fail | 0.147 | 0.115 | −3.2pp |
| Refusal | 0.106 | 0.106 | unchanged |

Refusal is untouched (a bare `[]` never carries a language tag), and F1 Func rises too (0.855→0.975) for the same reason, though F1 remains untrusted for the structural reasons discussed below regardless. The correction is one-directional and monotonic: Qwen3-Instruct's true performance was always at least as good as what was previously reported, never worse — every downstream comparison that already favored Qwen3-Instruct over Hammer (v3's headline finding) gets *stronger*, not weaker, under the fix. Every table below reflects the corrected numbers; see "Files" for exactly which script changed.

**Why this survived four prior report versions:** every earlier version's manual raw-generation spot-checks happened to sample outputs that didn't hit this fence style, and the byte-exact prompt-reconstruction test suite (`prompt_test.mjs`) checks *prompts*, not *parsing* — it was never positioned to catch a scoring-side bug like this one. Caught only because the v6 checklist experiment produced a result unusual enough (a metric moving the "wrong" direction) to trigger a direct inspection of the raw text, which is the same mechanism that caught every other bug in this report's history. Lesson generalized into takeaway #11 below.

---

## v6: the checklist, extended to all four models — a genuinely mixed result

v5 tested the 7-item output checklist (see below) on Hammer and xLAM only. Extending it to Qwen3-Instruct and Qwen3-Thinking — using the corrected parser above for a fair before/after on both sides — gives a result that is **not** "the checklist works":

| Model (3-shot) | Metric | Baseline | +Checklist | Δ | p |
|---|---|---|---|---|---|
| Qwen3-4B-Instruct | Partial Acc | 32.0% | 31.4% | −0.5pp | — |
| Qwen3-4B-Instruct | Full Acc | 23.4% | 20.9% | **−2.5pp** | 0.0000 |
| Qwen3-4B-Instruct | **Win Rate** | 34.2% | 32.6% | **−1.6pp** | 0.042 |
| Qwen3-4B-Instruct | Refusal | 10.6% | 3.7% | −6.9pp | 0.0000 |
| Qwen3-4B-Instruct | Parse fail | 11.5% | 4.9% | −6.5pp | — |
| Qwen3-4B-Thinking | Partial Acc | 38.5% | 39.7% | +1.2pp | — |
| Qwen3-4B-Thinking | Full Acc | 26.3% | 26.9% | +0.6pp | 0.462 (n.s.) |
| Qwen3-4B-Thinking | **Win Rate** | 76.0% | 78.7% | **+2.6pp** | 0.0005 |
| Qwen3-4B-Thinking | Refusal | 6.3% | 1.5% | −4.9pp | 0.0000 |
| Qwen3-4B-Thinking | Parse fail | 6.3% | 1.5% | −4.9pp | — |

Combined with v5: the checklist significantly **improves** Win Rate for Hammer (+5.4pp), xLAM (+3.1pp), and Qwen3-Thinking (+2.6pp) — three of four models — and **significantly hurts** Qwen3-Instruct's Win Rate (−1.6pp, p=0.042) and Full Acc (−2.5pp, p<0.001), despite also cutting its refusal rate by more than half.

**Why Qwen3-Instruct is the exception, traced to real generations (not a parsing artifact — checked directly, given the v6 correction above made exactly this kind of false alarm plausible):** of the 636 samples Qwen3-Instruct won at baseline, 110 flip to a loss under the checklist (68 new wrong answers, 39 new execution errors, only 3 new parse failures — genuine regressions, not fence-tag noise); only 81 previously-lost samples flip to a win, for a net loss of 29 samples (−1.6pp). Of the 197 baseline refusals, forcing "never refuse" produces a *correct* answer only 13 times (6.6%) — mostly it just converts a refusal into a new wrong attempt. And unlike Hammer (8.4% missing-label rate) and xLAM (38.4%), Qwen3-Instruct barely had the checklist's core target problem to begin with (0.1% missing-label rate at baseline) — so the checklist's main lever has nothing to pull for this model, while its "never refuse" item still pushes it into attempting cases it would otherwise have correctly declined.

**Net recommendation:** keep the checklist for Hammer, xLAM, and Qwen3-Thinking; do not apply it as-is to Qwen3-Instruct. This is visible in the dashboard's Overview tab, same card as v5, now with all four models and an updated "Reading this" note.

---

## v5: an evidence-based output checklist — does it actually fix the errors we found?

The trigger for this round was a complaint that the model was "putting in wrong arguments." Rather than write a prompt fix on that assumption, the raw generations were reviewed first, specifically to confirm or refute it.

**What the logs actually showed (measured, not assumed), on the 3-shot baselines:**
- The literal complaint — wrong argument *values* — exists but is not the dominant pattern.
- The dominant, confirmed pattern is **missing `"label"` fields**: 8.4% of Hammer's outputs and 38.4% of xLAM's had at least one function call with no `"label"` key, which breaks any later call that references it via `$var_N.result$`.
- A second confirmed pattern is **refusal** (`[]`) at a rate (16.0% for Hammer) that this report's own earlier integrity check shows is never objectively justified — 0/1861 gold solutions ever need a function outside the sample's own tool catalog.
- A third, smaller, distinct issue specific to xLAM: 26/1861 (1.4%) of baseline outputs were visibly truncated (not ending in `}`/`]`) under its 1000-token cap — a budget problem, the same failure shape as the Qwen3-Thinking truncation bug earlier in this report, not a reasoning problem.

**The fix:** a 7-item output checklist (every call has a label; valid JSON, no markdown fences; `$var$` references quoted; argument values computed, not left as expressions; exact function names; correct argument types; never refuse) injected once, verbatim, before `[BEGIN OF QUERY]` in each model's existing template. The rest of the prompt-construction path is untouched — confirmed byte-identical to before when `--checklist` is not passed. xLAM's `max_tokens` was also raised 1000→2000 in the same run to address the truncation issue; because both changes shipped in one run (per the confirmed test scope), xLAM's before/after numbers reflect both together and the two contributions aren't separated here. Both models rerun at 3-shot, same pinned revision and infra as their baselines, so this is a clean paired before/after on the same 1,861 samples — full prompt (with checklist) and full response stored for every sample.

**Results** (paired McNemar exact test, 1,861 samples, `matched_results/{hammer,xlam}_3shot_checklist/`):

| Model (3-shot) | Metric | Baseline | +Checklist | Δ | p |
|---|---|---|---|---|---|
| Hammer2.0-7b | Partial Acc | 29.0% | 30.4% | +1.4pp | — |
| Hammer2.0-7b | Full Acc | 21.7% | 20.6% | −1.0pp | 0.045 |
| Hammer2.0-7b | **Win Rate** | 25.3% | 30.7% | **+5.4pp** | ≈0.000000 |
| Hammer2.0-7b | Refusal | 16.0% | 2.4% | **−13.7pp** | ≈0.000000 |
| Hammer2.0-7b | Parse fail | 17.9% | 4.1% | −13.8pp | — |
| Hammer2.0-7b | Missing-label rate | 8.4% | 1.9% | −6.5pp | — |
| xLAM-7b-fc-r | Partial Acc | 23.0% | 24.6% | +1.7pp | — |
| xLAM-7b-fc-r | Full Acc | 14.4% | 16.3% | +1.9pp | 0.0014 |
| xLAM-7b-fc-r | **Win Rate** | 14.1% | 17.1% | **+3.1pp** | 0.00002 |
| xLAM-7b-fc-r | Refusal | 0.3% | 0.0% | −0.3pp | 0.063 (n.s.) |
| xLAM-7b-fc-r | Parse fail | 11.4% | 3.4% | −8.0pp | — |
| xLAM-7b-fc-r | Missing-label rate | 38.4% | 29.8% | −8.6pp | — |

**Reading this honestly:**
- Win Rate improves significantly for both models — real evidence the checklist helps both models reach the correct final answer more often, not just an assertion.
- Hammer's refusal rate collapses (16.0%→2.4%, highly significant) — direct evidence the "never refuse" item works.
- Hammer's Full Acc *drops slightly* (−1.0pp, only marginally significant at p=0.045) even as Win Rate rises: the checklist appears to make the model more likely to reach the correct value via an alternate valid path, not more likely to reproduce gold's exact call sequence. Reported as a real, small, marginal cost, not hidden.
- xLAM's missing-label rate falls meaningfully but stays high (38.4%→29.8%) — a real, partial fix for xLAM's dominant failure mode, not a solved problem. Its refusal reduction is not statistically significant, but it was already near zero at baseline (0.3%) so there was little room to move.
- **A genuine scoring-pipeline bug surfaced along the way:** one xLAM+checklist sample's predicted call chain executed to a valid Python integer with over 4,300 digits (a runaway computation), which crashed `score_all.py`'s JSON serialization — Python 3.11+'s int→str conversion guard rejects converting integers that large to text at all, including via `repr()`. Fixed by reporting the value's bit-length instead of stringifying it, so the scorer no longer has to convert the number to text to describe it. A real edge case in the scoring code, caught and fixed rather than silently dropping that sample.

**What this does and doesn't establish:** one confirmed, evidence-based prompt fix, tested here on 2 of the report's four models at one shot-count (3-shot) — extended to the remaining two (Qwen3-Instruct, Qwen3-Thinking) in v6 above, with a genuinely mixed result. Visible in the dashboard's Overview tab under "Does an explicit output checklist fix the errors we found?"

---

## v4 headline: thinking mode changes the answer entirely

v3's conclusion — "metric-dependent split, not a blowout" — held for **Qwen3-4B-Instruct** (no reasoning) against Hammer2.0-7b. Adding a third paper model (xLAM-7b-fc-r) and Qwen3's **Thinking** sibling (identical architecture, same prompts, extended reasoning before answering) changes the picture completely:

**Qwen3-4B-Thinking-2507 dominates every other model tested, on every trustworthy metric, by a wide and statistically overwhelming margin.**

| Comparison (3-shot, Win Rate, McNemar's exact) | Thinking wins | Other wins | p-value |
|---|---|---|---|
| Thinking vs. Qwen3-Instruct (same model, reasoning on vs. off) | 857 | 78 | ≈0.000000 |
| Thinking vs. Hammer2.0-7b (paper's best model) | 1001 | 56 | ≈0.000000 |
| Thinking vs. xLAM-7b-fc-r (paper model) | 1207 | 54 | ≈0.000000 |

(Updated 2026-09-02: the Instruct row reflects the v6 parser-gap correction below. The xLAM row was independently wrong before this update — re-derived with the exact same discordant-pair method that reproduces the Hammer row unchanged, confirming that row, unlike xLAM's, was never affected by the parser gap.)

This is not the "genuine tie on one metric, real-but-modest edge on another" story from v3 — turning reasoning on turns a roughly-tied 4B model into one that wins the overwhelming majority of head-to-head disagreements against every other model in this investigation, including the paper's actual top performer. See "Getting the Thinking-mode measurement right" below for how this number was nearly reported wrong (a truncation artifact inflated it, then a stale-script bug invalidated the first correct-looking version) before landing on a verified, reproducible result.

## What v3 found (unchanged, still valid)

Two earlier passes at this report each found a problem with the one before it. v1 claimed Qwen3-4B "beat every model in the paper's Table 1." v2 found that claim invalid — a validation run showed the paper's own best model doesn't reproduce its own published F1 numbers either — and retracted it, replacing it with a smaller same-day comparison. A subsequent self-audit then found ~24 additional ways that v2's comparison could still be broken (infra asymmetries, unverified determinism, unpinned model revisions, a real domain confound, latent scorer bugs, no significance testing). v3 fixed every one of those that was actually fixable by re-running both models on identical infrastructure and adding the missing analysis:

- **Full Sequence Match** (exact function names + exact arguments, in order), Qwen3-Instruct vs. Hammer: a small but real Qwen3 edge, not a tie. McNemar's exact test, p = 0.0072 — significant (corrected 2026-09-02: the parser-gap fix below moved this from the previously-reported p=0.0998/"tie" to a real, if modest, Qwen3 advantage — of 143 disagreements, Qwen3 wins 88, Hammer 55).
- **Win Rate**, Qwen3-Instruct vs. Hammer: **Qwen3-4B-Instruct has a real, statistically significant advantage.** McNemar's exact test, p ≈ 0.00000. Of 390 examples where the two models disagree, Qwen3 wins 278 and Hammer wins only 112.
- **F1 Func/Param**: Hammer is numerically ahead (0.971/0.700 vs. 0.975/0.739 corrected — now essentially tied, in fact Qwen3 nominally ahead), but this metric was independently found to be structurally unstable (see below) — no significance test is reported for it because the metric itself isn't trusted enough to warrant one.

Since Win Rate is the execution-based metric this report otherwise treats as most trustworthy, the v3 summary was: **Qwen3-4B-Instruct (4B, general-purpose, 2025) reaches the correct final answer significantly more often than Hammer2.0-7b (7B, purpose-built for function calling, 2024).** The original second half of this claim — "even though it doesn't reproduce Hammer's exact call sequence any more often than chance would predict" — no longer holds after the v6 parser-gap correction: Qwen3 has a small but real edge there too (p=0.0072), not a tie. The core finding (Qwen3 ahead on Win Rate) still stands, and is now less qualified than before — it's just no longer the most important finding in this report.

## Full results — all 8 configurations

| Model | Shots | F1 Func* | F1 Param* | Partial Acc | Full Acc | Win Rate |
|---|---|---|---|---|---|---|
| Hammer2.0-7b | 3-shot | 0.971 | 0.700 | 0.290 | 0.217 | 0.253 |
| Hammer2.0-7b | 1-shot | 0.967 | 0.495 | 0.208 | 0.070 | 0.159 |
| Qwen3-4B-Instruct-2507 | 3-shot | 0.975 | 0.739 | 0.320 | 0.234 | 0.342 |
| Qwen3-4B-Instruct-2507 | 1-shot | 0.970 | 0.478 | 0.215 | 0.048 | 0.183 |
| xLAM-7b-fc-r | 3-shot | 0.923 | 0.590 | 0.230 | 0.144 | 0.140 |
| xLAM-7b-fc-r | 1-shot | 0.846 | 0.389 | 0.147 | 0.005 | 0.027 |
| **Qwen3-4B-Thinking-2507** | **3-shot** | **0.951** | **0.739** | **0.385** | **0.263** | **0.759** |
| **Qwen3-4B-Thinking-2507** | **1-shot** | **0.934** | **0.513** | **0.289** | **0.092** | **0.606** |

*F1 columns: internally comparable only (see below) — not comparable to the paper's Table 1. Qwen3-Instruct rows corrected 2026-09-02 — see the v6 parser-gap section above.

Qwen3-Thinking's Win Rate (0.759) is roughly **2.2× Hammer's** and **2.2× Instruct's**, and its Full Acc (0.263) is the best of any configuration tested, matched or paper-original.

## xLAM-7b-fc-r as a third paper anchor — another clean validation

xLAM-7b-fc-r is the paper's own model, run through its own dedicated prompt template (`PROMPTS.json["xLAM-7b-fc-r"]`, which wraps ICL examples and expected output as `{"tool_calls": [...]}` rather than a bare list — a real, separate template, not a reuse of Hammer's). Its own architecture caps context at 4096 tokens (`max_position_embeddings` in `config.json`) — smaller than the 8192 used for Hammer/Qwen3-Instruct; this was discovered by a hard vLLM error on first attempt, not assumed, and only 3/1861 prompts are long enough for this to matter.

Before running: paper's Table 1 (3-shot) for `xLAM-7b-fc-r` predicts F1 Func 0.49, F1 Param 0.35, Partial 0.23, Full 0.18, Win 0.19. Measured: **Partial 0.230 — matching the prediction almost exactly.** Full (0.144) and Win (0.140) landed within the same ~0.02-0.05 band seen for Hammer's reproduction; F1 predictably inflated for the by-now-familiar structural reason. This is the **third** independent model reproduction (after Hammer's two) landing in the expected range on the metrics this report trusts — real, repeated evidence the pipeline itself is sound.

## Getting the Thinking-mode measurement right — three failures caught before trusting the number

This result did not come out clean on the first, second, or even third try. Each failure was caught by checking the result against something independent, not by assuming success:

**Failure 1 — truncation contamination.** First attempt used `max_tokens=4096` (matching the other runs). Checking the raw generations directly: **30% of examples never reached a closing `</think>` tag** — the reasoning trace consumed the entire budget before producing an answer at all. The headline number from this attempt (Win Rate 0.506) was reported as a probable *floor*, not trusted as final, and the run was redone with `max_tokens=16000` / `max_model_len=20000` (median actual reasoning length turned out to be ~10,700 characters — genuinely long, not a rare outlier). Rerun confirmed: **0/1861 truncated**, and the real number (0.759) is far higher than the contaminated one — meaning the first, "lower-bound" framing was itself too conservative.

**Failure 2 — session/scratchpad wipe mid-run.** A session restart cleared the ephemeral working directory, taking the SSH private key for the in-progress EC2 job with it (AWS never stores private keys — this access was unrecoverable; the SSM-based recovery path was also attempted and failed, since this AMI doesn't run the SSM agent). The instance was terminated via the AWS API (doesn't require the lost key) and the run — plus the already-completed xLAM results, which had not yet been copied to durable storage — had to be redone from scratch. Fix adopted going forward: SSH keys and completed results now get written directly to Drive-backed storage, not left in `/tmp` until a batch pull at the end.

**Failure 3 — stale script produced an invalid xLAM run.** After the wipe, the local `run_matched.py` was restored from the Drive-backed `scripts/` copy — which turned out to predate the same session's edits adding xLAM's dedicated template routing and the `--strip_think` flag. The redone xLAM run "succeeded" (no crash, plausible-looking numbers) while actually feeding xLAM **Hammer's prompt template** — invalid, and only caught by rereading the deployed script and finding the `LLAMA_MODELS`/xLAM branching simply wasn't there. The corrected script was unit-verified locally (asserted the right template string loads for each model name) and saved to durable storage *before* being redeployed, closing the gap that caused this.

The Thinking-mode numbers reported above are from the run that survived all three checks: 0% truncation, run via the audited script, and reproducing consistent xLAM numbers as a sanity anchor on the same infrastructure.

## Matched-infrastructure results (Hammer vs. Qwen3-Instruct only, the original v3 comparison)

Both models: EC2 g5.xlarge (NVIDIA A10G, 23GB), bf16, `max_model_len=8192`, `gpu_memory_utilization=0.90`, `batch_size=32`, temperature 0.0, exact pinned HF revision. The only remaining necessary difference is vLLM version (0.6.3.post1 for Hammer vs. 0.8.5 for Qwen3) — Qwen3's architecture didn't exist when 0.6.3 was released, so no earlier vLLM can run it at all; this was verified directly, not assumed.

| Model | Shots | F1 Func* | F1 Param* | Partial Acc | Full Acc | Win Rate |
|---|---|---|---|---|---|---|
| Hammer2.0-7b | 3-shot | 0.971 | **0.700** | 0.290 | 0.217 | 0.253 |
| Qwen3-4B-Instruct-2507 | 3-shot | **0.975** | 0.739 | **0.320** | **0.234** | **0.342** |
| Hammer2.0-7b | 1-shot | **0.967** | 0.495 | 0.208 | 0.070 | 0.159 |
| Qwen3-4B-Instruct-2507 | 1-shot | 0.970 | **0.478** | **0.215** | **0.048** | **0.183** |

*F1 columns: internally comparable only (see "why F1 is unreliable" below) — not comparable to the paper's Table 1. Qwen3 rows corrected 2026-09-02, see the v6 parser-gap section above.

**Paired significance tests (McNemar's exact, 3-shot, n=1861), run on two different outcome definitions (corrected 2026-09-02):**

| Outcome tested | Both right | Both wrong | Hammer-only-right | Qwen3-only-right | p-value | Verdict |
|---|---|---|---|---|---|---|
| Full Sequence Match (exact names + args) | 348 | 1370 | 55 | 88 | 0.0072 | **Significant — small Qwen3 edge** (previously reported as a tie, p=0.0998, before the v6 correction) |
| Win Rate (execution-based) | 358 | 1113 | 112 | 278 | ≈0.00000 | **Significant — Qwen3 ahead** |

These two tests now agree with each other on direction, though not on how close the race is: Full Sequence Match shows a small, real Qwen3 edge (of 143 disagreements, Qwen3 wins 88 to Hammer's 55); Win Rate shows a much larger one (of 390 disagreements, Qwen3 wins 278 to Hammer's 112). Full Sequence Match is the strictest, most syntax-sensitive metric (penalizes any deviation from the gold call order/arguments, even a mathematically equivalent one); Win Rate is the most semantically meaningful one (did the answer come out right). By both metrics, Qwen3 is ahead — more decisively on the one this report otherwise argues is most trustworthy.

**New this version — Hammer's 1-shot result**, which didn't exist before. Hammer degrades on 1-shot too (Full Acc 0.217→0.070, Win Rate 0.253→0.159) but noticeably less than Qwen3 does (0.234→0.048, 0.342→0.183). Both degrade for the identical reason (see refusal analysis below); Hammer's degradation is milder in degree, not different in kind.

**Consistency check against the earlier, non-matched runs:** Qwen3's numbers here (bf16/A10G/vLLM 0.8.5) are within noise of the original SageMaker run (fp16/T4/vLLM-LMI 0.8.4), both corrected 2026-09-02 for the same parser gap: 3-shot F1 Func 0.975 vs. 0.975, Win Rate 0.342 vs. 0.344. Hammer's numbers here (pinned revision, explicit batch/context settings) match the earlier ad hoc validation run almost exactly: F1 Func 0.971 vs. 0.971, Win Rate 0.253 vs. 0.251. **The infra confounds flagged in the audit (fp16 vs bf16, T4 vs A10G, batch size, unpinned revisions) turned out to have negligible real effect** — worth having checked, but not the thing that was actually distorting the earlier comparison (that was the parser gap above, unrelated to infra).

## Why F1 numbers still aren't comparable to the paper (unchanged from v2, re-confirmed here)

`git log` on IBM/NESTFUL shows `scorer.py`, `eval.py`, and the full `data_v2/nestful_data.jsonl` were introduced in one commit, 2025-04-21, seven months after the paper — the only scoring implementation ever made public, and almost certainly not what generated the printed Table 1 (the old `data_v1/` has 85 examples; this has 1861). The F1 metric is a global multi-label macro-F1 over 904 function names, 91% appearing in exactly one example — mechanically unstable. This is unchanged by the matched-infra rerun; it's a property of the metric and dataset, not of run conditions. **F1 Func/Param above are reported for completeness and internal (same-day) comparison only.**

## Determinism — actually verified this time, not assumed

The prior version asserted greedy decoding without proof (the endpoint had already been torn down when the gap was noticed). This version tests it directly: 5 real prompts, duplicated within the main batch and also re-run as two independent, fresh `generate()` calls after the main run completed.

| Run | Byte-identical across two independent calls |
|---|---|
| Hammer2.0-7b, 3-shot | 5/5 |
| Hammer2.0-7b, 1-shot | 5/5 |
| Qwen3-4B, 3-shot | 5/5 |
| Qwen3-4B, 1-shot | **4/5** |

One case (Qwen3, 1-shot) produced different text across two otherwise-identical calls at temperature 0.0. This is a genuine, minor non-determinism in vLLM 0.8.5's V1 engine (Hammer's older 0.6.3 engine showed none across 10 trials) — likely floating-point non-associativity at a near-tied logit, surfacing only under different batch-composition/kernel-scheduling. The specific divergent text wasn't captured (a gap in this run's own tooling, noted honestly rather than papered over). Practical takeaway: greedy decoding here is deterministic in the overwhelming majority of cases (19/20 across both models) but not with absolute certainty — a caveat worth carrying forward, not a reason to distrust the aggregate numbers.

## Domain split — confirmed dataset-inherent, both models, both shot counts

NESTFUL blends MathQA arithmetic chains (1390/1861, 75%) with StarCoder2 coding-utility chains (471/1861, 25%). Exact function-**name**-sequence match by domain:

| Domain | n | Hammer 3-shot | Qwen3-Instruct 3-shot | Qwen3-Thinking 3-shot |
|---|---|---|---|---|
| Math | 1390 | 7.2% | 9.6% | **19.2%** |
| Code | 471 | 91.1% | **92.8%** | 89.2% |

(Qwen3-Instruct's code figure corrected 2026-09-02 from 80.7% — the parser gap above turns out to have been concentrated almost entirely in code-domain samples, plausibly because code-shaped queries prompt the model to reach for markdown formatting more than math queries do; math barely moved, 9.57% vs. the previously reported 9.6%.)

Thinking improves on math dramatically over Instruct (9.6%→19.2%, roughly doubling) — the domain where all non-reasoning models struggle most — but, after the correction, is no longer ahead of Instruct on code (89.2% vs. 92.8%). This is consistent with the mechanism: math-domain nested arithmetic benefits from working through the dependency chain step by step before committing to an answer, which is exactly what the reasoning phase provides and Direct Prompting (single-shot, no visible intermediate work) does not; code-domain exact sequencing apparently doesn't need that same step-by-step benefit for either model.

Non-reasoning models (Hammer, Qwen3-Instruct, xLAM) struggle almost identically on math-domain exact ordering (arithmetic expressions admit multiple valid function orderings, e.g. `multiply→add` vs `add→multiply`, which strict sequence matching penalizes as wrong even when correct) and both do well on code-domain tasks. Corrected 2026-09-02: Qwen3-Instruct is now slightly *ahead* of Hammer in the code domain too (92.8% vs. 91.1%), reversing the earlier "Hammer has a clear edge in code" claim, which was an artifact of the same parser gap; Qwen3 is also ahead on math (9.6% vs. 7.2%). This is the more precise, domain-aware version of the earlier "sequence composition is hard" takeaway.

## Refusal behavior — now explained, not just counted

Both models emit `[]` (declining to call any function — the Hammer-family prompt explicitly invites this: "if none of the functions can be used, point it out and refuse to answer") at meaningfully high rates, and it is **overwhelmingly concentrated in the math domain**, for both models, at both shot counts:

| Run | Refusal rate | Math / Code split of refusals |
|---|---|---|
| Hammer, 3-shot | 298/1861 (16.0%) | 295 math / 3 code (99.0% math) |
| Hammer, 1-shot | 456/1861 (24.5%) | 454 math / 2 code (99.6% math) |
| Qwen3-Instruct, 3-shot | 197/1861 (10.6%) | 194 math / 3 code (98.5% math) |
| Qwen3-Instruct, 1-shot | 374/1861 (20.1%) | 371 math / 3 code (99.2% math) |
| Qwen3-Thinking, 3-shot | 118/1861 (6.3%) | 115 math / 3 code (97.5% math) |

Thinking also has the lowest refusal rate of any configuration tested (6.3%, vs. Instruct's 10.6% and Hammer's 16.0%) — part of the same mechanism as the accuracy gain: given room to reason, the model more often finds a workable plan instead of defaulting to "no function applies," and the refusals that remain still land almost entirely in the same math domain as every other model.

This is not model-idiosyncratic over-caution — it's a shared, dataset-driven behavior, and it's the dominant mechanism behind both models' 1-shot collapse (refusals roughly 1.5-1.7× at 1-shot vs 3-shot, tracking the Full Acc/Win Rate drop closely). Likely explanation: math-domain queries in this dataset read as more "answerable via reasoning" and less obviously "needs a tool," inviting the refusal branch of the prompt's own instructions more often than code-utility queries do.

## Scorer bugs — investigated, one patched, both found to have zero measured impact

The prior audit flagged two suspected `calculate_win_score` equality bugs. On inspection, one didn't actually exist: Python's native `==` already handles `20 == 20.0` and `[20, 3.5] == [20.0, 3.5]` correctly, so int/float and mixed-type list comparisons were never broken. The real, narrower gap: floating-point noise (e.g. `20.00000000001`) against an **int**-typed gold value skips the original rounding logic entirely (it only fires when both sides are exactly Python `float`). A patched scorer (`scorer_patched.py`, isolated via monkey-patch, zero changes to IBM's original file) was unit-tested to confirm it fixes exactly this case without over-matching genuinely wrong answers — then run against all four output files:

| Run | Official Win Rate | Patched Win Rate |
|---|---|---|
| Hammer, 3-shot | 0.253 | 0.253 |
| Hammer, 1-shot | 0.159 | 0.159 |
| Qwen3, 3-shot | 0.342 | 0.342 |
| Qwen3, 1-shot | 0.183 | 0.183 |

**Identical in all four cases.** The bug is real (verified with a synthetic unit test) but never actually triggers on NESTFUL's particular numeric answers. Reported honestly as a confirmed-but-inert finding rather than oversold as a correction that moved anything.

## What was NOT fixed, and why

- **F1 metric instability is a property of the benchmark, not of my pipeline** — there is nothing to "fix" here except not trusting the metric, which this report already does.
- **Prompt-template attribution (Qwen3 mapped onto Hammer's template) remains a modeling choice, not a bug.** Testing Qwen3 under its native Hermes-style tool-calling format is a legitimate follow-up experiment, not a correctness fix, and was out of scope for this pass.
- **Possible template-level training contamination** (the Hammer/xLAM-style prompt wording is reused across public tool-calling datasets) can't be ruled out or fixed from outside the model's training data — noted as an open caveat, not resolved.
- **Single greedy run per condition, no multi-seed variance estimate beyond the 5-prompt determinism spot-check.** Running full multi-seed replicates was judged not worth the added cloud cost given the determinism check already shows 19/20 exact stability.

## Integrity checks (all still pass on the new data)

1. No ICL example leakage into the 1861-sample test set (0/3).
2. No meaningful gold-answer leakage into prompts (2/1861 coincidental, 0.1%).
3. Not a gold-copy artifact: predictions byte-identical to gold sit at 17-18%, consistent with measured Full Acc.
4. Win Rate genuinely executes predicted call chains (manually audited non-identical winning trajectories).

## Infrastructure

- Single EC2 `g5.xlarge` (A10G, us-east-1b — the first launch attempt landed in a subnet routed through a NAT gateway with no inbound path and had to be relaunched in a properly IGW-routed subnet), Deep Learning AMI, two isolated venvs (`vllm==0.6.3.post1`+`transformers==4.46.3` for Hammer; `vllm==0.8.5`+`transformers==4.51.1` for Qwen3 — the latter pin was itself a fix: pip's default resolution pulled `transformers==5.16.0`, which is incompatible with vLLM 0.8.5's tokenizer-caching code and crashed the run on first attempt).
- Both models downloaded via `huggingface-cli download --revision <pinned SHA>` to local directories — no floating "main" reference.
- Total run time ~4 hours across two sessions (one session's watcher stalled for several hours when the local machine slept overnight — an operational gap, not an infrastructure failure — and was resumed manually with no data loss).
- Cost: ≈ $4 (g5.xlarge on-demand, ~4 hours).
- All resources torn down at the end: instance terminated, security group and key pair deleted, verified absent via AWS API.

## Files

- `matched_results/hammer_3shot/`, `hammer_1shot/`, `qwen3_3shot/`, `qwen3_1shot/`, `xlam_3shot/`, `xlam_1shot/`, `qwen3thinking_3shot/`, `qwen3thinking_1shot/`, `hammer_3shot_checklist/`, `xlam_3shot_checklist/`, `qwen3_3shot_checklist/`, `qwen3thinking_3shot_checklist/` — each with `output.jsonl` (generations) and `determinism_check.json`. Thinking runs also carry `generated_text_raw` (untouched, including the `<think>...</think>` block) alongside the stripped `generated_text` used for scoring; the `*_checklist/` runs carry the full checklist-augmented prompt in `input` for every sample.
- `scripts/run_matched.py` — the matched-infrastructure harness (identical prompt construction to the original run scripts, adds the built-in determinism check, and the `--checklist`/`--max_tokens` flags used for the v5/v6 experiments)
- `viewer/score_all.py` — the per-sample rescoring pipeline; as of 2026-09-02 strips ` ```<language> ` fences (not just bare ` ``` `), the fix behind the v6 correction above
- `scripts/scorer_patched.py` — IBM's scorer with one earlier verified-inert bugfix (int/float equality) applied, isolated via monkey-patch
- `scripts/analyze_matched.py` — domain split, refusal-domain correlation, McNemar test
- Prior-version artifacts retained for provenance: `results/nestful_3/`, `results/nestful_1/` (original SageMaker/T4 Qwen3 runs), `results/validation_hammer2.0-7b/` (first ad hoc Hammer validation)

To rescore: clone `github.com/IBM/NESTFUL`, add `'Qwen3-4B-Instruct-2507'` to the Hammer branch in `src/scorer.py` (one line), then run against any `output.jsonl` with `--executable_func_dir data_v2/executable_functions`.

## Takeaways for the benchmark work

1. **Reasoning before acting is the single largest effect measured in this entire investigation** — larger than model choice, larger than infra confounds, larger than any prompt-template decision. Same architecture, same weights family, same prompts, same everything except a reasoning phase: Win Rate goes from 0.342 to 0.759. Any benchmark design should treat "was the model allowed to think" as a first-class experimental variable, not an afterthought.
2. **A budget cap silently manufactures a false negative, and it looks exactly like a capability failure until checked.** The 4096-token attempt didn't error — it produced a plausible, lower, wrong number (0.506) that would have been reported as final if not checked against the raw generation text. Any benchmark involving reasoning models needs an explicit truncation check, not just a parse-success check.
3. **The result is metric-dependent, not a flat tie**, for the non-reasoning Instruct comparison — a tie on Full Sequence Match (p=0.10) but a significant Qwen3 win on Win Rate (p≈0.00000). Run a paired significance test on *every* metric being compared, not just one.
4. **Refusal behavior is a first-class benchmark signal, not scorer noise** — concentrated almost entirely in the math domain (~97-99% across all four models and both shot counts) and the primary driver of 1-shot collapse. Track "declined to act" separately from "acted incorrectly."
5. **Domain-stratified reporting is necessary, not optional** — aggregate Full Acc numbers average near-total failure on math ordering with strong success on code; neither number alone describes the benchmark, and this gap is exactly where thinking mode helps most.
6. **Verify determinism, and don't store the only copy of infrastructure access in ephemeral storage.** Two of this round's three failures were pure process gaps (an SSH key lost to a scratchpad wipe, a stale script silently restored from a not-yet-updated backup) — not modeling mistakes. The fix in both cases is the same: write anything you can't regenerate to durable storage the moment it's created, not at the end of a batch.
7. **A "successful" run is not the same as a "correct" run** — the invalid xLAM run from the stale script completed without any error and produced numbers that looked entirely plausible. The only thing that caught it was rereading the deployed code and checking it against what should have been there, not checking whether it ran.
8. **Execution-based Win Rate remains the most defensible metric available in NESTFUL** for the cost-bounded corpus-QA benchmark design — it doesn't penalize valid-but-differently-ordered solutions the way sequence matching does, and it's the metric on which thinking mode's advantage is clearest and most consistent.
9. **Read the logs before writing the prompt fix.** The complaint that triggered v5 ("wrong arguments") wasn't the dominant pattern once actually measured — missing labels and unjustified refusals were. A fix aimed at the wrong diagnosis would have looked reasonable and done little; the fix that worked came from counting the actual failure, not from the plausible-sounding guess. Same discipline that caught the truncation and stale-script issues earlier in this report.
10. **A prompt fix that raises Win Rate can still lower Full Acc, in the same run, on the same model.** Hammer's checklist run is the clearest example (Win Rate +5.4pp, Full Acc −1.0pp) — "the model got better" isn't one number, and reporting only the metric that improved would have been a real, avoidable distortion.
11. **A metric moving the "wrong" direction is a gift, not a nuisance — it's the thing that finds bugs.** The v6 parser-gap bug (three versions old, silently understating every Qwen3-Instruct number) was only found because the checklist experiment produced a surprising regression, which triggered a direct inspection of raw generations instead of accepting the number. A benchmark pipeline should treat every counter-intuitive result as a bug-finding opportunity before treating it as a finding.
12. **"Strip markdown fences" is an easy instruction to get subtly wrong, and it's worth testing on more than one model.** IBM's own official parser's `.replace("```", "")` works for every model that emits bare ` ``` ` fences (Hammer, xLAM, Qwen3-Thinking) and silently breaks for the one that sometimes emits ` ```json `-tagged ones (Qwen3-Instruct) — a one-model blind spot that would have stayed invisible without a model that happened to trigger it.
13. **A prompt fix validated on some models is not thereby validated on all of them.** The checklist helps 3 of 4 models here and measurably hurts the 4th (Qwen3-Instruct: Win Rate −1.6pp, Full Acc −2.5pp, both significant) via a real, traced mechanism (attempting previously-correctly-refused cases, and breaking some previously-correct answers) — not a fluke or a parsing artifact. "Works for Hammer and xLAM" was never evidence it would work for Qwen3-Instruct, and it didn't.
