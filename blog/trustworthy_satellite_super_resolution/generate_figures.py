#!/usr/bin/env python3
"""Generate article figures from evaluation.json and saved diagnostics."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 760, 430
INK, MUTED, GRID, PAPER = "#101010", "#666666", "#d8d8d8", "#ffffff"
BLUE, ORANGE, GREEN = "#2563eb", "#d97706", "#15803d"


def svg_start(title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(desc)}</desc>',
        '<style>text{font-family:Arial,sans-serif;fill:#101010}.title{font-size:20px;font-weight:700}.sub{font-size:11px;fill:#666}.tick{font-size:10px;fill:#666}.label{font-size:11px;font-weight:600}.value{font-size:10px;font-weight:700}.grid{stroke:#d8d8d8;stroke-width:1}</style>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{PAPER}"/>',
        f'<text x="42" y="35" class="title">{html.escape(title)}</text>',
        f'<text x="42" y="55" class="sub">{html.escape(desc)}</text>',
    ]


def save_svg(path: Path, lines: list[str]) -> None:
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def grouped_chart(data: dict, output: Path) -> None:
    cases = data["cases"]
    metrics = [
        ("SAM mean (deg)", [case["spectral_angle_degrees"]["mean"] for case in cases], BLUE),
        ("NDVI MAE (×100)", [100 * case["ndvi_downsample_error"]["mae"] for case in cases], GREEN),
        ("Gradient ratio", [case["learned_vs_bilinear"]["gradient_energy_ratio"] for case in cases], ORANGE),
    ]
    lines = svg_start(
        "Observation-consistency diagnostics",
        "Two bundled examples only; no independent high-resolution truth",
    )
    left, top, plot_w, plot_h, max_y = 72, 90, 640, 260, 8
    for value in (0, 2, 4, 6, 8):
        y = top + plot_h - value / max_y * plot_h
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" class="grid"/>', f'<text x="62" y="{y+4:.1f}" text-anchor="end" class="tick">{value}</text>']
    centres = (left + plot_w * 0.27, left + plot_w * 0.73)
    for case_index, case in enumerate(cases):
        centre = centres[case_index]
        for metric_index, (_, values, colour) in enumerate(metrics):
            value = values[case_index]
            x = centre + (metric_index - 1) * 58 - 20
            height = value / max_y * plot_h
            y = top + plot_h - height
            lines += [f'<rect x="{x:.1f}" y="{y:.1f}" width="40" height="{height:.1f}" fill="{colour}"/>', f'<text x="{x+20:.1f}" y="{y-7:.1f}" text-anchor="middle" class="value">{value:.2f}</text>']
        lines.append(f'<text x="{centre:.1f}" y="374" text-anchor="middle" class="label">{case["name"].title()}</text>')
    legend_x = 255
    for index, (label, _, colour) in enumerate(metrics):
        x = legend_x + index * 165
        lines += [f'<rect x="{x}" y="397" width="11" height="11" fill="{colour}"/>', f'<text x="{x+17}" y="406" class="tick">{html.escape(label)}</text>']
    save_svg(output, lines)


def spread_chart(data: dict, output: Path) -> None:
    cases = data["cases"]
    lines = svg_start(
        "Stochastic spread and residual association",
        "Five stochastic passes at 25 DDIM steps; spread is not calibrated uncertainty",
    )
    left, top, plot_w, plot_h = 72, 90, 640, 260
    max_spread = 0.05
    for value in (0, 0.01, 0.02, 0.03, 0.04, 0.05):
        y = top + plot_h - value / max_spread * plot_h
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" class="grid"/>', f'<text x="62" y="{y+4:.1f}" text-anchor="end" class="tick">{value:.2f}</text>']
    for index, case in enumerate(cases):
        centre = left + plot_w * (0.28 if index == 0 else 0.72)
        mean = case["stochastic_spread"]["mean_2sigma"]
        p95 = case["stochastic_spread"]["p95_2sigma"]
        for offset, value, colour, label in ((-28, mean, BLUE, "Mean"), (28, p95, ORANGE, "p95")):
            h = value / max_spread * plot_h
            x, y = centre + offset - 22, top + plot_h - h
            lines += [f'<rect x="{x:.1f}" y="{y:.1f}" width="44" height="{h:.1f}" fill="{colour}"/>', f'<text x="{x+22:.1f}" y="{y-7:.1f}" text-anchor="middle" class="value">{value:.3f}</text>']
        corr = case["stochastic_spread"]["correlation_with_absolute_residual"]
        lines += [f'<text x="{centre:.1f}" y="374" text-anchor="middle" class="label">{case["name"].title()}</text>', f'<text x="{centre:.1f}" y="390" text-anchor="middle" class="tick">spread-residual r = {corr:.2f}</text>']
    lines += [f'<rect x="555" y="404" width="11" height="11" fill="{BLUE}"/><text x="572" y="413" class="tick">Mean 2σ spread</text>', f'<rect x="650" y="404" width="11" height="11" fill="{ORANGE}"/><text x="667" y="413" class="tick">p95</text>']
    save_svg(output, lines)


def comparison_panel(input_dir: Path, output: Path) -> None:
    cell, label_h = 240, 28
    canvas = Image.new("RGB", (cell * 4, (cell + label_h) * 2), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    labels = ("Observed LR", "Bilinear ×4", "Learned ×4", "2σ spread")
    for row, case in enumerate(("rural", "urban")):
        for column, suffix in enumerate(("lr", "bilinear", "learned", "spread")):
            image = Image.open(input_dir / f"{case}_{suffix}.png").convert("RGB")
            image = image.resize((cell, cell), Image.Resampling.BICUBIC)
            x, y = column * cell, row * (cell + label_h)
            canvas.paste(image, (x, y))
            draw.rectangle((x, y + cell, x + cell, y + cell + label_h), fill="white")
            draw.text((x + 8, y + cell + 8), f"{case.upper()} | {labels[column]}", fill="black", font=font)
            draw.rectangle((x, y, x + cell - 1, y + cell + label_h - 1), outline="#d8d8d8")
    canvas.save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.evaluation.read_text(encoding="utf-8"))
    grouped_chart(data, args.output_dir / "consistency_diagnostics.svg")
    spread_chart(data, args.output_dir / "stochastic_spread.svg")
    comparison_panel(args.output_dir, args.output_dir / "comparison_panel.png")


if __name__ == "__main__":
    main()
