"""Minimal SVG chart helpers (no matplotlib dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def save_bar_chart(
    path: Path,
    labels: Iterable[str],
    values: Iterable[float],
    title: str,
    xlabel: str = "",
    ylabel: str = "",
    width: int = 900,
    height: int = 500,
) -> None:
    labels = list(labels)
    values = [float(v) for v in values]
    if not labels:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return

    margin_left, margin_right, margin_top, margin_bottom = 70, 20, 40, 120
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_v = max(values) if max(values) > 0 else 1.0
    n = len(values)
    bar_w = plot_w / max(n, 1) * 0.75
    gap = plot_w / max(n, 1)

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{width/2}' y='24' text-anchor='middle' font-size='16' "
        f"font-family='Segoe UI, Arial'>{_esc(title)}</text>",
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' "
        f"y2='{margin_top+plot_h}' stroke='#333'/>",
        f"<line x1='{margin_left}' y1='{margin_top+plot_h}' x2='{margin_left+plot_w}' "
        f"y2='{margin_top+plot_h}' stroke='#333'/>",
    ]
    if ylabel:
        parts.append(
            f"<text x='16' y='{margin_top+plot_h/2}' transform="
            f"'rotate(-90 16,{margin_top+plot_h/2})' font-size='12' "
            f"font-family='Segoe UI, Arial'>{_esc(ylabel)}</text>"
        )
    for i, (label, value) in enumerate(zip(labels, values)):
        h = (value / max_v) * plot_h
        x = margin_left + i * gap + (gap - bar_w) / 2
        y = margin_top + plot_h - h
        parts.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' height='{h:.1f}' "
            f"fill='#4f46e5'/>"
        )
        parts.append(
            f"<text x='{x + bar_w/2:.1f}' y='{margin_top+plot_h+12}' "
            f"transform='rotate(45 {x + bar_w/2:.1f},{margin_top+plot_h+12})' "
            f"font-size='10' font-family='Segoe UI, Arial'>{_esc(label)}</text>"
        )
    if xlabel:
        parts.append(
            f"<text x='{width/2}' y='{height-12}' text-anchor='middle' font-size='12' "
            f"font-family='Segoe UI, Arial'>{_esc(xlabel)}</text>"
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def save_histogram(
    path: Path,
    values: Iterable[float],
    title: str,
    bins: int = 30,
    xlabel: str = "",
    ylabel: str = "Count",
) -> None:
    vals = [float(v) for v in values if v == v]
    if not vals:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return
    lo, hi = min(vals), max(vals)
    if lo == hi:
        hi = lo + 1
    width_bin = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        idx = min(int((v - lo) / width_bin), bins - 1)
        counts[idx] += 1
    labels = [f"{lo + i * width_bin:.0f}" for i in range(bins)]
    # Show fewer x labels for readability
    step = max(bins // 8, 1)
    slim_labels = [labels[i] if i % step == 0 else "" for i in range(bins)]
    save_bar_chart(path, slim_labels, counts, title, xlabel=xlabel, ylabel=ylabel)


def save_scatter(
    path: Path,
    x_values: Iterable[float],
    y_values: Iterable[float],
    title: str,
    xlabel: str,
    ylabel: str,
    max_points: int = 2500,
    width: int = 800,
    height: int = 500,
) -> None:
    points = [(float(x), float(y)) for x, y in zip(x_values, y_values) if x == x and y == y]
    if len(points) > max_points:
        step = len(points) / max_points
        points = [points[int(i * step)] for i in range(max_points)]
    if not points:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if min_x == max_x:
        max_x += 1
    if min_y == max_y:
        max_y += 1

    ml, mr, mt, mb = 70, 20, 40, 50
    pw, ph = width - ml - mr, height - mt - mb
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{width/2}' y='24' text-anchor='middle' font-size='16' "
        f"font-family='Segoe UI, Arial'>{_esc(title)}</text>",
        f"<line x1='{ml}' y1='{mt}' x2='{ml}' y2='{mt+ph}' stroke='#333'/>",
        f"<line x1='{ml}' y1='{mt+ph}' x2='{ml+pw}' y2='{mt+ph}' stroke='#333'/>",
        f"<text x='{width/2}' y='{height-12}' text-anchor='middle' font-size='12' "
        f"font-family='Segoe UI, Arial'>{_esc(xlabel)}</text>",
        f"<text x='16' y='{mt+ph/2}' transform='rotate(-90 16,{mt+ph/2})' font-size='12' "
        f"font-family='Segoe UI, Arial'>{_esc(ylabel)}</text>",
    ]
    for x, y in points:
        px = ml + (x - min_x) / (max_x - min_x) * pw
        py = mt + ph - (y - min_y) / (max_y - min_y) * ph
        parts.append(
            f"<circle cx='{px:.1f}' cy='{py:.1f}' r='2.2' fill='#4f46e5' fill-opacity='0.35'/>"
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def save_line_chart(
    path: Path,
    series: dict[str, list[tuple[str, float]]],
    title: str,
    xlabel: str = "Date",
    ylabel: str = "Value",
    width: int = 1000,
    height: int = 520,
) -> None:
    """series: {name: [(x_label, y), ...]}"""
    if not series:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return

    all_points = [pt for pts in series.values() for pt in pts]
    y_vals = [p[1] for p in all_points]
    min_y, max_y = min(y_vals), max(y_vals)
    if min_y == max_y:
        max_y += 1

    # Use union of x labels in order of first series with max length
    x_labels = []
    for pts in series.values():
        if len(pts) > len(x_labels):
            x_labels = [p[0] for p in pts]
    x_index = {label: i for i, label in enumerate(x_labels)}
    n = max(len(x_labels), 1)

    ml, mr, mt, mb = 70, 140, 40, 70
    pw, ph = width - ml - mr, height - mt - mb
    colors = ["#4f46e5", "#059669", "#d97706", "#dc2626", "#7c3aed"]

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{width/2}' y='24' text-anchor='middle' font-size='16' "
        f"font-family='Segoe UI, Arial'>{_esc(title)}</text>",
        f"<line x1='{ml}' y1='{mt}' x2='{ml}' y2='{mt+ph}' stroke='#333'/>",
        f"<line x1='{ml}' y1='{mt+ph}' x2='{ml+pw}' y2='{mt+ph}' stroke='#333'/>",
        f"<text x='{width/2}' y='{height-16}' text-anchor='middle' font-size='12' "
        f"font-family='Segoe UI, Arial'>{_esc(xlabel)}</text>",
        f"<text x='16' y='{mt+ph/2}' transform='rotate(-90 16,{mt+ph/2})' font-size='12' "
        f"font-family='Segoe UI, Arial'>{_esc(ylabel)}</text>",
    ]

    for idx, (name, pts) in enumerate(series.items()):
        color = colors[idx % len(colors)]
        coords = []
        for x_label, y in pts:
            if x_label not in x_index:
                continue
            px = ml + x_index[x_label] / max(n - 1, 1) * pw
            py = mt + ph - (y - min_y) / (max_y - min_y) * ph
            coords.append(f"{px:.1f},{py:.1f}")
        if coords:
            parts.append(
                f"<polyline fill='none' stroke='{color}' stroke-width='2' "
                f"points='{' '.join(coords)}'/>"
            )
        parts.append(
            f"<text x='{width-mr+10}' y='{mt + 20 + idx*18}' font-size='12' "
            f"fill='{color}' font-family='Segoe UI, Arial'>{_esc(name)}</text>"
        )

    # sparse x ticks
    tick_step = max(n // 8, 1)
    for i, label in enumerate(x_labels):
        if i % tick_step != 0:
            continue
        px = ml + i / max(n - 1, 1) * pw
        parts.append(
            f"<text x='{px:.1f}' y='{mt+ph+18}' text-anchor='middle' font-size='9' "
            f"font-family='Segoe UI, Arial'>{_esc(label)}</text>"
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")
