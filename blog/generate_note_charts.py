#!/usr/bin/env python3
"""Generate monochrome SVG charts for research notes 001-003 (house style of note 005).

Dependency-free. Reads measured JSON evidence where it exists:
  - blog/scaling_geospatial_deep_learning/single_gpu_benchmark.json
  - blog/scaling_geospatial_deep_learning/historical_benchmark.json
  - blog/trustworthy_satellite_super_resolution/evaluation.json
Note-001 values are transcribed from the v2.0.0 fold-5 benchmark report.
"""

import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

STYLE = """  <style>
    .ax    { stroke: #cfcfcf; stroke-width: 1; }
    .grid  { stroke: #e9e9e9; stroke-width: 1; }
    .lbl   { font: 13px -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #6b6b6b; }
    .val   { font: 12px -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #0a0a0a; }
    .ttl   { font: 600 14px -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: #0a0a0a; }
    .s     { fill: none; stroke: #0a0a0a; stroke-width: 2; }
    .mk    { fill: #ffffff; stroke: #0a0a0a; stroke-width: 1.6; }
    .bar   { fill: #0a0a0a; }
    .bar2  { fill: #ffffff; stroke: #0a0a0a; stroke-width: 1.6; }
  </style>
"""


def svg_open(w: int, h: int, aria: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="{aria}">\n  <title>{title}</title>\n'
        + STYLE
        + f'  <rect width="{w}" height="{h}" fill="#ffffff"/>\n'
    )


def write(name: str, folder: str, content: str) -> None:
    path = os.path.join(ROOT, folder, name)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print('wrote', os.path.join(folder, name))


# ---------------------------------------------------------------- hbar charts
def hbar_chart(
    title: str, aria: str, rows: list[tuple[str, float, str]], xmax: float,
    gridvals: list[float], footer: str | None = None, x0: int = 250, w: int = 760,
) -> str:
    bar_h, row_h, top = 20, 33, 52
    x1 = w - 78
    h = top + row_h * len(rows) + (44 if footer else 26)
    out = svg_open(w, h, aria, title)
    out += f'  <text class="ttl" x="20" y="28">{title}</text>\n'
    plot_bottom = top + row_h * len(rows) - 8
    for gv in gridvals:
        gx = x0 + (x1 - x0) * gv / xmax
        out += f'  <line class="grid" x1="{gx:.0f}" y1="{top - 10}" x2="{gx:.0f}" y2="{plot_bottom}"/>\n'
        out += f'  <text class="lbl" x="{gx:.0f}" y="{plot_bottom + 16}" text-anchor="middle">{gv:g}</text>\n'
    out += f'  <line class="ax" x1="{x0}" y1="{top - 10}" x2="{x0}" y2="{plot_bottom}"/>\n'
    for i, (label, value, vtxt) in enumerate(rows):
        y = top + i * row_h
        bw = (x1 - x0) * value / xmax
        out += f'  <text class="lbl" x="{x0 - 8}" y="{y + bar_h - 6}" text-anchor="end">{label}</text>\n'
        out += f'  <rect class="bar" x="{x0}" y="{y}" width="{bw:.1f}" height="{bar_h}"/>\n'
        out += f'  <text class="val" x="{x0 + bw + 7:.1f}" y="{y + bar_h - 5}">{vtxt}</text>\n'
    if footer:
        out += f'  <text class="lbl" x="20" y="{h - 10}">{footer}</text>\n'
    return out + '</svg>\n'


def paired_hbar_chart(
    title: str, aria: str,
    rows: list[tuple[str, float, float, str, str]],  # label, v_rural_norm, v_urban_norm, txt_r, txt_u
    legend: tuple[str, str], footer: str | None = None, x0: int = 236, w: int = 760,
) -> str:
    bar_h, pair_gap, row_h, top = 14, 3, 48, 58
    x1 = w - 84
    h = top + row_h * len(rows) + (40 if footer else 22)
    out = svg_open(w, h, aria, title)
    out += f'  <text class="ttl" x="20" y="28">{title}</text>\n'
    # legend
    out += f'  <rect class="bar" x="{x1 - 210}" y="16" width="16" height="12"/>\n'
    out += f'  <text class="lbl" x="{x1 - 188}" y="27">{legend[0]}</text>\n'
    out += f'  <rect class="bar2" x="{x1 - 110}" y="16" width="16" height="12"/>\n'
    out += f'  <text class="lbl" x="{x1 - 88}" y="27">{legend[1]}</text>\n'
    plot_bottom = top + row_h * len(rows) - 10
    out += f'  <line class="ax" x1="{x0}" y1="{top - 10}" x2="{x0}" y2="{plot_bottom}"/>\n'
    for i, (label, vr, vu, tr, tu) in enumerate(rows):
        y = top + i * row_h
        wr = (x1 - x0) * vr
        wu = (x1 - x0) * vu
        out += f'  <text class="lbl" x="{x0 - 8}" y="{y + bar_h + 2}" text-anchor="end">{label}</text>\n'
        out += f'  <rect class="bar" x="{x0}" y="{y}" width="{wr:.1f}" height="{bar_h}"/>\n'
        out += f'  <text class="val" x="{x0 + wr + 7:.1f}" y="{y + bar_h - 3}">{tr}</text>\n'
        y2 = y + bar_h + pair_gap
        out += f'  <rect class="bar2" x="{x0}" y="{y2}" width="{wu:.1f}" height="{bar_h}"/>\n'
        out += f'  <text class="val" x="{x0 + wu + 7:.1f}" y="{y2 + bar_h - 3}">{tu}</text>\n'
    if footer:
        out += f'  <text class="lbl" x="20" y="{h - 10}">{footer}</text>\n'
    return out + '</svg>\n'


# ---------------------------------------------------------------- vbar groups
def grouped_vbar_chart(
    title: str, aria: str, groups: list[str], series_a: list[float], series_b: list[float],
    labels_a: list[str], labels_b: list[str], ymax: float, ygrid: list[float],
    legend: tuple[str, str], xlabel: str, p95_a: list[float] | None = None,
    p95_b: list[float] | None = None, w: int = 760, h: int = 430,
) -> str:
    px0, py0, px1, py1 = 70, 46, w - 30, h - 56
    out = svg_open(w, h, aria, title)
    out += f'  <text class="ttl" x="20" y="26">{title}</text>\n'

    def y(v: float) -> float:
        return py1 - (py1 - py0) * v / ymax

    for gv in ygrid:
        out += f'  <line class="grid" x1="{px0}" y1="{y(gv):.0f}" x2="{px1}" y2="{y(gv):.0f}"/>\n'
        out += f'  <text class="lbl" x="{px0 - 8}" y="{y(gv) + 4:.0f}" text-anchor="end">{gv:g}</text>\n'
    out += f'  <line class="ax" x1="{px0}" y1="{py0 - 6}" x2="{px0}" y2="{py1}"/>\n'
    out += f'  <line class="ax" x1="{px0}" y1="{py1}" x2="{px1}" y2="{py1}"/>\n'
    n = len(groups)
    bw, gap = 58, 12
    for i, g in enumerate(groups):
        cx = px0 + (px1 - px0) * (i + 0.5) / n
        xa, xb = cx - bw - gap / 2, cx + gap / 2
        ya, yb = y(series_a[i]), y(series_b[i])
        out += f'  <rect class="bar" x="{xa:.0f}" y="{ya:.0f}" width="{bw}" height="{py1 - ya:.0f}"/>\n'
        out += f'  <rect class="bar2" x="{xb:.0f}" y="{yb:.0f}" width="{bw}" height="{py1 - yb:.0f}"/>\n'
        out += f'  <text class="val" x="{xa + bw / 2:.0f}" y="{ya - 7:.0f}" text-anchor="middle">{labels_a[i]}</text>\n'
        out += f'  <text class="val" x="{xb + bw / 2:.0f}" y="{yb - 7:.0f}" text-anchor="middle">{labels_b[i]}</text>\n'
        if p95_a:
            out += f'  <line x1="{xa:.0f}" y1="{y(p95_a[i]):.1f}" x2="{xa + bw:.0f}" y2="{y(p95_a[i]):.1f}" stroke="#6b6b6b" stroke-width="1.6" stroke-dasharray="3 3"/>\n'
        if p95_b:
            out += f'  <line x1="{xb:.0f}" y1="{y(p95_b[i]):.1f}" x2="{xb + bw:.0f}" y2="{y(p95_b[i]):.1f}" stroke="#6b6b6b" stroke-width="1.6" stroke-dasharray="3 3"/>\n'
        out += f'  <text class="lbl" x="{cx:.0f}" y="{py1 + 20}" text-anchor="middle">{g}</text>\n'
    out += f'  <text class="lbl" x="{(px0 + px1) / 2:.0f}" y="{h - 12}" text-anchor="middle">{xlabel}</text>\n'
    # legend
    out += f'  <rect class="bar" x="{px0 + 14}" y="{py0 + 2}" width="16" height="12"/>\n'
    out += f'  <text class="lbl" x="{px0 + 36}" y="{py0 + 13}">{legend[0]}</text>\n'
    out += f'  <rect class="bar2" x="{px0 + 118}" y="{py0 + 2}" width="16" height="12"/>\n'
    out += f'  <text class="lbl" x="{px0 + 140}" y="{py0 + 13}">{legend[1]}</text>\n'
    return out + '</svg>\n'


# ------------------------------------------------------------------ line chart
def line_chart(
    title: str, aria: str, series: list[dict], xticks: list[float], yticks: list[float],
    xmax: float, ymax: float, xlabel: str, xmin: float = 0.0, ymin: float = 0.0,
    annotations: list[str] | None = None, w: int = 760, h: int = 430,
) -> str:
    px0, py0, px1, py1 = 70, 46, w - 30, h - 56
    out = svg_open(w, h, aria, title)
    out += f'  <text class="ttl" x="20" y="26">{title}</text>\n'

    def X(v: float) -> float:
        return px0 + (px1 - px0) * (v - xmin) / (xmax - xmin)

    def Y(v: float) -> float:
        return py1 - (py1 - py0) * (v - ymin) / (ymax - ymin)

    for gv in yticks:
        out += f'  <line class="grid" x1="{px0}" y1="{Y(gv):.0f}" x2="{px1}" y2="{Y(gv):.0f}"/>\n'
        out += f'  <text class="lbl" x="{px0 - 8}" y="{Y(gv) + 4:.0f}" text-anchor="end">{gv:g}</text>\n'
    out += f'  <line class="ax" x1="{px0}" y1="{py0 - 6}" x2="{px0}" y2="{py1}"/>\n'
    out += f'  <line class="ax" x1="{px0}" y1="{py1}" x2="{px1}" y2="{py1}"/>\n'
    for xt in xticks:
        out += f'  <text class="lbl" x="{X(xt):.0f}" y="{py1 + 20}" text-anchor="middle">{xt:g}</text>\n'
    out += f'  <text class="lbl" x="{(px0 + px1) / 2:.0f}" y="{h - 12}" text-anchor="middle">{xlabel}</text>\n'
    ly = py0 + 12
    for s in series:
        pts = ' '.join(f'{X(x):.1f},{Y(v):.1f}' for x, v in s['data'])
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get('dash') else ''
        out += f'  <polyline class="s"{dash} points="{pts}"/>\n'
        for x, v in s.get('markers', []):
            out += f'  <circle class="mk" cx="{X(x):.1f}" cy="{Y(v):.1f}" r="3.2"/>\n'
        if s.get('label'):
            out += f'  <line class="s"{dash} x1="{px1 - 220}" y1="{ly}" x2="{px1 - 184}" y2="{ly}"/>\n'
            out += f'  <text class="lbl" x="{px1 - 176}" y="{ly + 4}">{s["label"]}</text>\n'
            ly += 22
    for a in annotations or []:
        out += '  ' + a + '\n'
    return out + '</svg>\n'


# ============================================================== note 001 charts
F1 = 'super_resolution_crop_foundation'
fold5 = [
    ('Overall pixel accuracy', 0.7997, '0.7997'),
    ('Macro IoU (incl. background)', 0.4879, '0.4879'),
    ('Foreground macro IoU', 0.4743, '0.4743'),
    ('Macro F1', 0.6142, '0.6142'),
    ('Boundary F1 (1-px tolerance)', 0.8298, '0.8298'),
    ('Crop-presence macro F1', 0.2455, '0.2455'),
    ('Crop-presence micro F1', 0.4607, '0.4607'),
    ('Pixel top-label ECE (lower is better)', 0.0733, '0.0733'),
    ('SPOT diagnostic SSIM', 0.3097, '0.3097'),
]
write('fold5_metrics.svg', F1, hbar_chart(
    'Fold-5 internal benchmark, v2.0.0 checkpoint - measured, one seed',
    'Horizontal bar chart of the measured fold-5 internal metrics for the v2.0.0 checkpoint',
    fold5, 1.0, [0, 0.2, 0.4, 0.6, 0.8, 1.0],
    footer='SPOT diagnostic PSNR: 11.38 dB (decibel scale, not shown as a bar). All values from the v2.0.0 benchmark report.',
))

classes = [
    ('Corn', 0.8079, '0.8079 &#183; 620,357 px'),
    ('Soft winter wheat', 0.7812, '0.7812 &#183; 580,631 px'),
    ('Winter rapeseed', 0.7790, '0.7790 &#183; 157,965 px'),
    ('Beet', 0.7645, '0.7645 &#183; 67,567 px'),
    ('Soybeans', 0.7587, '0.7587 &#183; 71,771 px'),
    ('Winter triticale', 0.1294, '0.1294 &#183; 53,892 px'),
    ('Mixed cereal', 0.1052, '0.1052 &#183; 49,537 px'),
    ('Sorghum', 0.0184, '0.0184 &#183; 53,295 px'),
]
write('class_iou.svg', F1, hbar_chart(
    'Per-class IoU with 10 m pixel support - measured, fold 5',
    'Horizontal bar chart of per-class IoU for eight crop classes with pixel support labels',
    classes, 1.0, [0, 0.2, 0.4, 0.6, 0.8, 1.0], x0=190,
    footer='Support alone does not explain the ordering: beet and soybeans outperform triticale and sorghum at similar support.',
))

# ============================================================== note 002 charts
F2 = 'scaling_geospatial_deep_learning'
with open(os.path.join(ROOT, F2, 'single_gpu_benchmark.json'), encoding='utf-8') as f:
    bench = json.load(f)['results']
with open(os.path.join(ROOT, F2, 'historical_benchmark.json'), encoding='utf-8') as f:
    hist = json.load(f)

fp32 = {r['batch_size']: r for r in bench if r['precision'] == 'fp32'}
amp = {r['batch_size']: r for r in bench if r['precision'] == 'amp_fp16'}
batches = [1, 2, 4]

write('throughput_by_batch.svg', F2, grouped_vbar_chart(
    'Measured compute-only throughput, RTX 4080 (samples/s)',
    'Grouped bar chart of measured FP32 and AMP FP16 throughput at batch sizes one, two and four',
    [str(b) for b in batches],
    [fp32[b]['throughput_samples_s'] for b in batches],
    [amp[b]['throughput_samples_s'] for b in batches],
    [f'{fp32[b]["throughput_samples_s"]:.1f}' for b in batches],
    [f'{amp[b]["throughput_samples_s"]:.1f}' for b in batches],
    60, [0, 10, 20, 30, 40, 50, 60], ('FP32', 'AMP FP16'), 'batch size',
))

write('memory_by_batch.svg', F2, grouped_vbar_chart(
    'Measured peak allocated GPU memory (GiB)',
    'Grouped bar chart of measured FP32 and AMP FP16 peak allocated memory at batch sizes one, two and four',
    [str(b) for b in batches],
    [fp32[b]['peak_allocated_gib'] for b in batches],
    [amp[b]['peak_allocated_gib'] for b in batches],
    [f'{fp32[b]["peak_allocated_gib"]:.2f}' for b in batches],
    [f'{amp[b]["peak_allocated_gib"]:.2f}' for b in batches],
    3.6, [0, 1, 2, 3], ('FP32', 'AMP FP16'), 'batch size',
))

write('step_latency_by_batch.svg', F2, grouped_vbar_chart(
    'Measured optimisation-step latency (ms); dashes mark p95',
    'Grouped bar chart of measured FP32 and AMP FP16 median step latency with p95 markers at batch sizes one, two and four',
    [str(b) for b in batches],
    [fp32[b]['median_step_ms'] for b in batches],
    [amp[b]['median_step_ms'] for b in batches],
    [f'{fp32[b]["median_step_ms"]:.2f}' for b in batches],
    [f'{amp[b]["median_step_ms"]:.2f}' for b in batches],
    115, [0, 25, 50, 75, 100], ('FP32 median', 'AMP FP16 median'), 'batch size',
    p95_a=[fp32[b]['p95_step_ms'] for b in batches],
    p95_b=[amp[b]['p95_step_ms'] for b in batches],
))

best_so_far, best = [], 0.0
for e in hist['epochs']:
    best = max(best, e['validation_macro_iou'])
    best_so_far.append((e['epoch'], best))
write('quality_by_epoch_budget.svg', F2, line_chart(
    'Best validation macro IoU available at each epoch - measured, one run',
    'Line chart of the best validation macro IoU available at each epoch of the measured 50-epoch run',
    [{'data': best_so_far, 'markers': [(49, 0.5112)], 'label': None}],
    [0, 10, 20, 30, 40, 50], [0, 0.1, 0.2, 0.3, 0.4, 0.5], 50, 0.55,
    'epoch',
    annotations=['<text class="val" x="620" y="86">0.5112 at epoch 49</text>'],
))

amdahl = {}
for s in (0.10, 0.20, 0.35):
    amdahl[s] = [(n, 1.0 / (s + (1.0 - s) / n)) for n in range(1, 9)]
write('analytical_ddp_scaling.svg', F2, line_chart(
    'Amdahl speedup bound by serial fraction - analytical, not measured',
    'Line chart of analytical Amdahl speedup curves for serial fractions of ten, twenty and thirty-five percent',
    [
        {'data': amdahl[0.10], 'markers': [(n, v) for n, v in amdahl[0.10] if n in (2, 4, 8)], 'label': '10% serial', 'dash': None},
        {'data': amdahl[0.20], 'markers': [(n, v) for n, v in amdahl[0.20] if n in (2, 4, 8)], 'label': '20% serial', 'dash': '9 5'},
        {'data': amdahl[0.35], 'markers': [(n, v) for n, v in amdahl[0.35] if n in (2, 4, 8)], 'label': '35% serial', 'dash': '2.5 4.5'},
    ],
    [1, 2, 3, 4, 5, 6, 7, 8], [1, 2, 3, 4, 5], 8, 5.2, 'GPUs (N)', xmin=1, ymin=0.6,
))

# ============================================================== note 003 charts
F3 = 'trustworthy_satellite_super_resolution'
with open(os.path.join(ROOT, F3, 'evaluation.json'), encoding='utf-8') as f:
    ev = json.load(f)
rc = {c['name']: c for c in ev['cases']}
r, u = rc['rural'], rc['urban']

diag = [
    ('Mean spectral angle', r['spectral_angle_degrees']['mean'], u['spectral_angle_degrees']['mean'], '&#176;', 3),
    ('p95 spectral angle', r['spectral_angle_degrees']['p95'], u['spectral_angle_degrees']['p95'], '&#176;', 3),
    ('NDVI MAE (box-averaged)', r['ndvi_downsample_error']['mae'], u['ndvi_downsample_error']['mae'], '', 4),
    ('p95 absolute NDVI error', r['ndvi_downsample_error']['p95_absolute'], u['ndvi_downsample_error']['p95_absolute'], '', 4),
    ('Largest band MAE (B08)', max(r['downsample_consistency']['mae_by_band']), max(u['downsample_consistency']['mae_by_band']), '', 5),
    ('Learned/bilinear gradient energy', r['learned_vs_bilinear']['gradient_energy_ratio'], u['learned_vs_bilinear']['gradient_energy_ratio'], '&#215;', 2),
]
rows = []
for label, vr, vu, unit, prec in diag:
    m = max(vr, vu)
    rows.append((label, vr / m, vu / m, f'{vr:.{prec}f}{unit}', f'{vu:.{prec}f}{unit}'))
write('consistency_diagnostics.svg', F3, paired_hbar_chart(
    'Observation-consistency diagnostics - measured, two examples',
    'Paired bar chart of six measured observation-consistency diagnostics for the rural and urban examples, each row normalised to its own maximum with true values labelled',
    rows, ('Rural', 'Urban'),
    footer='Bars are normalised per row to the row maximum; read values from the labels. Units differ per row.',
))

spread_rows = [
    ('Mean 2&#963; spread', r['stochastic_spread']['mean_2sigma'] / u['stochastic_spread']['mean_2sigma'], 1.0,
     f"{r['stochastic_spread']['mean_2sigma']:.4f}", f"{u['stochastic_spread']['mean_2sigma']:.4f}"),
    ('p95 2&#963; spread', r['stochastic_spread']['p95_2sigma'] / u['stochastic_spread']['p95_2sigma'], 1.0,
     f"{r['stochastic_spread']['p95_2sigma']:.4f}", f"{u['stochastic_spread']['p95_2sigma']:.4f}"),
]
write('stochastic_spread.svg', F3, paired_hbar_chart(
    'Stochastic spread across five 25-step passes - measured',
    'Paired bar chart of mean and p95 two-sigma stochastic spread for the rural and urban examples, each row normalised to the urban value with true values labelled',
    spread_rows, ('Rural', 'Urban'),
    footer='Bars normalised per row to the urban value. Spread-residual Pearson r: 0.375 (rural), 0.421 (urban). Not calibrated uncertainty.',
))
print('done')
