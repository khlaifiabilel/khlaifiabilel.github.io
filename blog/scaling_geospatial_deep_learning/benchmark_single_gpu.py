#!/usr/bin/env python3
"""Benchmark one complete synthetic training step for the crop model."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import platform
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import torch

from neuralq_crop_foundation.losses import MultiTaskCropLoss
from neuralq_crop_foundation.models import cropnet
from neuralq_crop_foundation.models.cropnet import CropSuperResolutionNet
from neuralq_crop_foundation.types import CropTargets, SentinelBatch


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nvidia_query(field: str) -> str | None:
    try:
        return subprocess.check_output(
            ["nvidia-smi", f"--query-gpu={field}", "--format=csv,noheader,nounits", "--id=0"],
            text=True,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def make_batch(batch_size: int, device: torch.device) -> tuple[SentinelBatch, CropTargets]:
    generator = torch.Generator(device=device).manual_seed(42 + batch_size)
    height = width = 32
    s2_times, s1_times = 16, 4

    s2 = torch.rand(batch_size, s2_times, 10, height, width, device=device, generator=generator)
    s1_asc = torch.randn(batch_size, s1_times, 2, height, width, device=device, generator=generator)
    s1_des = torch.randn(batch_size, s1_times, 2, height, width, device=device, generator=generator)
    s2_days = torch.linspace(1, 365, s2_times, device=device).expand(batch_size, -1)
    s1_days = torch.linspace(15, 350, s1_times, device=device).expand(batch_size, -1)
    valid_s2 = torch.ones(batch_size, s2_times, dtype=torch.bool, device=device)
    valid_s1 = torch.ones(batch_size, s1_times, dtype=torch.bool, device=device)

    semantic = torch.randint(0, 19, (batch_size, height, width), device=device, generator=generator)
    instance = torch.arange(height * width, device=device).reshape(1, height, width)
    instance = (instance // 64 + 1).expand(batch_size, -1, -1)
    spot = torch.rand(batch_size, 3, height * 10, width * 10, device=device, generator=generator)
    spot_valid = torch.ones(batch_size, 1, height * 10, width * 10, dtype=torch.bool, device=device)

    batch = SentinelBatch(
        s2=s2,
        s2_days=s2_days,
        s2_valid=valid_s2,
        s1_asc=s1_asc,
        s1_asc_days=s1_days,
        s1_asc_valid=valid_s1,
        s1_des=s1_des,
        s1_des_days=s1_days,
        s1_des_valid=valid_s1,
    )
    targets = CropTargets(
        semantic_10m=semantic,
        instance_10m=instance,
        spot_rgb_highres=spot,
        spot_valid_highres=spot_valid,
    )
    return batch, targets


def benchmark(
    batch_size: int,
    precision: str,
    warmup: int,
    iterations: int,
    device: torch.device,
) -> dict[str, float | int | str]:
    gc.collect()
    torch.cuda.empty_cache()
    torch.manual_seed(42)
    model = CropSuperResolutionNet().to(device).train()
    loss_fn = MultiTaskCropLoss().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    batch, targets = make_batch(batch_size, device)
    use_amp = precision == "amp_fp16"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    def step() -> None:
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
            output = model(batch)
            loss = loss_fn(output, targets, batch)["total"]
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

    for _ in range(warmup):
        step()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    timings = []
    for _ in range(iterations):
        start = time.perf_counter()
        step()
        torch.cuda.synchronize()
        timings.append(time.perf_counter() - start)

    median = statistics.median(timings)
    return {
        "batch_size": batch_size,
        "precision": precision,
        "warmup_steps": warmup,
        "measured_steps": iterations,
        "median_step_ms": median * 1000,
        "mean_step_ms": statistics.mean(timings) * 1000,
        "p95_step_ms": percentile(timings, 0.95) * 1000,
        "throughput_samples_s": batch_size / median,
        "peak_allocated_gib": torch.cuda.max_memory_allocated() / 1024**3,
        "peak_reserved_gib": torch.cuda.max_memory_reserved() / 1024**3,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=(1, 2, 4))
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this benchmark.")
    source_root = Path(cropnet.__file__).resolve().parents[2]
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source_root, text=True
    ).strip()
    source_status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=source_root, text=True
    ).strip()
    script_path = Path(__file__).resolve()
    device = torch.device("cuda:0")
    results = []
    for precision in ("fp32", "amp_fp16"):
        for batch_size in args.batch_sizes:
            results.append(
                benchmark(batch_size, precision, args.warmup, args.iterations, device)
            )

    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": "synthetic tensors resident on GPU; full model, weighted loss, backward pass, gradient clipping and AdamW update; excludes data loading and validation",
        "seed": 42,
        "benchmark": {
            "script_sha256": sha256(script_path),
            "invocation": {
                "warmup": args.warmup,
                "iterations": args.iterations,
                "batch_sizes": args.batch_sizes,
                "precisions": ["fp32", "amp_fp16"],
            },
            "device_index": 0,
            "hostname": platform.node(),
        },
        "source": {
            "commit": source_commit,
            "worktree_clean": not source_status,
        },
        "model": "CropSuperResolutionNet",
        "model_parameters": sum(p.numel() for p in CropSuperResolutionNet().parameters()),
        "input": {
            "s2": "[B,16,10,32,32]",
            "s1_ascending": "[B,4,2,32,32]",
            "s1_descending": "[B,4,2,32,32]",
            "spot_target": "[B,3,320,320]",
        },
        "runtime": {
            "python": platform.python_version(),
            "pytorch": torch.__version__,
            "cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
            "gpu": torch.cuda.get_device_name(0),
            "driver": nvidia_query("driver_version"),
            "power_limit_w": nvidia_query("power.limit"),
            "persistence_mode": nvidia_query("persistence_mode"),
        },
        "results": results,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
