"""Runs IBM's official scorer.py with ONE targeted monkey-patch to
calculate_win_score, fixing two equality-check gaps identified in audit:

  1. int-vs-float: gold=20 (int), pred=20.0 (float) currently fails equality
     outright because the original code only rounds when *both* are float.
  2. list-of-mixed-numeric-types: [20, 3.5] vs [20.0, 3.5] currently fails
     outright; now compared element-wise with the same numeric tolerance.

Nothing else in scorer.py, output_parsers.py, or utils.py is touched.
Usage identical to the original: pass --model_name/--result_file_path/--executable_func_dir.
"""
import sys, os, json, math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "NESTFUL_full", "src"))
import scorer as _scorer  # noqa: E402


def _numeq(a, b, ndigits=6):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return round(float(a), ndigits) == round(float(b), ndigits)
    return a == b


def calculate_win_score_patched(pred_func_calls, gold_ans, tools, executable_func_dir):
    if not pred_func_calls:
        return False
    gold_ans = json.loads(gold_ans)
    tools = json.loads(tools)
    pred_ans = _scorer.calculate_ans(pred_func_calls, tools, executable_func_dir)

    if isinstance(gold_ans, float) and isinstance(pred_ans, float):
        dec_no = len(str(gold_ans).split(".")[1])
        pred_ans = round(pred_ans, dec_no)

    if pred_ans == gold_ans:
        return True

    # Fix 1: cross int/float numeric equality
    if _numeq(pred_ans, gold_ans):
        return True

    # tuple -> list coercion (original behavior, kept)
    if isinstance(pred_ans, tuple) and isinstance(gold_ans, list):
        pred_ans_l = _scorer.listit(pred_ans)
        if pred_ans_l == gold_ans:
            return True
        # Fix 2: element-wise numeric equality for lists/tuples of mixed int/float
        if isinstance(pred_ans_l, list) and len(pred_ans_l) == len(gold_ans):
            if all(_numeq(p, g) for p, g in zip(pred_ans_l, gold_ans)):
                return True

    # Fix 2b: both already lists (no tuple involved), mixed numeric types
    if isinstance(pred_ans, list) and isinstance(gold_ans, list) and len(pred_ans) == len(gold_ans):
        if all(_numeq(p, g) for p, g in zip(pred_ans, gold_ans)):
            return True

    return False


# Late-bound: calculate_scores() looks up calculate_win_score by name in
# scorer.py's own module globals at call time, so overwriting it here is
# enough - no need to re-exec scorer.py's source (that would just redefine
# the original back).
_scorer.calculate_win_score = calculate_win_score_patched

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str)
    parser.add_argument("--result_file_path", type=str)
    parser.add_argument("--executable_func_dir", type=str)
    args = parser.parse_args()

    data = _scorer.read_jsonlines(args.result_file_path)
    result = _scorer.calculate_scores(data, args.model_name, args.executable_func_dir)
    _scorer.print_result(result, args.model_name)
