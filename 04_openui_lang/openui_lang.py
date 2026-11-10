"""A small OpenUI Lang parser (Python copy; the browser uses openui_lang.js).

OpenUI Lang (Thesys, https://www.openui.com) describes a UI as lines of

    name = Component(arg1, arg2, ...)

Arguments are positional; the catalog maps positions to prop names.
Values are strings, numbers, true/false/null, [arrays], {objects}, or a bare
identifier, which is a *reference* to another line. References may point
forward (to a line that has not arrived yet), so a renderer can draw the
outline first and fill it in as the stream continues.

This is a teaching subset of the language, not the full grammar.
"""

import json
import re

TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?)|(?P<id>[A-Za-z_]\w*)|(?P<p>[()\[\]{},:=]))')

# Component -> positional parameter names.
CATALOG = {
    "Column": ["children"],
    "Row": ["children"],
    "Heading": ["text"],
    "Text": ["text"],
    "MetricCard": ["label", "value", "delta"],
    "BarChart": ["title", "data"],
    "Button": ["label", "action"],
    "HtmlArtifact": ["title", "html"],  # the open-ended escape hatch
}


class ParseError(ValueError):
    pass


def tokenize(line: str) -> list[tuple[str, str]]:
    pos, out = 0, []
    line = line.rstrip()
    while pos < len(line):
        m = TOKEN.match(line, pos)
        if not m:
            raise ParseError(f"unexpected character at {pos}: {line[pos:pos + 10]!r}")
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, value=None):
        tok = self.peek()
        if tok[0] is None or (value is not None and tok[1] != value):
            raise ParseError(f"expected {value or 'a value'}, got {tok[1]!r}")
        self.i += 1
        return tok

    def value(self):
        kind, text = self.take()
        if kind == "str":
            return json.loads(text)
        if kind == "num":
            return float(text) if "." in text else int(text)
        if kind == "id":
            if text in ("true", "false", "null"):
                return {"true": True, "false": False, "null": None}[text]
            if self.peek()[1] == "(":
                return self.call(text)
            return {"$ref": text}
        if text == "[":
            items = []
            while self.peek()[1] != "]":
                items.append(self.value())
                if self.peek()[1] == ",":
                    self.take(",")
            self.take("]")
            return items
        if text == "{":
            obj = {}
            while self.peek()[1] != "}":
                key = self.take()[1]
                key = json.loads(key) if key.startswith('"') else key
                self.take(":")
                obj[key] = self.value()
                if self.peek()[1] == ",":
                    self.take(",")
            self.take("}")
            return obj
        raise ParseError(f"unexpected {text!r}")

    def call(self, name):
        self.take("(")
        args = []
        while self.peek()[1] != ")":
            args.append(self.value())
            if self.peek()[1] == ",":
                self.take(",")
        self.take(")")
        if name not in CATALOG:
            raise ParseError(f"'{name}' is not in the catalog")
        params = CATALOG[name]
        if len(args) > len(params):
            raise ParseError(f"{name} takes at most {len(params)} arguments")
        return {"component": name, "props": dict(zip(params, args))}


def parse_line(line: str) -> tuple[str, dict]:
    p = _Parser(tokenize(line))
    kind, name = p.take()
    if kind != "id":
        raise ParseError("a statement starts with a name")
    p.take("=")
    node = p.value()
    if p.peek()[0] is not None:
        raise ParseError(f"trailing input {p.peek()[1]!r}")
    return name, node


def parse(program: str) -> dict[str, dict]:
    """Parse a whole program into {name: node}. Raises ParseError on bad lines."""
    statements = {}
    for n, line in enumerate(program.splitlines(), 1):
        if line.strip() and not line.lstrip().startswith("#"):
            try:
                name, node = parse_line(line)
            except ParseError as exc:
                raise ParseError(f"line {n}: {exc}") from None
            statements[name] = node
    return statements


def resolve(statements: dict, name: str = "root", seen=()):
    """Expand references into a nested tree (for comparison with JSON)."""
    if name in seen:
        raise ParseError(f"reference cycle through '{name}'")

    def expand(v):
        if isinstance(v, dict) and "$ref" in v:
            return resolve(statements, v["$ref"], seen + (name,))
        if isinstance(v, dict):
            return {k: expand(x) for k, x in v.items()}
        if isinstance(v, list):
            return [expand(x) for x in v]
        return v

    if name not in statements:
        raise ParseError(f"undefined reference '{name}'")
    return expand(statements[name])
