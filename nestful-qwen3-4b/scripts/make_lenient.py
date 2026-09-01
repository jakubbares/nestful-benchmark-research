#!/usr/bin/env python
"""Secondary analysis: strip markdown code fences (```json ... ```) from
generated_text so the official Hammer parser can read otherwise-valid JSON.
Writes output_lenient.jsonl next to the input. The official parser already
strips bare ``` but chokes on the 'json' language tag left behind."""
import json, re, sys

path = sys.argv[1]
out_path = path.replace("output.jsonl", "output_lenient.jsonl")
n_fixed = 0
with open(path) as f, open(out_path, "w") as out:
    for line in f:
        rec = json.loads(line)
        g = rec["generated_text"].strip()
        m = re.match(r"^```(?:json)?\s*(.*?)\s*```\s*$", g, re.DOTALL) or re.match(
            r"^```(?:json)?\s*(.*)$", g, re.DOTALL
        )
        if m:
            rec["generated_text"] = m.group(1).strip()
            n_fixed += 1
        out.write(json.dumps(rec) + "\n")
print(f"fence-stripped {n_fixed} records -> {out_path}")
