"""Negative tests for the build-time guards.

A validation suite that has never rejected anything is decoration. This injects
one fault per guard into a known-good sample and asserts each guard fires.

    python test_guards.py
"""

import json

import build_dataset as B
import queries
from graphs import GRAPHS

CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


g = GRAPHS[0]                       # syn-001: gold 400.0, intermediate $var_2 = 240.0
GOLD, VALUES = g.execute()
SEQ = g.to_sequence()
CATALOGUE, NAMES = B.build_catalogue(g, 1000)
QUERY = queries.QUERIES["syn-001"]


@case("query states an intermediate value")
def _leak():
    B.check(g, SEQ, NAMES, QUERY + " (240 posters are already printed.)", GOLD, VALUES)


@case("query drops a literal the answer depends on")
def _coverage():
    B.check(g, SEQ, NAMES, QUERY.replace("640", "many"), GOLD, VALUES)


@case("catalogue omits a tool the answer calls")
def _missing_tool():
    B.check(g, SEQ, [n for n in NAMES if n != "subtract"], QUERY, GOLD, VALUES)


@case("catalogue offers no distractors")
def _no_distractors():
    B.check(g, SEQ, ["divide", "multiply", "subtract"], QUERY, GOLD, VALUES)


@case("serialised sequence no longer reproduces the gold answer")
def _reexec():
    bad = json.loads(json.dumps(SEQ))
    bad[1]["arguments"]["arg_1"] = 999
    B.check(g, bad, NAMES, QUERY, GOLD, VALUES)


@case("sequence contains a forward reference")
def _forward_ref():
    bad = json.loads(json.dumps(SEQ))
    bad[0], bad[1] = bad[1], bad[0]
    B.check(g, bad, NAMES, QUERY, GOLD, VALUES)


def main():
    failed = 0
    for name, fn in CASES:
        try:
            fn()
            print("  FAIL  guard did not fire: {}".format(name))
            failed += 1
        except AssertionError as e:
            print("  ok    {}\n          -> {}".format(name, str(e)[:90]))
    B.check(g, SEQ, NAMES, QUERY, GOLD, VALUES)      # positive control
    print("  ok    positive control: the clean sample passes every guard")
    print("{}/{} guards fire".format(len(CASES) - failed, len(CASES)))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
