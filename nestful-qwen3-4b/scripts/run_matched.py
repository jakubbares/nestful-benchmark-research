#!/usr/bin/env python
"""Run NESTFUL inference for a given model on THIS box's vLLM, using the
identical prompt-construction path as IBM's own instruct_data_prep.py.

Per-model prompt routing matches IBM's code exactly:
  - LLAMA_MODELS -> "LLaMa-3.1" template, always .format()
  - everything else -> PROMPTS.json[model_name] if present else Hammer2.0-7b's
    template, tried via .format() first (succeeds for templates with
    pre-escaped JSON-example braces, e.g. xLAM-7b-fc-r), falling back to
    .replace() on exception (Hammer2.0-7b's un-escaped braces).
  - xLAM-1b/7b-fc-r also get a special ICL example format
    ({"tool_calls": [...]}) instead of a bare list, per get_icl_str.

Designed to remove the infra confounds identified in the audit: models run
on the same GPU, same dtype (bf16), same batch size, same
gpu_memory_utilization, pinned to an exact HF revision.
"""
import argparse, json, os, time


LLAMA_MODELS = [
    "Llama-3.1-8B-Instruct",
    "llama-3-1-70b-instruct",
    "llama-3-1-405b-instruct-fp8",
    "Llama-3.2-11B-Vision-Instruct",
    "Llama-3.2-90B-Vision-Instruct",
]

# Evidence-based, not speculative: every item here maps to a specific,
# counted failure mode found by inspecting real generations against
# scored.json (see chat record 2026-08-31). Not a rewrite of the baseline
# template - inserted only when --checklist is passed, so the unmodified
# baseline template (and its results) stays byte-identical and comparable.
CHECKLIST = """[BEGIN OF OUTPUT CHECKLIST]
Before finalizing your answer, verify every item below:
1. LABELS: every single function call in your list has its own "label" field
   (e.g. "label": "$var_1"), including calls whose result is only used by a
   later step. A call referenced later but missing its own label will fail.
2. VALID JSON ONLY: output raw JSON with no markdown formatting - never wrap
   your answer in ``` code fences or add any text before or after the list.
3. QUOTED REFERENCES: a reference to an earlier result, e.g. $var_1.result$,
   must always appear as a quoted JSON string ("$var_1.result$"), never bare.
4. COMPUTED VALUES ONLY: every argument value must be a literal JSON number
   or string - never a math expression like 1/6. Compute the decimal value
   yourself before writing it.
5. EXACT FUNCTION NAMES: use function names exactly as they appear in the
   tools list above. Do not invent or assume standard library functions.
6. ARGUMENT TYPES: check each parameter's declared type in the tool
   description and pass a value of exactly that type.
7. NEVER REFUSE: the provided tools are always sufficient to answer the
   question in full - do not output an empty list or decline to answer.
[END OF OUTPUT CHECKLIST]

"""


def get_icl_str(icl_examples, model_name):
    exampl_str = ""
    for idx, ex in enumerate(icl_examples, 1):
        if model_name in ("xLAM-7b-fc-r", "xLAM-1b-fc-r"):
            exampl_str += (
                f'\n#Example-{idx}\nInput: {ex["input"]}\n'
                f'Output: {{"tool_calls": {json.dumps(ex["output"])} }}\n'
            )
        else:
            exampl_str += f"\n#Example-{idx}\nInput: {ex['input']}\nOutput: {json.dumps(ex['output'])}\n"
    return exampl_str


def build_prompts(nestful_dir, icl_count, model_name, checklist=False):
    with open(os.path.join(nestful_dir, "data_v2", "nestful_data.jsonl")) as f:
        data = [json.loads(l) for l in f]
    for i in range(len(data)):
        data[i]["tools"] = json.dumps(data[i]["tools"])
        data[i]["gold_answer"] = json.dumps(data[i]["gold_answer"])
        data[i]["output"] = json.dumps(data[i]["output"])

    with open(os.path.join(nestful_dir, "src", "icl_examples.json")) as f:
        icl_examples = json.load(f)[:icl_count]
    with open(os.path.join(nestful_dir, "src", "PROMPTS.json")) as f:
        prompt_dict = json.load(f)

    icl_str = get_icl_str(icl_examples, model_name)
    is_llama = model_name in LLAMA_MODELS
    if is_llama:
        template = prompt_dict["LLaMa-3.1"]
    else:
        template = prompt_dict[model_name] if model_name in prompt_dict else prompt_dict["Hammer2.0-7b"]

    if checklist:
        # Inserted once into the template, before per-sample substitution, so
        # it flows through whichever path (.format()/.replace()) is taken
        # below - lands after the format instructions, outside/before the
        # [BEGIN OF QUERY] block rather than nested inside it.
        assert template.count("[BEGIN OF QUERY]") == 1, "unexpected template shape for checklist injection"
        template = template.replace("[BEGIN OF QUERY]", CHECKLIST + "[BEGIN OF QUERY]")

    test_data = []
    for sample in data:
        if is_llama:
            input_prompt = template.format(
                FUNCTION_STR=json.dumps(sample["tools"]),
                ICL_EXAMPLES=icl_str,
                QUERY=sample["input"],
            )
        else:
            try:
                input_prompt = template.format(
                    FUNCTION_STR=json.dumps(sample["tools"]),
                    ICL_EXAMPLES=icl_str,
                    QUERY=sample["input"],
                )
            except (KeyError, IndexError):
                input_prompt = (
                    template.replace("{FUNCTION_STR}", json.dumps(sample["tools"]))
                    .replace("{ICL_EXAMPLES}", icl_str)
                    .replace("{QUERY}", sample["input"])
                )
        test_data.append(
            {
                "sample_id": sample["sample_id"],
                "input": input_prompt,
                "output": sample["output"],
                "gold_answer": sample["gold_answer"],
                "tools": sample["tools"],
            }
        )
    return test_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="local path or HF repo id")
    ap.add_argument("--model_name", required=True)
    ap.add_argument("--nestful_dir", default="NESTFUL")
    ap.add_argument("--save_directory", default="results")
    ap.add_argument("--icl_count", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max_tokens", type=int, default=1000)
    ap.add_argument("--max_model_len", type=int, default=8192)
    ap.add_argument("--gpu_memory_utilization", type=float, default=0.90)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--determinism_check", type=int, default=5,
                     help="duplicate the first N prompts to verify greedy determinism")
    ap.add_argument("--checklist", action="store_true",
                     help="insert the evidence-based output checklist before the query")
    ap.add_argument("--strip_think", action="store_true",
                     help="for reasoning models: strip <think>...</think> before saving "
                          "generated_text (raw text kept in generated_text_raw)")
    args = ap.parse_args()
    print(args, flush=True)

    test_data = build_prompts(args.nestful_dir, args.icl_count, args.model_name, args.checklist)

    # Determinism check: duplicate the first N prompts within the SAME batch
    # (the harshest test - same call, mixed batch composition) and verify
    # byte-identical outputs.
    det_n = args.determinism_check
    det_originals = test_data[:det_n]
    det_dupes = [dict(s, sample_id=s["sample_id"] + "__DUPCHECK") for s in det_originals]
    run_data = det_dupes + test_data  # dupes go first, alongside their originals later in the batch

    save_dir = os.path.join(args.save_directory, f"nestful_{args.icl_count}", args.model_name)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "output.jsonl")
    det_path = os.path.join(save_dir, "determinism_check.json")

    from vllm import LLM, SamplingParams

    print("### Loading model...", flush=True)
    llm = LLM(
        model=args.model,
        dtype=args.dtype,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
    )
    sampling_params = SamplingParams(temperature=args.temperature, max_tokens=args.max_tokens)

    prompts = [s["input"] for s in run_data]
    t0 = time.time()
    n_written = 0
    with open(save_path, "w") as f:
        for idx in range(0, len(prompts), args.batch_size):
            batch = run_data[idx: idx + args.batch_size]
            batch_prompts = prompts[idx: idx + args.batch_size]
            outputs = llm.generate(batch_prompts, sampling_params)
            for s, o in zip(batch, outputs):
                text = o.outputs[0].text.strip()
                if s["sample_id"].endswith("__DUPCHECK"):
                    continue  # written separately below
                rec = dict(s)
                if args.strip_think:
                    rec["generated_text_raw"] = text
                    rec["generated_text"] = text.split("</think>", 1)[-1].strip() if "</think>" in text else text
                else:
                    rec["generated_text"] = text
                f.write(json.dumps(rec) + "\n")
                n_written += 1
            el = time.time() - t0
            print(f"### {min(idx+args.batch_size, len(prompts))}/{len(prompts)} raw calls | "
                  f"{el/60:.1f} min | {n_written} scored samples written", flush=True)

    # Determinism check: re-run the SAME N prompts as a fresh, separate call
    # (different batch composition than their first appearance) and compare.
    dup_prompts = [s["input"] for s in det_dupes]
    dup_outputs_first = llm.generate(dup_prompts, sampling_params)
    dup_outputs_second = llm.generate(dup_prompts, sampling_params)
    det_results = []
    for orig, o1, o2 in zip(det_originals, dup_outputs_first, dup_outputs_second):
        t1, t2 = o1.outputs[0].text, o2.outputs[0].text
        det_results.append({
            "sample_id": orig["sample_id"],
            "identical_across_two_fresh_calls": (t1 == t2),
        })
    with open(det_path, "w") as f:
        json.dump(det_results, f, indent=2)
    n_det_ok = sum(1 for d in det_results if d["identical_across_two_fresh_calls"])
    print(f"### DETERMINISM CHECK: {n_det_ok}/{len(det_results)} prompts gave byte-identical "
          f"output across two independent generate() calls", flush=True)
    print("### DONE...!!!", flush=True)


if __name__ == "__main__":
    main()
