"""Minimal stand-in for the `jsonlines` package (only what NESTFUL's utils.py touches)."""
import json


class _Reader:
    def __init__(self, path):
        self.path = path

    def iter(self):
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Writer:
    def __init__(self, path):
        self.f = open(path, "w")

    def write_all(self, data):
        for d in data:
            self.f.write(json.dumps(d) + "\n")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.f.close()
        return False


def open(path, mode="r"):  # noqa: A001
    import builtins
    return _Reader(path) if mode == "r" else _Writer(path)
