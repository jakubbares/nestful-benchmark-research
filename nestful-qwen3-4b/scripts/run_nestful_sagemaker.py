#!/usr/bin/env python
"""NESTFUL inference against a SageMaker vLLM endpoint hosting
Qwen/Qwen3-4B-Instruct-2507. Prompt construction is identical to
run_nestful_qwen3.py (IBM's official Hammer2.0-7b path, byte-for-byte).

Payload mode:
  completions  -> {"prompt": <full formatted string>}  (byte-exact, preferred)
  chat         -> {"messages":[{system},{user}]}       (identical after Qwen3
                  chat template application; used if the container only
                  routes /invocations to chat completions)
"""
import argparse, json, os, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from run_nestful_qwen3 import build_prompts

SYSTEM_MSG = "You are a helpful assistant."
USER_START = "<|im_start|>user\n"
USER_END = "<|im_end|>\n<|im_start|>assistant\n"


def to_messages(full_prompt):
    user = full_prompt.split(USER_START, 1)[1]
    user = user.rsplit(USER_END, 1)[0].rstrip("\n")
    return [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": user},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="nestful-qwen3-4b")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--model_name", default="Qwen3-4B-Instruct-2507")
    ap.add_argument("--save_directory", default="results_sm")
    ap.add_argument("--icl_count", type=int, default=3)
    ap.add_argument("--mode", choices=["completions", "chat", "tgi"], default="completions")
    ap.add_argument("--model_field", default="/opt/ml/model")
    ap.add_argument("--max_tokens", type=int, default=1000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
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
        print(f"### Resuming: {len(done_ids)} done", flush=True)
    todo = [s for s in test_data if s["sample_id"] not in done_ids]
    print(f"### {len(todo)} samples to run", flush=True)
    if not todo:
        return

    session = boto3.session.Session(region_name=args.region)
    client = session.client(
        "sagemaker-runtime",
        config=boto3.session.Config(
            read_timeout=300, connect_timeout=30, retries={"max_attempts": 0},
            max_pool_connections=args.concurrency * 2,
        ),
    )

    lock = threading.Lock()
    n_done = 0
    t0 = time.time()

    def call_one(sample):
        if args.mode == "tgi":
            body = {
                "inputs": sample["input"],
                "parameters": {
                    "max_new_tokens": args.max_tokens,
                    "temperature": args.temperature,
                    "do_sample": False,
                },
            }
        elif args.mode == "completions":
            body = {
                "model": args.model_field,
                "prompt": sample["input"],
                "max_tokens": args.max_tokens,
                "temperature": args.temperature,
            }
        else:
            body = {
                "model": args.model_field,
                "messages": to_messages(sample["input"]),
                "max_tokens": args.max_tokens,
                "temperature": args.temperature,
            }
        last_err = None
        for attempt in range(5):
            try:
                resp = client.invoke_endpoint(
                    EndpointName=args.endpoint,
                    ContentType="application/json",
                    Body=json.dumps(body),
                )
                out = json.loads(resp["Body"].read())
                if "generated_text" in out:  # TGI/LMI schema
                    text = out["generated_text"]
                elif isinstance(out, list) and out and "generated_text" in out[0]:
                    text = out[0]["generated_text"]
                else:  # OpenAI schema
                    choice = out["choices"][0]
                    text = choice.get("text")
                    if text is None:
                        text = choice["message"]["content"]
                return text.strip()
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"failed after retries: {last_err}")

    def worker(sample):
        nonlocal n_done
        text = call_one(sample)
        rec = dict(sample)
        rec["generated_text"] = text
        with lock:
            with open(save_path, "a") as f:
                f.write(json.dumps(rec) + "\n")
            n_done += 1
            if n_done % 50 == 0 or n_done == len(todo):
                el = time.time() - t0
                rate = n_done / el
                eta = (len(todo) - n_done) / rate if rate else 0
                print(
                    f"### {n_done}/{len(todo)} | {el/60:.1f} min | "
                    f"{rate*60:.1f} samples/min | ETA {eta/60:.1f} min",
                    flush=True,
                )

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(worker, s) for s in todo]
        errs = 0
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as e:
                errs += 1
                print(f"!!! sample failed: {e}", flush=True)
    print(f"### DONE. failures: {errs}", flush=True)


if __name__ == "__main__":
    main()
