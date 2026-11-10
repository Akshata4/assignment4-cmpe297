"""The one example used in every topic: a small shop's weekly sales.

Using the same data everywhere makes the comparison fair: each topic shows
the *same* dashboard, delivered in a different format or protocol.
"""

SALES = {
    "week": "Nov 3 - Nov 9",
    "revenue": 48200,
    "revenue_delta": "+12%",
    "orders": 312,
    "orders_delta": "+5%",
    "top_product": "Lemons",
    "stock_left": 40,  # crates of lemons still in stock
    "daily": [
        {"label": "Mon", "value": 5200},
        {"label": "Tue", "value": 6100},
        {"label": "Wed", "value": 7400},
        {"label": "Thu", "value": 6900},
        {"label": "Fri", "value": 8800},
        {"label": "Sat", "value": 9100},
        {"label": "Sun", "value": 4700},
    ],
}

ALLOWED_ACTIONS = {"reorder"}  # the only action any button may trigger


def money(n: float) -> str:
    return f"${n:,.0f}"


def reorder(crates: int = 60) -> str:
    """The application-side handler for the ``reorder`` action (demo only)."""
    return f"Reorder of {crates} crates of {SALES['top_product']} queued (demo - nothing was bought)."


def custom_widget_html() -> str:
    """What an *open-ended* model would write: raw HTML/CSS/JS.

    It is a widget no catalog has (a reorder planner with a slider), which is
    exactly why you would allow open-ended output. It must only ever be shown
    inside a sandboxed iframe.
    """
    return """<!doctype html>
<html><head><style>
  body { font-family: system-ui, sans-serif; margin: 12px; color: #1f2937; }
  h3 { margin: 0 0 8px; font-size: 15px; }
  input { width: 100%; }
  .out { margin-top: 10px; padding: 8px; border-radius: 6px; background: #ecfdf5; color: #065f46; font-weight: 600; }
</style></head><body>
  <h3>Lemon reorder planner (generated HTML)</h3>
  <label>Days of stock to cover: <b id="d">7</b></label>
  <input id="days" type="range" min="1" max="14" value="7">
  <div class="out" id="out"></div>
  <script>
    const perDay = 12, inStock = 40;   // numbers the model wrote into the page
    const days = document.getElementById('days');
    function update() {
      const need = Math.max(0, perDay * days.value - inStock);
      document.getElementById('d').textContent = days.value;
      document.getElementById('out').textContent = 'Order ' + need + ' crates to cover ' + days.value + ' days';
    }
    days.oninput = update; update();
  </script>
</body></html>"""
