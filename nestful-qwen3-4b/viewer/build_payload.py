#!/usr/bin/env python3
"""Assemble the single-file viewer's data payload: dataset + all runs + scores.

Tool specs are deduplicated into a global table (4206 unique specs shared across
1861 samples) so the exact prompt can still be rebuilt byte-for-byte in the browser.
F1 intent/slot replicate scorer.py's loop exactly (on grounded call strings).
"""
import base64, gzip, json, os, statistics, sys
from collections import Counter
from scipy.stats import binomtest

HERE = os.path.dirname(os.path.abspath(__file__))
NESTFUL = os.path.join(HERE, "NESTFUL")
sys.path.insert(0, os.path.join(HERE, "shim"))
sys.path.insert(0, os.path.join(NESTFUL, "src"))
# Use score_all.py's fence-tag-aware wrapped parsers (not IBM's raw ones) so
# F1 inputs use the same corrected parsing as every other metric here - see
# score_all.py's _FENCE_TAG comment for why (a ```json-tagged fence, which
# IBM's own .replace("```", "") doesn't fully strip, silently understated
# Qwen3-Instruct's numbers throughout this project until found 2026-09-02).
from score_all import parse_Hammer2_0_7b, parse_xLAM_1b_fc_r, _FENCE_TAG   # noqa: E402
from utils import compute_score_sklearn         # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from run_matched import CHECKLIST   # noqa: E402  (single source of truth - never hand-copy this text into JS)

RUN_ROOT = ("/Users/jakubbares/Library/CloudStorage/GoogleDrive-bares.jakub@gmail.com/"
            "My Drive/CIIRC PhD/FIrst-Effort/nestful-qwen3-4b")

# NESTFUL paper (arXiv:2409.03797v3), Table 1, transcribed by hand. Order per
# model/shot-setting: (f1_func, f1_param, partial, full, win). Params in
# billions, for the leaderboard sort. "key" matches RUNS[i]["model"] where we
# have our own reproduction of that exact model.
PAPER = [
    dict(key="xLAM-1b-fc-r",                 label="xLAM-1b-fc-r",                 params=1,
         one=(0.35,0.16,0.13,0.04,0.03), three=(0.49,0.20,0.15,0.06,0.04)),
    dict(key="xLAM-7b-fc-r",                 label="xLAM-7b-fc-r",                 params=7,
         one=(0.54,0.32,0.18,0.10,0.13), three=(0.49,0.35,0.23,0.18,0.19)),
    dict(key="Hammer2.0-7b",                 label="Hammer2.0-7b",                 params=7,
         one=(0.62,0.42,0.29,0.25,0.33), three=(0.61,0.46,0.31,0.25,0.34)),
    dict(key="granite-3.0-8b-instruct",      label="granite-3.0-8b-instruct",      params=8,
         one=(0.50,0.27,0.15,0.05,0.07), three=(0.52,0.35,0.22,0.15,0.16)),
    dict(key="llama-3-1-8b-instruct",        label="llama-3.1-8b-instruct",        params=8,
         one=(0.58,0.37,0.24,0.18,0.16), three=(0.53,0.38,0.24,0.19,0.16)),
    dict(key="ToolACE-8b",                   label="ToolACE-8b",                   params=8,
         one=(0.51,0.23,0.13,0.00,0.00), three=(0.51,0.27,0.14,0.00,0.00)),
    dict(key="llama-3-2-11b-instruct",       label="llama-3.2-11b-instruct",       params=11,
         one=(0.57,0.42,0.26,0.21,0.18), three=(0.60,0.38,0.26,0.21,0.17)),
    dict(key="Granite-20B-FunctionCalling",  label="Granite-20B-FunctionCalling",  params=20,
         one=(0.60,0.37,0.28,0.24,0.26), three=(0.59,0.35,0.26,0.22,0.24)),
    dict(key="Mixtral-8x7B-Instruct-v0.1",   label="Mixtral-8x7B-Instruct-v0.1",   params=46.7,
         one=(0.29,0.20,0.14,0.12,0.11), three=(0.36,0.25,0.16,0.13,0.13)),
    dict(key="xLAM-8x7b-fc-r",               label="xLAM-8x7b-fc-r",               params=46.7,
         one=(0.44,0.27,0.16,0.01,0.01), three=(0.49,0.29,0.17,0.02,0.03)),
    dict(key="llama-3-1-70b-instruct",       label="llama-3.1-70b-instruct",       params=70,
         one=(0.35,0.18,0.10,0.00,0.01), three=(0.33,0.16,0.10,0.00,0.03)),
    dict(key="llama-3-2-90b-instruct",       label="llama-3.2-90b-instruct",       params=90,
         one=(0.32,0.16,0.09,0.00,0.02), three=(0.29,0.14,0.10,0.00,0.03)),
    dict(key="Mixtral-8x22B-Instruct-v0.1",  label="Mixtral-8x22B-Instruct-v0.1",  params=141,
         one=(0.43,0.30,0.22,0.16,0.10), three=(0.64,0.48,0.29,0.21,0.29)),
    dict(key="xLAM-8x22b-fc-r",              label="xLAM-8x22b-fc-r",              params=141,
         one=(0.59,0.40,0.23,0.15,0.08), three=(0.59,0.40,0.23,0.14,0.11)),
    dict(key="llama-3-1-405b-instruct-fp8",  label="llama-3.1-405b-instruct-fp8",  params=405,
         one=(0.21,0.20,0.13,0.10,0.08), three=(0.26,0.25,0.15,0.11,0.14)),
]
PAPER_METRIC_ORDER = ("f1_func", "f1_param", "partial", "full", "win")

MATCHED = ("EC2 g5.xlarge (A10G 23GB) · bf16 · ctx 8192 · batch 32 · gpu_mem_util 0.90 · T=0.0")
RUNS = [
    dict(key="hammer_3shot", label="Hammer2.0-7b · 3-shot", short="Hammer 3-shot",
         model="Hammer2.0-7b", shots=3, side="baseline", tier="matched",
         path="matched_results/hammer_3shot/output.jsonl", rev="2e267cc2",
         infra=MATCHED + " · vLLM 0.6.3.post1 · transformers 4.46.3"),
    dict(key="hammer_1shot", label="Hammer2.0-7b · 1-shot", short="Hammer 1-shot",
         model="Hammer2.0-7b", shots=1, side="baseline", tier="matched",
         path="matched_results/hammer_1shot/output.jsonl", rev="2e267cc2",
         infra=MATCHED + " · vLLM 0.6.3.post1 · transformers 4.46.3"),
    dict(key="qwen3_3shot", label="Qwen3-4B · 3-shot", short="Qwen3 3-shot",
         model="Qwen3-4B-Instruct-2507", shots=3, side="ours", tier="matched",
         path="matched_results/qwen3_3shot/output.jsonl", rev="cdbee75f",
         infra=MATCHED + " · vLLM 0.8.5 · transformers 4.51.1"),
    dict(key="qwen3_1shot", label="Qwen3-4B · 1-shot", short="Qwen3 1-shot",
         model="Qwen3-4B-Instruct-2507", shots=1, side="ours", tier="matched",
         path="matched_results/qwen3_1shot/output.jsonl", rev="cdbee75f",
         infra=MATCHED + " · vLLM 0.8.5 · transformers 4.51.1"),
    dict(key="qwen3_3shot_sagemaker", label="Qwen3-4B · 3-shot (SageMaker)", short="Qwen3 3-shot SM",
         model="Qwen3-4B-Instruct-2507", shots=3, side="ours", tier="legacy",
         path="results/nestful_3/output.jsonl", rev="(unpinned)",
         infra="SageMaker · NVIDIA T4 · fp16 · vLLM-LMI 0.8.4 · T=0.0 · original 2026-08-21 run"),
    dict(key="qwen3_1shot_sagemaker", label="Qwen3-4B · 1-shot (SageMaker)", short="Qwen3 1-shot SM",
         model="Qwen3-4B-Instruct-2507", shots=1, side="ours", tier="legacy",
         path="results/nestful_1/output.jsonl", rev="(unpinned)",
         infra="SageMaker · NVIDIA T4 · fp16 · vLLM-LMI 0.8.4 · T=0.0 · original 2026-08-21 run"),
    dict(key="hammer_3shot_adhoc", label="Hammer2.0-7b · 3-shot (ad hoc)", short="Hammer 3-shot ad hoc",
         model="Hammer2.0-7b", shots=3, side="baseline", tier="legacy",
         path="results/validation_hammer2.0-7b/output.jsonl", rev="(unpinned)",
         infra="first validation run · unpinned revision · default batch/context · T=0.0"),
    dict(key="xlam_3shot", label="xLAM-7b-fc-r · 3-shot", short="xLAM 3-shot",
         model="xLAM-7b-fc-r", shots=3, side="baseline", tier="matched",
         path="matched_results/xlam_3shot/output.jsonl", rev="(unpinned, ungated)",
         infra=MATCHED.replace("ctx 8192", "ctx 4096 (model's own max_position_embeddings)")
               + " · vLLM 0.8.5 · transformers 4.51.1 · own {\"tool_calls\":[...]} template, not Hammer's",
         parser="xlam"),
    dict(key="xlam_1shot", label="xLAM-7b-fc-r · 1-shot", short="xLAM 1-shot",
         model="xLAM-7b-fc-r", shots=1, side="baseline", tier="matched",
         path="matched_results/xlam_1shot/output.jsonl", rev="(unpinned, ungated)",
         infra=MATCHED.replace("ctx 8192", "ctx 4096 (model's own max_position_embeddings)")
               + " · vLLM 0.8.5 · transformers 4.51.1 · own {\"tool_calls\":[...]} template, not Hammer's",
         parser="xlam"),
    dict(key="qwen3thinking_3shot", label="Qwen3-4B-Thinking-2507 · 3-shot", short="Thinking 3-shot",
         model="Qwen3-4B-Thinking-2507", shots=3, side="ours", tier="matched",
         path="matched_results/qwen3thinking_3shot/output.jsonl", rev="768f209d",
         infra=MATCHED.replace("ctx 8192", "ctx 20000").replace("batch 32", "batch 16")
               + " · vLLM 0.8.5 · transformers 4.51.1 · max_tokens 16000 · <think> stripped before scoring"),
    dict(key="qwen3thinking_1shot", label="Qwen3-4B-Thinking-2507 · 1-shot", short="Thinking 1-shot",
         model="Qwen3-4B-Thinking-2507", shots=1, side="ours", tier="matched",
         path="matched_results/qwen3thinking_1shot/output.jsonl", rev="768f209d",
         infra=MATCHED.replace("ctx 8192", "ctx 20000").replace("batch 32", "batch 16")
               + " · vLLM 0.8.5 · transformers 4.51.1 · max_tokens 16000 · <think> stripped before scoring"),
    # Evidence-based output checklist (see chat record 2026-08-31/09-01): a block of
    # 7 verification items - labels present, valid JSON, quoted references, computed
    # values only, exact function names, argument types, never refuse - injected
    # before [BEGIN OF QUERY]. Same infra/revision as the baseline "matched" runs
    # above, so baseline-vs-checklist is a clean paired comparison; kept in its own
    # tier so it doesn't get folded into the main matched-infra model-vs-model table.
    dict(key="hammer_3shot_checklist", label="Hammer2.0-7b · 3-shot + checklist", short="Hammer 3-shot +checklist",
         model="Hammer2.0-7b", shots=3, side="baseline", tier="checklist",
         path="matched_results/hammer_3shot_checklist/output.jsonl", rev="2e267cc2",
         infra=MATCHED + " · vLLM 0.6.3.post1 · transformers 4.46.3 · +output checklist prompt"),
    dict(key="xlam_3shot_checklist", label="xLAM-7b-fc-r · 3-shot + checklist", short="xLAM 3-shot +checklist",
         model="xLAM-7b-fc-r", shots=3, side="baseline", tier="checklist",
         path="matched_results/xlam_3shot_checklist/output.jsonl", rev="(unpinned, ungated)",
         infra=MATCHED.replace("ctx 8192", "ctx 4096 (model's own max_position_embeddings)")
               + " · vLLM 0.8.5 · transformers 4.51.1 · own {\"tool_calls\":[...]} template, not Hammer's"
               + " · max_tokens 2000 (raised from 1000) · +output checklist prompt",
         parser="xlam"),
    dict(key="qwen3_3shot_checklist", label="Qwen3-4B-Instruct-2507 · 3-shot + checklist", short="Qwen3-Instruct 3-shot +checklist",
         model="Qwen3-4B-Instruct-2507", shots=3, side="ours", tier="checklist",
         path="matched_results/qwen3_3shot_checklist/output.jsonl", rev="cdbee75f",
         infra=MATCHED + " · vLLM 0.8.5 · transformers 4.51.1 · +output checklist prompt"),
    dict(key="qwen3thinking_3shot_checklist", label="Qwen3-4B-Thinking-2507 · 3-shot + checklist", short="Thinking 3-shot +checklist",
         model="Qwen3-4B-Thinking-2507", shots=3, side="ours", tier="checklist",
         path="matched_results/qwen3thinking_3shot_checklist/output.jsonl", rev="768f209d",
         infra=MATCHED.replace("ctx 8192", "ctx 20000").replace("batch 32", "batch 16")
               + " · vLLM 0.8.5 · transformers 4.51.1 · max_tokens 16000 · <think> stripped before scoring"
               + " · +output checklist prompt"),
]

# Pairs the dashboard's checklist card diffs baseline -> checklist for.
CHECKLIST_PAIRS = [
    ("hammer_3shot", "hammer_3shot_checklist"),
    ("xlam_3shot", "xlam_3shot_checklist"),
    ("qwen3_3shot", "qwen3_3shot_checklist"),
    ("qwen3thinking_3shot", "qwen3thinking_3shot_checklist"),
]

# ------------------------------------------------------------------ dataset --
gold = [json.loads(l) for l in open(os.path.join(NESTFUL, "data_v2", "nestful_data.jsonl"))]
EXEC_DIR = os.path.join(NESTFUL, "data_v2", "executable_functions")

BASIC = set()
for line in open(os.path.join(EXEC_DIR, "basic_functions.py")):
    if line.startswith("def "):
        s = line.strip().replace("def ", "")
        BASIC.add(s[:s.index("(")])

# REPORT.md v3 used this hand-written list; it omits 16 functions that really do
# live in basic_functions.py, so 26 MathQA samples were counted as "code" there.
REPORT_MATH = {"add","subtract","multiply","divide","inverse","square","cube","sqrt","power",
    "factorial","gcd","lcm","percent","average","circle_area","circle_perimeter","rectangle_area",
    "rectangle_perimeter","square_area","square_perimeter","triangle_area","volume_cube",
    "volume_sphere","volume_cylinder","surface_area_cube","surface_area_sphere","negate","floor",
    "ceil","log","exp","choose","permutation"}

spec_index, spec_table = {}, []
def spec_id(tool):
    s = json.dumps(tool)
    if s not in spec_index:
        spec_index[s] = len(spec_table)
        spec_table.append(s)
    return spec_index[s]

samples = []
for g in gold:
    names = {c["name"] for c in g["output"]}
    nested = sum(1 for c in g["output"] for v in c["arguments"].values()
                 if isinstance(v, str) and v.startswith("$"))
    samples.append({
        "id": g["sample_id"],
        "q": g["input"],
        "gold": g["output"],
        "ga": g["gold_answer"],
        "ts": [spec_id(t) for t in g["tools"]],
        "d": "math" if names <= BASIC else "code",
        "dr": "math" if names <= REPORT_MATH else "code",
        "nc": len(g["output"]),
        "nn": nested,
    })

for s, g in zip(samples, gold):
    assert "[" + ", ".join(spec_table[i] for i in s["ts"]) + "]" == json.dumps(g["tools"]), s["id"]
print(f"samples {len(samples)} | math {sum(1 for s in samples if s['d']=='math')} "
      f"| code {sum(1 for s in samples if s['d']=='code')} | tool specs {len(spec_table)}")
print(f"REPORT.md's split would be math {sum(1 for s in samples if s['dr']=='math')} "
      f"/ code {sum(1 for s in samples if s['dr']=='code')} "
      f"({sum(1 for s in samples if s['d']!=s['dr'])} samples reclassified)")

# --------------------------------------------------- official F1 (scorer.py) --
PARSERS = {"hammer": parse_Hammer2_0_7b, "xlam": parse_xLAM_1b_fc_r}

def scorer_f1_inputs(path, parser_key="hammer"):
    """scorer.py's intent/slot accumulation, verbatim, over grounded call strings."""
    parser = PARSERS[parser_key]
    gi, pi, gs, ps = [], [], [], []
    for line in open(path):
        item = json.loads(line)
        pred_fc, gold_fc, _, _, _, _ = parser(dict(item), 0)
        pan, gan = [], []
        for f in pred_fc:
            if not f: continue
            try:
                if f.strip() == '{"name": "dummy", "arguments": {}}': continue
                pan.append(str(json.loads(f.replace('<|endoftext|>', '').strip())['name']))
            except Exception: pass
        for f in gold_fc:
            if not f: continue
            try:
                gan.append(str(json.loads(f.replace('<|endoftext|>', '').strip())['name']))
            except Exception: pass
        gi.append(gan); pi.append(pan)
        pmap, gmap = {}, {}
        for f in pred_fc:
            if f.strip() == '{"name": "dummy", "arguments": {}}': continue
            try:
                if not f: continue
                f = json.loads(f.replace('<|endoftext|>', '').strip())
                if type(f) != dict or 'name' not in f: raise Exception
                pmap[f['name']] = []
                for arg, val in f['arguments'].items():
                    if type(val) == str and val.startswith("$") and not val.endswith("$"): val = val + "$"
                    pmap[f['name']].append(f'{arg} = {val}')
            except Exception: pass
        for f in gold_fc:
            if not f: continue
            try:
                f = json.loads(f.replace('<|endoftext|>', '').strip())
                gmap[f['name']] = [f'{arg} = {val}' for arg, val in f['arguments'].items()]
            except Exception: pass
        for key in set(pmap) | set(gmap):
            ps.append(pmap.get(key, [])); gs.append(gmap.get(key, []))
    _, _, f1i = compute_score_sklearn(gi, pi)
    _, _, f1s = compute_score_sklearn(gs, ps)
    return round(f1i, 3), round(f1s, 3)

# ------------------------------------------------------------------ diagnosis --
WHY = {
 "exact":        "Function names and arguments match gold exactly, in order. Counts for Full Sequence Match.",
 "alt_win":      "A different call chain from gold, but executing it reaches the correct final answer. Counts for Win Rate, not for Full Match — the case strict sequence matching penalises unfairly.",
 "args":         "Right functions in the right order; at least one argument value differs from gold, and the executed answer is wrong.",
 "order":        "Same multiset of functions as gold but in a different order, and the answer came out wrong.",
 "partial_funcs":"Some of gold's functions were used, others were swapped out or dropped.",
 "wrong_funcs":  "An entirely different set of functions than gold.",
 "exec_error":   "The predicted chain parsed as JSON but could not be executed to completion — see the execution error on the sample.",
 "refusal":      "Emitted `[]`, declining to call any function. The prompt's own instruction #2 explicitly invites this: \"If none of the function can be used, point it out and refuse to answer.\"",
 "unparsable":   "The generation was not JSON the official Hammer parser could read — markdown fences with a language tag, surrounding prose, or truncation at the 1000-token cap.",
}
DIAG_ORDER = ["exact", "alt_win", "args", "order", "partial_funcs", "wrong_funcs",
              "exec_error", "refusal", "unparsable"]
DIAG_LABEL = {"exact": "Exact match", "alt_win": "Alternate trajectory win",
              "args": "Wrong arguments", "order": "Wrong order", "partial_funcs": "Partly wrong functions",
              "wrong_funcs": "Wrong functions", "exec_error": "Execution failed",
              "refusal": "Refusal ([])", "unparsable": "Unparsable output"}

def diagnose(r, gold_names):
    if r["rf"]: return "refusal"
    if r["pe"]: return "unparsable"
    if r["fm"]: return "exact"
    if r["wn"]: return "alt_win"
    if r["ee"]: return "exec_error"
    if r["pn"] == gold_names: return "args"
    if sorted(r["pn"], key=str) == sorted(gold_names, key=str): return "order"
    if set(r["pn"]) & set(gold_names): return "partial_funcs"
    return "wrong_funcs"

# ----------------------------------------------------------------- run scores --
scored = json.load(open(os.path.join(HERE, "scored.json")))
runs_out = {}
for run in RUNS:
    rows = scored[run["key"]]
    idx = {r["id"]: r for r in rows}
    per = []
    for s in samples:
        r = idx[s["id"]]
        gold_names = [c["name"] for c in s["gold"]]
        row = {
            "g": r["gen"], "pn": r["pn"], "pa": r["pa"], "ee": r["ee"],
            "pt": r["pt"], "fm": int(r["fm"]), "wn": int(r["wn"]),
            "rf": int(r["rf"]), "pe": int(r["pe"]), "ns": int(r["ns"]),
            "c": diagnose(r, gold_names),
        }
        # Only store the raw (pre-<think>-strip) text when it actually differs
        # from the scored text - keeps the 9 non-reasoning runs from carrying
        # a duplicate copy of every generation.
        if r["genraw"] != r["gen"]:
            row["gr"] = r["genraw"]
        per.append(row)
    f1_func, f1_param = scorer_f1_inputs(os.path.join(RUN_ROOT, run["path"]), run.get("parser", "hammer"))
    n = len(per)
    mean = lambda xs: round(statistics.mean(xs), 4) if xs else 0.0
    runs_out[run["key"]] = {
        "meta": {k: run[k] for k in ("key", "label", "short", "model", "shots", "side", "tier", "infra", "rev")},
        "agg": {
            "n": n, "f1_func": f1_func, "f1_param": f1_param,
            "partial": mean([p["pt"] for p in per]),
            "full": mean([p["fm"] for p in per]),
            "win": mean([p["wn"] for p in per]),
            "refusal": mean([p["rf"] for p in per]),
            "parse_err": mean([p["pe"] for p in per]),
            "nameseq": mean([p["ns"] for p in per]),
            "diag": dict(Counter(p["c"] for p in per)),
            "by_domain": {dom: {
                "n": sum(1 for s in samples if s["d"] == dom),
                "full": mean([p["fm"] for s, p in zip(samples, per) if s["d"] == dom]),
                "win": mean([p["wn"] for s, p in zip(samples, per) if s["d"] == dom]),
                "nameseq": mean([p["ns"] for s, p in zip(samples, per) if s["d"] == dom]),
                "refusal": mean([p["rf"] for s, p in zip(samples, per) if s["d"] == dom]),
                "partial": mean([p["pt"] for s, p in zip(samples, per) if s["d"] == dom]),
            } for dom in ("math", "code")},
        },
        "rows": per,
    }
    a = runs_out[run["key"]]["agg"]
    print(f"{run['key']:24s} f1_func={a['f1_func']} f1_param={a['f1_param']} "
          f"partial={a['partial']} full={a['full']} win={a['win']} refusal={a['refusal']}")

# --------------------------------------------------------- checklist experiment --
# Evidence-based fix (chat record 2026-08-31/09-01): review of raw generations
# found two real, counted failure modes - missing "label" fields (breaks any
# later reference to that call) and refusals ("[]") on samples the tools can
# always solve - plus xLAM specifically truncating under its 1000-token cap.
# This block pairs each baseline run against its +checklist counterpart on the
# SAME 1861 samples (same order, since both built from the same `samples`
# list) and reports the delta plus a paired McNemar exact test, so the
# dashboard shows real before/after evidence rather than an assertion.
def mcnemar_p(base_rows, ck_rows, field):
    b = sum(1 for x, y in zip(base_rows, ck_rows) if x[field] and not y[field])
    c = sum(1 for x, y in zip(base_rows, ck_rows) if not x[field] and y[field])
    if b + c == 0:
        return 1.0, b, c
    return round(binomtest(min(b, c), b + c, 0.5).pvalue, 6), b, c


def missing_label_rate(path, parser_key):
    n_missing, n = 0, 0
    for line in open(os.path.join(RUN_ROOT, path)):
        item = json.loads(line)
        n += 1
        raw = _FENCE_TAG.sub("", item["generated_text"]).strip()
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        calls = parsed.get("tool_calls") if parser_key == "xlam" and isinstance(parsed, dict) else parsed
        if isinstance(calls, list) and calls:
            if any(isinstance(c, dict) and "label" not in c for c in calls):
                n_missing += 1
    return round(n_missing / n, 4) if n else 0.0


CHECKLIST_EXPERIMENT = []
for base_key, ck_key in CHECKLIST_PAIRS:
    base_run = next(r for r in RUNS if r["key"] == base_key)
    ck_run = next(r for r in RUNS if r["key"] == ck_key)
    base_rows, ck_rows = runs_out[base_key]["rows"], runs_out[ck_key]["rows"]
    base_agg, ck_agg = runs_out[base_key]["agg"], runs_out[ck_key]["agg"]
    metrics = {}
    for field, name in (("wn", "win"), ("fm", "full"), ("rf", "refusal")):
        p, b, c = mcnemar_p(base_rows, ck_rows, field)
        metrics[name] = {"base": base_agg[name], "checklist": ck_agg[name],
                          "delta": round(ck_agg[name] - base_agg[name], 4),
                          "p": p, "discordant_base_only": b, "discordant_checklist_only": c}
    CHECKLIST_EXPERIMENT.append({
        "model": base_run["model"],
        "base_key": base_key, "checklist_key": ck_key,
        "n": base_agg["n"],
        "metrics": metrics,
        "partial": {"base": base_agg["partial"], "checklist": ck_agg["partial"],
                    "delta": round(ck_agg["partial"] - base_agg["partial"], 4)},
        "parse_err": {"base": base_agg["parse_err"], "checklist": ck_agg["parse_err"],
                      "delta": round(ck_agg["parse_err"] - base_agg["parse_err"], 4)},
        "missing_label": {"base": missing_label_rate(base_run["path"], base_run.get("parser", "hammer")),
                           "checklist": missing_label_rate(ck_run["path"], ck_run.get("parser", "hammer"))},
    })
    print(f"checklist {base_key} -> {ck_key}: "
          f"win {metrics['win']['base']}->{metrics['win']['checklist']} (p={metrics['win']['p']})  "
          f"refusal {metrics['refusal']['base']}->{metrics['refusal']['checklist']} (p={metrics['refusal']['p']})")

# ICL blocks, pre-rendered with Python's json.dumps spacing so the browser can
# rebuild any prompt byte-for-byte by pure concatenation.
ICL = json.load(open(os.path.join(NESTFUL, "src", "icl_examples.json")))
def icl_str(n):
    out = ""
    for i, ex in enumerate(ICL[:n], 1):
        out += f"\n#Example-{i}\nInput: {ex['input']}\nOutput: {json.dumps(ex['output'])}\n"
    return out
ICL_STR = {str(n): icl_str(n) for n in (1, 3)}

# xLAM-7b-fc-r wraps each ICL example's output as {"tool_calls": [...]} instead
# of a bare list (output_parsers.py get_icl_str's xLAM-specific branch).
def icl_str_xlam(n):
    out = ""
    for i, ex in enumerate(ICL[:n], 1):
        out += f'\n#Example-{i}\nInput: {ex["input"]}\nOutput: {{"tool_calls": {json.dumps(ex["output"])} }}\n'
    return out
ICL_STR_XLAM = {str(n): icl_str_xlam(n) for n in (1, 3)}

det = {}
for run in RUNS:
    p = os.path.join(RUN_ROOT, os.path.dirname(run["path"]), "determinism_check.json")
    if os.path.exists(p):
        det[run["key"]] = json.load(open(p))

payload = {
    "samples": samples, "specs": spec_table, "runs": runs_out,
    "run_order": [r["key"] for r in RUNS],
    "prompts": {"templates": json.load(open(os.path.join(NESTFUL, "src", "PROMPTS.json"))),
                "icl": ICL, "icl_str": ICL_STR, "icl_str_xlam": ICL_STR_XLAM,
                "checklist": CHECKLIST,
                "template_used": "Hammer2.0-7b"},
    "paper": {"models": PAPER, "metric_order": PAPER_METRIC_ORDER,
              "source": "arXiv:2409.03797v3, Table 1 (hand-transcribed from the figure)"},
    "determinism": det,
    "diag_order": DIAG_ORDER, "diag_label": DIAG_LABEL, "why": WHY,
    "checklist_experiment": CHECKLIST_EXPERIMENT,
}
raw = json.dumps(payload, separators=(",", ":")).encode()
comp = gzip.compress(raw, 9)
b64 = base64.b64encode(comp).decode()
open(os.path.join(HERE, "payload.b64"), "w").write(b64)
print(f"payload raw {len(raw)/1e6:.2f} MB -> gzip {len(comp)/1e6:.2f} MB -> base64 {len(b64)/1e6:.2f} MB")
