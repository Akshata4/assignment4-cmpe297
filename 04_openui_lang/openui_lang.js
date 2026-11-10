// OpenUI Lang parser for the browser - same grammar as openui_lang.py.
// parse(program) returns { statements: {name: node}, errors: [...] }.
// Lines that do not parse yet (still streaming) are reported, not fatal.

export const CATALOG = {
  Column: ["children"], Row: ["children"], Heading: ["text"], Text: ["text"],
  MetricCard: ["label", "value", "delta"], BarChart: ["title", "data"],
  Button: ["label", "action"], HtmlArtifact: ["title", "html"],
};

const TOKEN = /\s*(?:("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?)|([A-Za-z_]\w*)|([()[\]{},:=]))/y;

function tokenize(line) {
  const out = [];
  line = line.trimEnd();
  TOKEN.lastIndex = 0;
  while (TOKEN.lastIndex < line.length) {
    const start = TOKEN.lastIndex;
    const m = TOKEN.exec(line);
    if (!m) throw new Error(`unexpected character at ${start}`);
    if (m[1]) out.push(["str", m[1]]); else if (m[2]) out.push(["num", m[2]]);
    else if (m[3]) out.push(["id", m[3]]); else out.push(["p", m[4]]);
  }
  return out;
}

function parseLine(line) {
  const t = tokenize(line);
  let i = 0;
  const peek = () => t[i] || [null, null];
  const take = (v) => {
    const tok = peek();
    if (tok[0] === null || (v !== undefined && tok[1] !== v)) throw new Error(`expected ${v ?? "a value"}, got ${tok[1]}`);
    i++; return tok;
  };
  const list = (close, item) => { const out = []; while (peek()[1] !== close) { out.push(item()); if (peek()[1] === ",") take(","); } take(close); return out; };
  function value() {
    const [kind, text] = take();
    if (kind === "str") return JSON.parse(text);
    if (kind === "num") return Number(text);
    if (kind === "id") {
      if (text === "true" || text === "false" || text === "null") return JSON.parse(text);
      if (peek()[1] === "(") {
        take("(");
        const args = list(")", value);
        if (!CATALOG[text]) throw new Error(`'${text}' is not in the catalog`);
        return { component: text, props: Object.fromEntries(args.map((a, k) => [CATALOG[text][k], a])) };
      }
      return { $ref: text };
    }
    if (text === "[") return list("]", value);
    if (text === "{") {
      return Object.fromEntries(list("}", () => { const k = take()[1]; take(":"); return [k.startsWith('"') ? JSON.parse(k) : k, value()]; }));
    }
    throw new Error(`unexpected ${text}`);
  }
  const [kind, name] = take();
  if (kind !== "id") throw new Error("a statement starts with a name");
  take("=");
  const node = value();
  if (peek()[0] !== null) throw new Error(`trailing input ${peek()[1]}`);
  return [name, node];
}

export function parse(program) {
  const statements = {}, errors = [];
  program.split("\n").forEach((line, n) => {
    if (!line.trim() || line.trim().startsWith("#")) return;
    try { const [name, node] = parseLine(line); statements[name] = node; }
    catch (e) { errors.push(`line ${n + 1}: ${e.message}`); }
  });
  return { statements, errors };
}
