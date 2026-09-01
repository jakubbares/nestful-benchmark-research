#!/usr/bin/env python
"""Full analysis pass over matched-infra Hammer/Qwen3 results:
  - domain split (math vs code) for both models, both shot-counts
  - refusal-pattern breakdown by domain
  - paired McNemar test on per-example Full-Sequence-Match (name+arg exact)
    between Hammer2.0-7b and Qwen3-4B, both 3-shot, matched infra
Reads scorer.py's own parser for the win/full-match booleans so results
match the official scorer's definitions exactly.
"""
import json, sys, os
sys.path.insert(0, "NESTFUL_full/src")
from output_parsers import parse_Hammer2_0_7b
from scorer import post_process_api_with_args
from sklearn.metrics import accuracy_score

MATH_FUNCS = {"add","subtract","multiply","divide","inverse","square","cube","sqrt","power",
              "factorial","gcd","lcm","percent","average","circle_area","circle_perimeter",
              "rectangle_area","rectangle_perimeter","square_area","square_perimeter",
              "triangle_area","volume_cube","volume_sphere","volume_cylinder","surface_area_cube",
              "surface_area_sphere","negate","floor","ceil","log","exp","choose","permutation"}

gold_data = {d["sample_id"]: d for d in (json.loads(l) for l in open("NESTFUL/data_v2/nestful_data.jsonl"))}


def domain(sid):
    names = {c["name"] for c in gold_data[sid]["output"]}
    return "math" if names <= MATH_FUNCS else "code"


def full_match_per_sample(path, model_name="Hammer2.0-7b"):
    """Replicates scorer.py's per-example accuracy_combined==1 check exactly."""
    recs = [json.loads(l) for l in open(path)]
    out = {}
    for item in recs:
        pred_fc, gold_fc, pred_dl, gold_dl, _, _ = parse_Hammer2_0_7b(dict(item), 0)
        api_gold, api_pred = [], []
        for f in gold_fc:
            f = json.loads(f.replace("<|endoftext|>", "").strip())
            args = ", ".join(sorted(f"{k} = {v}" for k, v in f["arguments"].items()))
            api_gold.append(f"{f['name']}({args})")
        for f in pred_fc:
            try:
                f = json.loads(f.replace("<|endoftext|>", "").strip())
                args = ", ".join(sorted(f"{k} = {v}" for k, v in f.get("arguments", {}).items()))
                api_pred.append(f"{f['name']}({args})")
            except Exception:
                continue
        api_gold, api_pred = post_process_api_with_args(api_gold, api_pred)
        try:
            acc = accuracy_score(api_gold, api_pred)
        except Exception:
            acc = 0.0
        out[item["sample_id"]] = (acc == 1.0)
    return out


def domain_report(path, label):
    recs = [json.loads(l) for l in open(path)]
    buckets = {"math": [], "code": []}
    for r in recs:
        d = domain(r["sample_id"])
        seq_match = False
        try:
            pred = json.loads(r["generated_text"].replace("```", "").strip())
            if isinstance(pred, list) and pred:
                pnames = [c.get("name") for c in pred]
                gnames = [c.get("name") for c in json.loads(r["output"])]
                seq_match = (pnames == gnames)
        except Exception:
            pass
        buckets[d].append(seq_match)
    print(f"--- {label} ---")
    for k, v in buckets.items():
        print(f"  {k}: n={len(v)}, exact function-NAME-sequence match={sum(v)/len(v):.1%}")


def refusal_report(path, label):
    recs = [json.loads(l) for l in open(path)]
    refusals = []
    for r in recs:
        g = r["generated_text"].replace("```", "").strip()
        try:
            c = json.loads(g)
            if isinstance(c, list) and len(c) == 0:
                refusals.append(r)
        except Exception:
            pass
    dom = [domain(r["sample_id"]) for r in refusals]
    print(f"--- {label} refusals ---")
    print(f"  {len(refusals)}/{len(recs)} ({len(refusals)/len(recs):.1%}) | "
          f"math={dom.count('math')} code={dom.count('code')}")


if __name__ == "__main__":
    print("=" * 60)
    domain_report("matched_results/hammer_3shot/output.jsonl", "Hammer2.0-7b 3-shot")
    domain_report("matched_results/hammer_1shot/output.jsonl", "Hammer2.0-7b 1-shot")
    if os.path.exists("matched_results/qwen3_3shot/output.jsonl"):
        domain_report("matched_results/qwen3_3shot/output.jsonl", "Qwen3-4B 3-shot")
        domain_report("matched_results/qwen3_1shot/output.jsonl", "Qwen3-4B 1-shot")

    print("=" * 60)
    refusal_report("matched_results/hammer_3shot/output.jsonl", "Hammer2.0-7b 3-shot")
    refusal_report("matched_results/hammer_1shot/output.jsonl", "Hammer2.0-7b 1-shot")
    if os.path.exists("matched_results/qwen3_3shot/output.jsonl"):
        refusal_report("matched_results/qwen3_3shot/output.jsonl", "Qwen3-4B 3-shot")
        refusal_report("matched_results/qwen3_1shot/output.jsonl", "Qwen3-4B 1-shot")

    if os.path.exists("matched_results/qwen3_3shot/output.jsonl"):
        print("=" * 60)
        print("McNemar's test: Hammer2.0-7b vs Qwen3-4B, 3-shot, Full Sequence Match")
        h = full_match_per_sample("matched_results/hammer_3shot/output.jsonl")
        q = full_match_per_sample("matched_results/qwen3_3shot/output.jsonl")
        ids = sorted(set(h) & set(q))
        b = sum(1 for i in ids if h[i] and not q[i])   # Hammer right, Qwen3 wrong
        c = sum(1 for i in ids if not h[i] and q[i])   # Qwen3 right, Hammer wrong
        both_right = sum(1 for i in ids if h[i] and q[i])
        both_wrong = sum(1 for i in ids if not h[i] and not q[i])
        print(f"  n paired examples: {len(ids)}")
        print(f"  both right: {both_right} | both wrong: {both_wrong} | "
              f"Hammer-only-right: {b} | Qwen3-only-right: {c}")
        from scipy.stats import binomtest
        if b + c > 0:
            res = binomtest(min(b, c), b + c, 0.5)
            print(f"  McNemar exact (binomial on discordant pairs): p = {res.pvalue:.4f}")
            print(f"  {'NOT significant at p<0.05 -- consistent with a tie' if res.pvalue >= 0.05 else 'SIGNIFICANT difference'}")
        else:
            print("  no discordant pairs")
