#!/usr/bin/env python3
"""Generate dependency-free SVG charts from benchmark JSON files."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


WIDTH, HEIGHT = 760, 430
INK, MUTED, GRID, PAPER = "#101010", "#666666", "#d8d8d8", "#ffffff"
BLUE, ORANGE, GREEN = "#2563eb", "#d97706", "#15803d"


def svg_start(title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(desc)}</desc>',
        '<style>text{font-family:Arial,sans-serif;fill:#101010}.title{font-size:20px;font-weight:700}.sub{font-size:11px;fill:#666}.tick{font-size:10px;fill:#666}.label{font-size:11px;font-weight:600}.value{font-size:10px;font-weight:700}.grid{stroke:#d8d8d8;stroke-width:1}.axis{stroke:#101010;stroke-width:1.3}.line{fill:none;stroke-width:2.5}.dash{stroke-dasharray:6 5}</style>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{PAPER}"/>',
        f'<text x="42" y="35" class="title">{html.escape(title)}</text>',
        f'<text x="42" y="55" class="sub">{html.escape(desc)}</text>',
    ]


def save(path: Path, lines: list[str]) -> None:
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def throughput_chart(data: dict, output: Path) -> None:
    rows = data["results"]
    lines = svg_start(
        "Single-GPU training-step throughput",
        "Measured RTX 4080 synthetic compute benchmark; higher is better; data loading excluded",
    )
    left, top, plot_w, plot_h = 72, 90, 640, 265
    max_y = 60
    for value in range(0, 61, 10):
        y = top + plot_h - value / max_y * plot_h
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" class="grid"/>', f'<text x="62" y="{y+4:.1f}" text-anchor="end" class="tick">{value}</text>']
    batches = [1, 2, 4]
    group_w, bar_w = plot_w / len(batches), 48
    colours = {"fp32": ORANGE, "amp_fp16": BLUE}
    labels = {"fp32": "FP32", "amp_fp16": "AMP FP16"}
    for index, batch in enumerate(batches):
        centre = left + group_w * (index + 0.5)
        for offset, precision in ((-28, "fp32"), (28, "amp_fp16")):
            row = next(r for r in rows if r["batch_size"] == batch and r["precision"] == precision)
            value = row["throughput_samples_s"]
            height = value / max_y * plot_h
            x = centre + offset - bar_w / 2
            y = top + plot_h - height
            lines += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{height:.1f}" fill="{colours[precision]}"/>', f'<text x="{x+bar_w/2:.1f}" y="{y-7:.1f}" text-anchor="middle" class="value">{value:.1f}</text>']
        lines.append(f'<text x="{centre:.1f}" y="377" text-anchor="middle" class="label">Batch {batch}</text>')
    lines += [f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" class="axis"/>', '<text x="18" y="230" transform="rotate(-90 18 230)" class="label">Samples per second</text>', f'<rect x="500" y="395" width="12" height="12" fill="{ORANGE}"/><text x="518" y="405" class="tick">FP32</text>', f'<rect x="575" y="395" width="12" height="12" fill="{BLUE}"/><text x="593" y="405" class="tick">AMP FP16</text>']
    save(output, lines)


def memory_chart(data: dict, output: Path) -> None:
    rows = data["results"]
    lines = svg_start(
        "Peak allocated GPU memory",
        "Measured RTX 4080 synthetic benchmark. FP32 GiB: 0.87, 1.68, 3.29. AMP FP16 GiB: 0.67, 1.28, 2.50.",
    )
    left, top, plot_w, plot_h = 72, 90, 640, 265
    max_y = 4
    for value in range(0, 5):
        y = top + plot_h - value / max_y * plot_h
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" class="grid"/>', f'<text x="62" y="{y+4:.1f}" text-anchor="end" class="tick">{value}</text>']
    colours = {"fp32": ORANGE, "amp_fp16": BLUE}
    for precision in ("fp32", "amp_fp16"):
        points = []
        for index, batch in enumerate((1, 2, 4)):
            row = next(r for r in rows if r["batch_size"] == batch and r["precision"] == precision)
            value = row["peak_allocated_gib"]
            x = left + plot_w * index / 2
            y = top + plot_h - value / max_y * plot_h
            points.append((x, y, value))
        path = " ".join(("M" if i == 0 else "L") + f" {x:.1f} {y:.1f}" for i, (x, y, _) in enumerate(points))
        dash = "" if precision == "fp32" else ' stroke-dasharray="8 5"'
        lines.append(f'<path d="{path}" class="line" stroke="{colours[precision]}"{dash}/>')
        for x, y, value in points:
            shape = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{colours[precision]}"/>' if precision == "fp32" else f'<rect x="{x-5:.1f}" y="{y-5:.1f}" width="10" height="10" fill="{colours[precision]}"/>'
            lines += [shape, f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" class="value">{value:.2f}</text>']
    for index, batch in enumerate((1, 2, 4)):
        x = left + plot_w * index / 2
        lines.append(f'<text x="{x:.1f}" y="377" text-anchor="middle" class="label">Batch {batch}</text>')
    lines += ['<text x="18" y="230" transform="rotate(-90 18 230)" class="label">Peak allocated memory (GiB)</text>', f'<circle cx="506" cy="401" r="6" fill="{ORANGE}"/><text x="518" y="405" class="tick">FP32</text>', f'<rect x="575" y="395" width="12" height="12" fill="{BLUE}"/><text x="593" y="405" class="tick">AMP FP16</text>']
    save(output, lines)


def convergence_chart(data: dict, output: Path) -> None:
    epochs = data["epochs"]
    best = []
    current = 0.0
    for row in epochs:
        current = max(current, row["validation_macro_iou"])
        best.append((row["epoch"], current))
    lines = svg_start(
        "Checkpoint quality versus training budget",
        "Measured historical run; best validation macro IoU available by each epoch",
    )
    left, top, plot_w, plot_h = 72, 90, 640, 265
    min_y, max_y = 0.1, 0.55
    for value in (0.1, 0.2, 0.3, 0.4, 0.5):
        y = top + plot_h - (value - min_y) / (max_y - min_y) * plot_h
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" class="grid"/>', f'<text x="62" y="{y+4:.1f}" text-anchor="end" class="tick">{value:.1f}</text>']
    points = []
    for epoch, value in best:
        x = left + (epoch - 1) / 49 * plot_w
        y = top + plot_h - (value - min_y) / (max_y - min_y) * plot_h
        points.append((x, y))
    path = " ".join(("M" if i == 0 else "L") + f" {x:.1f} {y:.1f}" for i, (x, y) in enumerate(points))
    lines.append(f'<path d="{path}" class="line" stroke="{GREEN}"/>')
    for epoch in (1, 10, 20, 30, 40, 50):
        x = left + (epoch - 1) / 49 * plot_w
        lines.append(f'<text x="{x:.1f}" y="377" text-anchor="middle" class="tick">{epoch}</text>')
    best_epoch = data["summary"]["best_epoch"]
    best_value = data["summary"]["best_validation_macro_iou"]
    x = left + (best_epoch - 1) / 49 * plot_w
    y = top + plot_h - (best_value - min_y) / (max_y - min_y) * plot_h
    lines += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{GREEN}"/>', f'<text x="{x-8:.1f}" y="{y-12:.1f}" text-anchor="end" class="value">Best {best_value:.4f} at epoch {best_epoch}</text>', '<text x="392" y="407" text-anchor="middle" class="label">Epoch budget</text>', '<text x="18" y="230" transform="rotate(-90 18 230)" class="label">Best available macro IoU</text>']
    save(output, lines)


def scaling_chart(output: Path) -> None:
    lines = svg_start(
        "Analytical Amdahl strong-scaling sensitivity",
        "Not measured. Speedup at 8 GPUs: 4.71× (10% serial), 3.33× (20%), 2.32× (35%).",
    )
    left, top, plot_w, plot_h = 72, 90, 640, 265
    max_y = 8
    for value in (0, 2, 4, 6, 8):
        y = top + plot_h - value / max_y * plot_h
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" class="grid"/>', f'<text x="62" y="{y+4:.1f}" text-anchor="end" class="tick">{value}</text>']
    gpu_counts = (1, 2, 4, 8)
    scenarios = ((0.10, GREEN, "10% serial"), (0.20, BLUE, "20% serial"), (0.35, ORANGE, "35% serial"))
    for scenario_index, (serial, colour, _) in enumerate(scenarios):
        points = []
        for index, count in enumerate(gpu_counts):
            speedup = 1 / (serial + (1 - serial) / count)
            x = left + index / 3 * plot_w
            y = top + plot_h - speedup / max_y * plot_h
            points.append((x, y))
        path = " ".join(("M" if i == 0 else "L") + f" {x:.1f} {y:.1f}" for i, (x, y) in enumerate(points))
        dash_patterns = ("", ' stroke-dasharray="9 4"', ' stroke-dasharray="3 4"')
        lines.append(f'<path d="{path}" class="line" stroke="{colour}"{dash_patterns[scenario_index]}/>')
        for x, y in points:
            if scenario_index == 0:
                marker = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colour}"/>'
            elif scenario_index == 1:
                marker = f'<rect x="{x-4:.1f}" y="{y-4:.1f}" width="8" height="8" fill="{colour}"/>'
            else:
                marker = f'<path d="M {x:.1f} {y-5:.1f} L {x+5:.1f} {y+4:.1f} L {x-5:.1f} {y+4:.1f} Z" fill="{colour}"/>'
            lines.append(marker)
    ideal = [(left + i / 3 * plot_w, top + plot_h - n / max_y * plot_h) for i, n in enumerate(gpu_counts)]
    ideal_path = " ".join(("M" if i == 0 else "L") + f" {x:.1f} {y:.1f}" for i, (x, y) in enumerate(ideal))
    lines.append(f'<path d="{ideal_path}" class="line dash" stroke="{MUTED}"/>')
    for index, count in enumerate(gpu_counts):
        x = left + index / 3 * plot_w
        lines.append(f'<text x="{x:.1f}" y="377" text-anchor="middle" class="label">{count} GPU</text>')
    lines += ['<text x="18" y="230" transform="rotate(-90 18 230)" class="label">Theoretical speedup</text>', f'<line x1="390" y1="400" x2="414" y2="400" stroke="{GREEN}" stroke-width="3"/><text x="420" y="404" class="tick">10%</text>', f'<line x1="465" y1="400" x2="489" y2="400" stroke="{BLUE}" stroke-width="3"/><text x="495" y="404" class="tick">20%</text>', f'<line x1="540" y1="400" x2="564" y2="400" stroke="{ORANGE}" stroke-width="3"/><text x="570" y="404" class="tick">35% serial</text>', f'<line x1="645" y1="400" x2="669" y2="400" stroke="{MUTED}" stroke-width="2" stroke-dasharray="5 4"/><text x="675" y="404" class="tick">Ideal</text>']
    save(output, lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--microbenchmark", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    micro = json.loads(args.microbenchmark.read_text(encoding="utf-8"))
    historical = json.loads(args.historical.read_text(encoding="utf-8"))
    throughput_chart(micro, args.output_dir / "throughput_by_batch.svg")
    memory_chart(micro, args.output_dir / "memory_by_batch.svg")
    convergence_chart(historical, args.output_dir / "quality_by_epoch_budget.svg")
    scaling_chart(args.output_dir / "analytical_ddp_scaling.svg")


if __name__ == "__main__":
    main()
