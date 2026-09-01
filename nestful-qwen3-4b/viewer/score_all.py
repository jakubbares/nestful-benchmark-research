#!/usr/bin/env python3
"""Per-sample rescoring of every NESTFUL run using IBM's own scorer/parser code.

Emits one JSON blob per run with, for every sample: parsed prediction, official
partial/full accuracy, execution-based win, the value the predicted call chain
actually produced, and a diagnosis of why it differs from gold.
"""
import io, json, os, signal, sys, importlib.util, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
NESTFUL = os.path.join(HERE, "NESTFUL")
sys.path.insert(0, os.path.join(HERE, "shim"))
sys.path.insert(0, os.path.join(NESTFUL, "src"))

from output_parsers import parse_Hammer2_0_7b, parse_xLAM_1b_fc_r   # noqa: E402
from utils import post_process_api_with_args             # noqa: E402
from sklearn.metrics import accuracy_score               # noqa: E402

EXEC_DIR = os.path.join(NESTFUL, "data_v2", "executable_functions")
RUN_ROOT = ("/Users/jakubbares/Library/CloudStorage/GoogleDrive-bares.jakub@gmail.com/"
            "My Drive/CIIRC PhD/FIrst-Effort/nestful-qwen3-4b")

# Third element is the output_parsers.py function for that model's native
# output format. xLAM emits {"tool_calls": [...]}, not Hammer's bare list -
# using parse_Hammer2_0_7b on it would misparse every sample.
RUNS = [
    ("hammer_3shot", "matched_results/hammer_3shot/output.jsonl", parse_Hammer2_0_7b),
    ("hammer_1shot", "matched_results/hammer_1shot/output.jsonl", parse_Hammer2_0_7b),
    ("qwen3_3shot",  "matched_results/qwen3_3shot/output.jsonl", parse_Hammer2_0_7b),
    ("qwen3_1shot",  "matched_results/qwen3_1shot/output.jsonl", parse_Hammer2_0_7b),
    ("qwen3_3shot_sagemaker", "results/nestful_3/output.jsonl", parse_Hammer2_0_7b),
    ("qwen3_1shot_sagemaker", "results/nestful_1/output.jsonl", parse_Hammer2_0_7b),
    ("hammer_3shot_adhoc",    "results/validation_hammer2.0-7b/output.jsonl", parse_Hammer2_0_7b),
    ("xlam_3shot",   "matched_results/xlam_3shot/output.jsonl", parse_xLAM_1b_fc_r),
    ("xlam_1shot",   "matched_results/xlam_1shot/output.jsonl", parse_xLAM_1b_fc_r),
    ("qwen3thinking_3shot", "matched_results/qwen3thinking_3shot/output.jsonl", parse_Hammer2_0_7b),
    ("qwen3thinking_1shot", "matched_results/qwen3thinking_1shot/output.jsonl", parse_Hammer2_0_7b),
    ("hammer_3shot_checklist", "matched_results/hammer_3shot_checklist/output.jsonl", parse_Hammer2_0_7b),
    ("xlam_3shot_checklist",   "matched_results/xlam_3shot_checklist/output.jsonl", parse_xLAM_1b_fc_r),
]

# ---------------------------------------------------------------- executor ---
FUNC_FILE_MAP = json.load(open(os.path.join(EXEC_DIR, "func_file_map.json")))


def _basic_func_names():
    names = []
    for l in open(os.path.join(EXEC_DIR, "basic_functions.py")):
        if l.startswith("def "):
            s = l.strip().replace("def ", "")
            names.append(s[:s.index("(")])
    return set(names)


BASIC = _basic_func_names()


def _load(file_name):
    """Fresh exec_module per call, exactly as IBM's scorer does. Caching the
    module changes results (module-level state carries between samples)."""
    path = os.path.join(EXEC_DIR, file_name)
    spec = importlib.util.spec_from_file_location(file_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[file_name] = mod
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


def _handler(signum, frame):
    raise TimeoutError("Time limit exceeded!")


def execute_chain(func_calls, spec_lib):
    """IBM calculate_ans, with the failure reason kept instead of discarded."""
    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(10)
    try:
        variable_result_map = {}
        for f in func_calls:
            label = f["label"].replace("$", "")
            matches = [s for s in spec_lib if s["name"] == f["name"]]
            if not matches:
                return False, f"function '{f['name']}' is not in this sample's tool catalog"
            output_params = list(matches[0]["output_parameters"].keys())
            arg_val_list = []
            for k, v in f["arguments"].items():
                if type(v) == str and v.startswith("$") and v.endswith("$"):
                    v = v[1:-1]
                    v_l, out_param = v.split(".", 1)
                    v = variable_result_map[v_l][out_param]
                elif type(v) == str and v.startswith("$var"):
                    v = v[1:]
                    v_l, out_param = v.split(".", 1)
                    v = variable_result_map[v_l][out_param]
                arg_val_list.append(v)

            file_name = "basic_functions.py" if f["name"] in BASIC else FUNC_FILE_MAP[f["name"]]
            func = getattr(_load(file_name), f["name"])
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    res = func(*arg_val_list)
            except Exception as e:
                return False, f"{f['name']}() raised {type(e).__name__}: {e}"

            if len(output_params) != 1:
                return False, f"{f['name']} declares {len(output_params)} outputs (scorer supports 1)"
            variable_result_map[label] = {output_params[0]: res}

        final_var = func_calls[-1]["label"].replace("$", "")
        return next(iter(variable_result_map[final_var].values())), None
    except TimeoutError:
        return False, "execution timed out (10s)"
    except KeyError as e:
        return False, f"unresolved variable reference {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        signal.alarm(0)


def listit(t):
    return list(map(listit, t)) if isinstance(t, (list, tuple)) else t


def win_score(pred_ans, gold_ans):
    """IBM calculate_win_score comparison half (execution already done)."""
    if type(gold_ans) == float and type(pred_ans) == float:
        dec_no = len(str(gold_ans).split(".")[1])
        pred_ans = round(pred_ans, dec_no)
    if pred_ans == gold_ans:
        return True
    if type(pred_ans) == tuple and type(gold_ans) == list:
        if listit(pred_ans) == gold_ans:
            return True
    return False


def jsonable(v):
    try:
        json.dumps(v)
        return v
    except Exception:
        # A model can produce a call chain (e.g. runaway exponentiation) whose
        # real execution result is a valid Python int with thousands of
        # digits - repr()/str() on that hits Python's int->str conversion
        # guard (PEP 587-style limit) and raises instead of returning text.
        # bit_length() avoids the guard entirely (no string conversion).
        if isinstance(v, int) and not isinstance(v, bool):
            digits = int(v.bit_length() * 0.301029995664) + 1
            return f"<integer too large to serialize: ~{digits} digits>"
        try:
            return repr(v)
        except Exception:
            return "<unrepresentable value>"


# ------------------------------------------------------------------ scoring --
def api_signature(call):
    args = ", ".join(sorted(
        f"{k} = {v + '$' if isinstance(v, str) and v.startswith('$') and not v.endswith('$') else v}"
        for k, v in call.get("arguments", {}).items()))
    return f"{call['name']}({args})"


def score_run(path, parser=parse_Hammer2_0_7b):
    rows = []
    for line in open(path):
        item = json.loads(line)
        pred_fc, gold_fc, pred_dl, gold_dl, _, parse_err = parser(dict(item), 0)

        raw = item["generated_text"].replace("```", "").strip()
        if raw in ("[]", "[ ]"):
            refusal = True
        else:
            try:
                parsed_raw = json.loads(raw)
                refusal = isinstance(parsed_raw, dict) and parsed_raw.get("tool_calls") == []
            except Exception:
                refusal = False

        def sigs(func_calls):
            out = []
            for f in func_calls:
                try:
                    d = json.loads(f.replace("<|endoftext|>", "").strip())
                    out.append(api_signature(d))
                except Exception:
                    continue
            return out

        g_sig, p_sig = post_process_api_with_args(sigs(gold_fc), sigs(pred_fc))
        try:
            partial = float(accuracy_score(g_sig, p_sig))
        except Exception:
            partial = 0.0
        full = partial == 1.0

        gold_names = [c["name"] for c in gold_dl]
        pred_names = [c.get("name") for c in pred_dl if isinstance(c, dict)] if isinstance(pred_dl, list) else []

        gold_ans = json.loads(item["gold_answer"])
        tools = json.loads(item["tools"])
        if pred_dl:
            pred_ans, exec_err = execute_chain(pred_dl, tools)
        else:
            pred_ans, exec_err = False, "no parsable function calls to execute"
        win = bool(win_score(pred_ans, gold_ans)) if pred_dl else False

        rows.append({
            "id": item["sample_id"],
            "gen": item["generated_text"],
            # thinking runs strip <think>...</think> before scoring and keep the
            # untouched original separately - this is that original, defaulting
            # to the scored text itself when there was nothing to strip.
            "genraw": item.get("generated_text_raw", item["generated_text"]),
            "pn": pred_names,
            "pa": jsonable(pred_ans) if not (pred_ans is False and exec_err) else None,
            "ee": exec_err,
            "pe": bool(parse_err),
            "rf": refusal,
            "pt": round(partial, 4),
            "fm": full,
            "wn": win,
            "ns": pred_names == gold_names,
            "nset": sorted(pred_names) == sorted(gold_names),
        })
    return rows


if __name__ == "__main__":
    out = {}
    for name, rel, parser in RUNS:
        p = os.path.join(RUN_ROOT, rel)
        print(f"scoring {name} ...", flush=True)
        rows = score_run(p, parser)
        agg = {
            "n": len(rows),
            "full": sum(r["fm"] for r in rows) / len(rows),
            "partial": sum(r["pt"] for r in rows) / len(rows),
            "win": sum(r["wn"] for r in rows) / len(rows),
            "refusal": sum(r["rf"] for r in rows) / len(rows),
            "parse_err": sum(r["pe"] for r in rows) / len(rows),
        }
        print("   ", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in agg.items()}, flush=True)
        out[name] = rows
    json.dump(out, open(os.path.join(HERE, "scored.json"), "w"))
    print("wrote scored.json")
