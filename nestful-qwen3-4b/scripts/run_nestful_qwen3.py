#!/usr/bin/env python
"""NESTFUL inference for Qwen/Qwen3-4B-Instruct-2507 on Apple Silicon via MLX.

Replicates IBM's official protocol (github.com/IBM/NESTFUL, src/eval.py +
src/instruct_data_prep.py) exactly:
  - Hammer2.0-7b prompt template from src/PROMPTS.json (Hammer2.0 is the
    Qwen-family ChatML model in the paper; Qwen3 uses the same ChatML format).
  - The generic get_icl_str() branch for ICL examples.
  - The .replace() formatting path (the .format() path raises on the Hammer
    template's literal braces, exactly as in the original code), including
    json.dumps() applied to the already-stringified tools list.
  - temperature 0.0, max_tokens 1000 (eval.py defaults used for the paper).

Only the runtime differs: mlx_lm.batch_generate (greedy) instead of vLLM,
because the paper's vLLM setup needs CUDA. Weights are the unquantized bf16
conversion (mlx-community/Qwen3-4B-Instruct-2507-bf16) of the original model.
"""
import argparse, json, os, time

NESTFUL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NESTFUL")


def get_icl_str(icl_examples):
    # instruct_data_prep.get_icl_str, generic (else) branch
    exampl_str = ""
    for idx, ex in enumerate(icl_examples, 1):
        exampl_str += f"\n#Example-{idx}\nInput: {ex['input']}\nOutput: {json.dumps(ex['output'])}\n"
    return exampl_str


def build_prompts(icl_count):
    with open(os.path.join(NESTFUL_DIR, "data_v2", "nestful_data.jsonl")) as f:
        data = [json.loads(l) for l in f]
    # eval.py lines 17-20
    for i in range(len(data)):
        data[i]["tools"] = json.dumps(data[i]["tools"])
        data[i]["gold_answer"] = json.dumps(data[i]["gold_answer"])
        data[i]["output"] = json.dumps(data[i]["output"])

    with open(os.path.join(NESTFUL_DIR, "src", "icl_examples.json")) as f:
        icl_examples = json.load(f)[:icl_count]
    with open(os.path.join(NESTFUL_DIR, "src", "PROMPTS.json")) as f:
        template = json.load(f)["Hammer2.0-7b"]

    icl_str = get_icl_str(icl_examples)
    test_data = []
    for sample in data:
        # instruct_data_prep.get_instruct_data, generic model except-branch
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
    ap.add_argument("--model", default="mlx-community/Qwen3-4B-Instruct-2507-bf16")
    ap.add_argument("--model_name", default="Qwen3-4B-Instruct-2507")
    ap.add_argument("--save_directory", default="results")
    ap.add_argument("--icl_count", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max_tokens", type=int, default=1000)
    ap.add_argument("--chunk_size", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0, help="only run first N samples (smoke test)")
    args = ap.parse_args()
    print(args, flush=True)

    test_data = build_prompts(args.icl_count)
    if args.limit:
        test_data = test_data[: args.limit]

    save_dir = os.path.join(args.save_directory, f"nestful_{args.icl_count}", args.model_name)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "output.jsonl")

    done_ids = set()
    if os.path.exists(save_path):
        with open(save_path) as f:
            for l in f:
                try:
                    done_ids.add(json.loads(l)["sample_id"])
                except Exception:
                    pass
        print(f"### Resuming: {len(done_ids)} samples already done", flush=True)
    todo = [s for s in test_data if s["sample_id"] not in done_ids]
    print(f"### {len(todo)} samples to run", flush=True)
    if not todo:
        print("### Nothing to do", flush=True)
        return

    from mlx_lm import load, batch_generate
    from mlx_lm.sample_utils import make_sampler

    print("### Loading model...", flush=True)
    model, tokenizer = load(args.model)
    sampler = make_sampler(temp=args.temperature)

    t0 = time.time()
    n_done = 0
    for idx in range(0, len(todo), args.chunk_size):
        chunk = todo[idx : idx + args.chunk_size]
        token_prompts = [tokenizer.encode(s["input"]) for s in chunk]
        resp = batch_generate(
            model,
            tokenizer,
            prompts=token_prompts,
            max_tokens=args.max_tokens,
            sampler=sampler,
            completion_batch_size=32,
        )
        with open(save_path, "a") as f:
            for s, text in zip(chunk, resp.texts):
                rec = dict(s)
                rec["generated_text"] = text.strip()
                f.write(json.dumps(rec) + "\n")
        n_done += len(chunk)
        el = time.time() - t0
        rate = n_done / el
        eta = (len(todo) - n_done) / rate if rate > 0 else 0
        print(
            f"### {n_done}/{len(todo)} | {el/60:.1f} min elapsed | "
            f"{rate*60:.1f} samples/min | ETA {eta/60:.1f} min | "
            f"gen_tps {resp.stats.generation_tps:.0f} | peak_mem {resp.stats.peak_memory:.1f} GB",
            flush=True,
        )

    print("### DONE...!!!", flush=True)


if __name__ == "__main__":
    main()
