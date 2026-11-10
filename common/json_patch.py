"""Minimal RFC 6902 JSON Patch (add / replace / remove) and RFC 6901 pointers.

AG-UI ``STATE_DELTA`` events and json-render streams both use JSON Patch.
The browser has the same code in ``json_patch.js``; this copy lets the
Python tests check that a stream of patches builds the expected document.
"""

import copy


def _tokens(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"bad JSON pointer: {pointer!r}")
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]


def get_pointer(doc, pointer: str):
    for tok in _tokens(pointer):
        doc = doc[int(tok)] if isinstance(doc, list) else doc[tok]
    return doc


def apply_patch(doc, ops: list[dict]):
    doc = copy.deepcopy(doc)
    for op in ops:
        tokens = _tokens(op["path"])
        if not tokens:  # the whole document
            doc = copy.deepcopy(op.get("value"))
            continue
        parent = doc
        for tok in tokens[:-1]:
            parent = parent[int(tok)] if isinstance(parent, list) else parent[tok]
        key = tokens[-1]
        if isinstance(parent, list):
            idx = len(parent) if key == "-" else int(key)
            if op["op"] == "add":
                parent.insert(idx, op["value"])
            elif op["op"] == "replace":
                parent[idx] = op["value"]
            elif op["op"] == "remove":
                parent.pop(idx)
        else:
            if op["op"] in ("add", "replace"):
                parent[key] = op["value"]
            elif op["op"] == "remove":
                parent.pop(key)
        if op["op"] not in ("add", "replace", "remove"):
            raise ValueError(f"unsupported op {op['op']!r}")
    return doc
