// The shared component catalog: the ONLY components any page may draw.
//
// Every topic speaks a different format (a JSON tree, A2UI messages,
// OpenUI Lang, a json-render spec, ...). Each topic's renderer translates
// that format into calls to these functions. Text always goes in through
// textContent, never innerHTML, so model output cannot inject markup.
// The single exception is GeneratedView, which puts model-written HTML in a
// sandboxed iframe.

export function h(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === "") continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export const components = {
  Heading: ({ text }) => h("h2", { class: "c-heading" }, text),
  Text: ({ text }) => h("p", { class: "c-text" }, text),
  MetricCard: ({ label, value, delta }) =>
    h("div", { class: "c-card" }, [
      h("div", { class: "c-label" }, label),
      h("div", { class: "c-value" }, value),
      delta ? h("div", { class: "c-delta " + (String(delta).startsWith("-") ? "down" : "up") }, delta) : null,
    ]),
  BarChart: ({ title, data = [] }) => {
    const max = Math.max(1, ...data.map((d) => d.value));
    return h("div", { class: "c-chart" }, [
      title ? h("div", { class: "c-label" }, title) : null,
      h("div", { class: "c-bars" }, data.map((d) =>
        h("div", { class: "c-bar-wrap", title: `${d.label}: ${d.value}` }, [
          h("div", { class: "c-bar", style: `height:${(d.value / max) * 100}%` }),
          h("span", {}, d.label),
        ]))),
    ]);
  },
  Button: ({ label, onClick }) => h("button", { class: "c-button", onclick: onClick }, label),
  TextField: ({ label, value, onInput }) =>
    h("label", { class: "c-field" }, [
      h("span", {}, label),
      h("input", { value: value ?? "", oninput: (e) => onInput && onInput(e.target.value) }),
    ]),
  Row: ({ children }) => h("div", { class: "c-row" }, children),
  Column: ({ children }) => h("div", { class: "c-column" }, children),
  // The open-ended escape hatch: model-written HTML, sandboxed.
  GeneratedView: ({ html, height }) => sandboxedFrame(html, height),
};

// A placeholder for something that has not streamed in yet.
export const pending = (what) => h("div", { class: "c-pending" }, `waiting for ${what}…`);

// Put untrusted HTML in an iframe that:
//  * has an opaque origin (no allow-same-origin): no cookies, storage or parent DOM access
//  * cannot submit forms, open popups or navigate the top page
//  * gets a Content-Security-Policy that blocks every network request
export function sandboxedFrame(html, height = 220) {
  const csp = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">`;
  const doc = /<head>/i.test(html) ? html.replace(/<head>/i, "<head>" + csp) : csp + html;
  const frame = h("iframe", { class: "c-sandbox", sandbox: "allow-scripts", title: "generated view" });
  frame.style.height = `${height}px`;
  frame.srcdoc = doc;
  return frame;
}

export function showJson(el, obj) {
  el.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
}

export function log(el, text) {
  const line = h("div", {}, `${new Date().toLocaleTimeString()}  ${text}`);
  el.prepend(line);
}
