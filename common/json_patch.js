// Minimal RFC 6902 JSON Patch (add / replace / remove) + RFC 6901 pointers.
// Same behaviour as common/json_patch.py.

function tokens(pointer) {
  if (pointer === "") return [];
  return pointer.slice(1).split("/").map((t) => t.replace(/~1/g, "/").replace(/~0/g, "~"));
}

export function getPointer(doc, pointer) {
  let cur = doc;
  for (const t of tokens(pointer)) {
    if (cur == null) return undefined;
    cur = Array.isArray(cur) ? cur[Number(t)] : cur[t];
  }
  return cur;
}

export function setPointer(doc, pointer, value) {
  return applyPatch(doc, [{ op: "add", path: pointer, value }]);
}

export function applyPatch(doc, ops) {
  doc = structuredClone(doc);
  for (const op of ops) {
    const toks = tokens(op.path);
    if (toks.length === 0) { doc = structuredClone(op.value); continue; }
    let parent = doc;
    for (const t of toks.slice(0, -1)) parent = Array.isArray(parent) ? parent[Number(t)] : parent[t];
    const key = toks[toks.length - 1];
    if (Array.isArray(parent)) {
      const i = key === "-" ? parent.length : Number(key);
      if (op.op === "add") parent.splice(i, 0, op.value);
      else if (op.op === "replace") parent[i] = op.value;
      else if (op.op === "remove") parent.splice(i, 1);
    } else {
      if (op.op === "add" || op.op === "replace") parent[key] = op.value;
      else if (op.op === "remove") delete parent[key];
    }
  }
  return doc;
}
