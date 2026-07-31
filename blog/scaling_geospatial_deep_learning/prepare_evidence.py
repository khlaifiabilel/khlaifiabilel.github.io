#!/usr/bin/env python3
"""Extract the public evidence subset used by the scaling article."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    history = sorted(snapshot["history"], key=lambda row: int(row["epoch"]))
    epochs = [
        {
            "epoch": int(row["epoch"]),
            "duration_s": float(row["trainer/epoch_duration_seconds"]),
            "validation_macro_iou": float(row["val/macro_iou"]),
        }
        for row in history
    ]
    payload = {
        "schema_version": 1,
        "evidence": "measured historical run",
        "snapshot_sha256": sha256(args.snapshot),
        "benchmark_sha256": sha256(args.benchmark),
        "wandb_run_path": snapshot["run_path"],
        "training_commit": snapshot["git_commit"],
        "dataset_revision": snapshot["dataset_revision"],
        "protocol": {
            "epochs": benchmark["run"]["epochs"],
            "train_samples": snapshot["config"]["dataset"]["train_samples"],
            "validation_samples": snapshot["config"]["dataset"]["validation_samples"],
            "batch_size": snapshot["config"]["cli"]["batch_size"],
            "crop_size_10m": snapshot["config"]["cli"]["crop_size"],
            "precision": benchmark["gpu_scenario_model"]["precision"],
            "gpu": benchmark["source"]["runtime"]["gpu"]["name"],
            "pytorch": benchmark["source"]["runtime"]["torch"],
            "cuda": benchmark["source"]["runtime"]["torch_cuda"],
        },
        "summary": {
            "best_epoch": benchmark["run"]["best_epoch"],
            "best_validation_macro_iou": benchmark["run"]["best_validation_macro_iou"],
            "median_epoch_s": benchmark["run"]["epoch_seconds"]["median"],
            "timed_train_validation_h": benchmark["run"]["timed_train_validation_hours"],
            "end_to_end_h": benchmark["run"]["wandb_end_to_end_runtime_hours"],
            "epoch_50_peak_allocated_gib": snapshot["summary"]["system/gpu_peak_allocated_gib"],
            "epoch_50_peak_reserved_gib": snapshot["summary"]["system/gpu_peak_reserved_gib"],
        },
        "epochs": epochs,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
