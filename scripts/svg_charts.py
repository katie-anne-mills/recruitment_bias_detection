"""Reusable SVG charts for self-contained HTML reports.

Every chart function returns an inline <svg> string: no JavaScript, no external
assets. Colours are CSS custom properties defined in CHART_CSS (light and dark
mode), so include CHART_CSS in the page's <style> block and put the charts inside
an element with class "viz-root".

Charts plot scores on an integer scale (1 to scale_max, default 1–10), with
optional shaded bands given as (name, low, high) tuples, e.g. ("Minimal", 1, 2).
Series are coloured in order: the first series is blue, the second orange, the
third aqua. Hovering a dot or bar shows its tooltip text (an SVG <title>).

Charts:
    stacked_dot_chart          one dot per item, stacked in its score column; one row per series
    dot_plot                   one dot per series on each labelled row (e.g. an average per category)
    grouped_bar_chart          horizontal bars, one bar per series on each labelled row

HTML helpers:
    legend                     colour key for the series
    table                      plain table; the first cell of each row is a row heading
"""

import collections
import html
import math

# Colours: the first three slots of the dataviz reference palette, validated for
# colour-vision deficiency and contrast in both modes.
CHART_CSS = """
.viz-root {
  color-scheme: light;
  --surface-1: #fcfcfb; --page: #f9f9f7;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --band-a: #f0efec; --band-b: #fcfcfb;
  --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --surface-1: #1a1a19; --page: #0d0d0d;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --band-a: #262624; --band-b: #1a1a19;
    --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70;
  }
}
:root[data-theme="dark"] .viz-root {
  color-scheme: dark;
  --surface-1: #1a1a19; --page: #0d0d0d;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --band-a: #262624; --band-b: #1a1a19;
  --border: rgba(255,255,255,0.10);
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70;
}
table { border-collapse: collapse; width: 100%; margin: 8px 0 4px; background: var(--surface-1); font-size: 14px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--grid); vertical-align: top; }
th { color: var(--text-secondary); font-weight: 600; }
td.num { font-variant-numeric: tabular-nums; }
.legend { display: flex; gap: 20px; flex-wrap: wrap; font-size: 14px; color: var(--text-secondary); margin: 8px 0; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
svg { display: block; width: 100%; height: auto; background: var(--surface-1); border-radius: 8px; }
svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.t-primary { fill: var(--text-primary); }
.t-secondary { fill: var(--text-secondary); }
.t-muted { fill: var(--text-muted); }
@media print {
  .viz-root { color-scheme: light; }
  table, svg { break-inside: avoid; }
}
"""

SERIES_COLOURS = ("--series-1", "--series-2", "--series-3")


def series_colour(index: int) -> str:
    """CSS colour for the series at this position (blue, orange, aqua, then repeats)."""
    return f"var({SERIES_COLOURS[index % len(SERIES_COLOURS)]})"


def _esc(x) -> str:
    return html.escape(str(x))


def _svg(width: float, height: float, parts: list, description: str) -> str:
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(description)}">'
            f'<title>{_esc(description)}</title>' + "".join(parts) + "</svg>")


def _score_bands(bands, left: float, col_w: float, top: float, bottom: float) -> list:
    """Shaded background bands for a chart whose score columns are centred on 1..max."""
    parts = []
    # show "(1–2)" ranges only when the narrowest band is wide enough to fit them
    narrowest = min((hi - lo + 1 for _, lo, hi in bands), default=0)
    for i, (name, lo, hi) in enumerate(bands):
        x0, x1 = left + (lo - 1) * col_w, left + hi * col_w
        fill = "var(--band-a)" if i % 2 == 0 else "var(--band-b)"
        parts.append(f'<rect x="{x0:.1f}" y="{top}" width="{x1 - x0:.1f}" height="{bottom - top}" fill="{fill}"/>')
        label = f"{name} ({lo}–{hi})" if narrowest * col_w >= 90 else name
        parts.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{top + 14}" text-anchor="middle" font-size="11" '
                     f'class="t-muted">{_esc(label)}</text>')
    return parts


def _score_axis(left: float, col_w: float, y: float, scale_max: int, title: str) -> list:
    """Axis with one centred tick label per score, 1..scale_max."""
    parts = [f'<line x1="{left}" y1="{y}" x2="{left + scale_max * col_w}" y2="{y}" '
             'stroke="var(--axis)" stroke-width="1"/>']
    for v in range(1, scale_max + 1):
        x = left + (v - 0.5) * col_w
        parts.append(f'<text x="{x:.1f}" y="{y + 16}" text-anchor="middle" font-size="12" class="t-secondary" '
                     f'style="font-variant-numeric: tabular-nums">{v}</text>')
    if title:
        parts.append(f'<text x="{left + scale_max / 2 * col_w:.1f}" y="{y + 34}" text-anchor="middle" '
                     f'font-size="12" class="t-secondary">{_esc(title)}</text>')
    return parts


def stacked_dot_chart(series: list, *, bands=(), axis_title: str = "", description: str,
                      scale_max: int = 10, width: float = 720, label_width: float = 200) -> str:
    """One row per series; each item is a dot stacked in its score column.

    series: list of dicts with
        "name":   row label
        "points": list of (score, tooltip), stacked in the order given
        "median": optional (value, tooltip), drawn as a vertical bar under the row
        "mean":   optional (value, tooltip), drawn as an outline triangle under the row
    """
    left, right = label_width, 20
    col_w = (width - left - right) / scale_max
    per_row, step, r = 5, 10, 4
    top_pad, marker_h, row_gap = 24, 22, 14

    heights = []
    for s in series:
        counts = collections.Counter(score for score, _ in s["points"])
        stack_rows = max((math.ceil(c / per_row) for c in counts.values()), default=1)
        heights.append(stack_rows * step + 8 + marker_h)
    plot_bottom = top_pad + sum(heights) + row_gap * (len(series) - 1) + 8
    height = plot_bottom + 44

    parts = _score_bands(bands, left, col_w, 0, plot_bottom)
    y = top_pad
    for i, (s, h) in enumerate(zip(series, heights)):
        colour = series_colour(i)
        dots_bottom = y + h - marker_h
        parts.append(f'<text x="{left - 12}" y="{y + (h - marker_h) / 2 + 4:.1f}" text-anchor="end" '
                     f'font-size="13" font-weight="600" class="t-primary">{_esc(s["name"])}</text>')
        by_score = collections.defaultdict(list)
        for score, tooltip in s["points"]:
            by_score[score].append(tooltip)
        for score, tooltips in by_score.items():
            x0 = left + (score - 0.5) * col_w - (per_row - 1) * step / 2
            for k, tooltip in enumerate(tooltips):
                cx = x0 + (k % per_row) * step
                cy = dots_bottom - 4 - (k // per_row) * step
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{colour}" '
                             f'stroke="var(--surface-1)" stroke-width="1"><title>{_esc(tooltip)}</title></circle>')
        my = dots_bottom + 6
        if s.get("median"):
            value, tooltip = s["median"]
            xm = left + (value - 0.5) * col_w
            parts.append(f'<rect x="{xm - 1:.1f}" y="{my}" width="2" height="12" rx="1" fill="var(--text-primary)">'
                         f'<title>{_esc(tooltip)}</title></rect>')
        if s.get("mean"):
            value, tooltip = s["mean"]
            xa = left + (value - 0.5) * col_w
            parts.append(f'<path d="M{xa:.1f},{my} l5,10 h-10 z" fill="none" stroke="var(--text-primary)" '
                         f'stroke-width="1.5"><title>{_esc(tooltip)}</title></path>')
        y += h + row_gap

    parts += _score_axis(left, col_w, plot_bottom, scale_max, axis_title)
    return _svg(width, height, parts, description)


def dot_plot(rows: list, *, bands=(), axis_title: str = "", description: str, empty_label: str = "",
             scale_max: int = 10, width: float = 760, label_width: float = 340) -> str:
    """One labelled row per category, with a dot per series at its value.

    rows: list of (label, values), where values has one entry per series:
          (value, tooltip), or None when that series has no value for the row.
          Rows where every value is None show empty_label instead of dots.
    """
    left, right, row_h = label_width, 20, 26
    col_w = (width - left - right) / scale_max
    top = 24
    plot_bottom = top + row_h * len(rows) + 6
    height = plot_bottom + 44
    parts = _score_bands(bands, left, col_w, 0, plot_bottom)
    for j, (label, values) in enumerate(rows):
        cy = top + j * row_h + row_h / 2
        parts.append(f'<line x1="{left}" y1="{cy}" x2="{left + scale_max * col_w}" y2="{cy}" '
                     'stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{left - 10}" y="{cy + 4}" text-anchor="end" font-size="12" '
                     f'class="t-secondary">{_esc(label)}</text>')
        if all(v is None for v in values):
            if empty_label:
                parts.append(f'<text x="{left + 8}" y="{cy - 4}" font-size="11" font-style="italic" '
                             f'class="t-muted">{_esc(empty_label)}</text>')
            continue
        for i, v in enumerate(values):
            if v is None:
                continue
            value, tooltip = v
            # nudge series apart vertically so equal values don't hide each other
            offset = (i - (len(values) - 1) / 2) * 7
            cx = left + (value - 0.5) * col_w
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy + offset:.1f}" r="4.5" fill="{series_colour(i)}" '
                         f'stroke="var(--surface-1)" stroke-width="2"><title>{_esc(tooltip)}</title></circle>')
    parts += _score_axis(left, col_w, plot_bottom, scale_max, axis_title)
    return _svg(width, height, parts, description)


def grouped_bar_chart(rows: list, *, bands=(), axis_title: str = "", description: str,
                      scale_max: int = 10, width: float = 760, label_width: float = 360) -> str:
    """Horizontal bar chart: one labelled row per item, one bar per series, starting from 0.

    rows: list of (label, values), where values has one (value, tooltip) per series.
    Each bar is labelled with its value at the end.
    """
    left, right, top = label_width, 36, 24
    n_series = max((len(values) for _, values in rows), default=1)
    bar_h, bar_gap, row_gap, r = 10, 2, 12, 4
    row_h = n_series * bar_h + (n_series - 1) * bar_gap + row_gap
    unit = (width - left - right) / scale_max
    plot_bottom = top + row_h * len(rows)
    height = plot_bottom + 44

    # bars start at 0, so each band runs from the previous band's top score
    parts = []
    for i, (name, lo, hi) in enumerate(bands):
        x0, x1 = left + (lo - 1 if lo > 1 else 0) * unit, left + hi * unit
        fill = "var(--band-a)" if i % 2 == 0 else "var(--band-b)"
        parts.append(f'<rect x="{x0:.1f}" y="0" width="{x1 - x0:.1f}" height="{plot_bottom}" fill="{fill}"/>')
        parts.append(f'<text x="{(x0 + x1) / 2:.1f}" y="14" text-anchor="middle" font-size="11" '
                     f'class="t-muted">{_esc(name)}</text>')

    for j, (label, values) in enumerate(rows):
        y = top + j * row_h + row_gap / 2
        group_h = row_h - row_gap
        parts.append(f'<text x="{left - 10}" y="{y + group_h / 2 + 4:.1f}" text-anchor="end" font-size="12" '
                     f'class="t-secondary">{_esc(label)}</text>')
        for i, (value, tooltip) in enumerate(values):
            by = y + i * (bar_h + bar_gap)
            w = value * unit
            # square at the baseline, 4px rounded data-end
            path = (f"M{left},{by:.1f} h{w - r:.1f} a{r},{r} 0 0 1 {r},{r} v{bar_h - 2 * r} "
                    f"a{r},{r} 0 0 1 -{r},{r} h-{w - r:.1f} z")
            parts.append(f'<path d="{path}" fill="{series_colour(i)}"><title>{_esc(tooltip)}</title></path>')
            parts.append(f'<text x="{left + w + 5:.1f}" y="{by + bar_h - 1:.1f}" font-size="11" '
                         f'class="t-secondary" style="font-variant-numeric: tabular-nums">{value}</text>')

    parts.append(f'<line x1="{left}" y1="{plot_bottom}" x2="{left + scale_max * unit}" y2="{plot_bottom}" '
                 'stroke="var(--axis)" stroke-width="1"/>')
    for v in range(0, scale_max + 1, 2):
        parts.append(f'<text x="{left + v * unit:.1f}" y="{plot_bottom + 16}" text-anchor="middle" font-size="12" '
                     f'class="t-secondary" style="font-variant-numeric: tabular-nums">{v}</text>')
    if axis_title:
        parts.append(f'<text x="{left + scale_max / 2 * unit:.1f}" y="{plot_bottom + 34}" text-anchor="middle" '
                     f'font-size="12" class="t-secondary">{_esc(axis_title)}</text>')
    return _svg(width, height, parts, description)


def legend(names: list) -> str:
    """Colour key: one swatch per series, in series order."""
    items = [f'<span><span class="swatch" style="background: {series_colour(i)}"></span>{_esc(name)}</span>'
             for i, name in enumerate(names)]
    return f'<div class="legend">{"".join(items)}</div>'


def table(head: list, rows: list) -> str:
    """Table with a header row; the first cell of each row is styled as its heading."""
    th = "".join(f"<th>{_esc(h)}</th>" for h in head)
    body = []
    for row in rows:
        cells = [f"<th>{_esc(row[0])}</th>"] + [f'<td class="num">{_esc(c)}</td>' for c in row[1:]]
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"
