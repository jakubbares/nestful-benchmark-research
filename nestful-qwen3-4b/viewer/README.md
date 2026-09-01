# NESTFUL Run Explorer — build pipeline

`../nestful_explorer.html` is a single self-contained file (1.5 MB): all 1,861 NESTFUL
samples, all 7 runs, every prompt, and every per-sample score, embedded as gzip+base64
and inflated in the browser with `DecompressionStream`. No server, no network, no CDN.

## Rebuild

```bash
git clone --depth 1 https://github.com/IBM/NESTFUL.git      # into this directory
python3 -W ignore score_all.py        # per-sample rescoring -> scored.json  (~2 min)
python3 -W ignore build_payload.py    # dataset + runs + prompts -> payload.b64
python3 assemble.py ../nestful_explorer.html
```

Requires `scikit-learn` (`shim/jsonlines.py` stands in for the `jsonlines` package).

## Verification

```bash
node prompt_test.mjs   # browser prompt rebuild vs the 7,444 stored prompts
node smoke.mjs         # headless-Chrome smoke test of every tab (needs puppeteer-core)
```

## Files

| file | role |
|---|---|
| `score_all.py` | drives IBM's `scorer.py` / `output_parsers.py` per sample; executes every predicted call chain |
| `build_payload.py` | dataset, dedup'd tool-spec table, official F1, domain split, diagnosis categories |
| `assemble.py` | stitches `tmpl_head.html` + `tmpl_js*.js` + `payload.b64` into the final HTML |
| `tmpl_head.html` | markup and CSS |
| `tmpl_js1.js` | prompt rebuilding, McNemar, filtering, list |
| `tmpl_js2.js` | sample detail, gold/prediction alignment, prompt modal |
| `tmpl_js3.js` | Compare and Overview tabs |
| `tmpl_js4.js` | Prompts and Method tabs, boot |

## Two things the rebuild gets right that are easy to get wrong

1. **Do not cache executed modules.** IBM's scorer calls `exec_module` fresh for every
   function call. Caching them changes 13 Win Rate outcomes, because NESTFUL's generated
   function files carry module-level state.
2. **F1 slot must be computed on the *grounded* call strings** the parser returns
   (`$var_1.result$` → `$divide.result$`), not on the raw prediction JSON. Computing it on
   raw JSON gives 0.642 instead of the correct 0.700.
