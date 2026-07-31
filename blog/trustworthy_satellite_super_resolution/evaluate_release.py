#!/usr/bin/env python3
"""Evaluate S2SR observation consistency without claiming HR ground truth."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
import importlib.metadata
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from omegaconf import OmegaConf
from PIL import Image

import s2sr
from s2sr.model import SRLatentDiffusion


BANDS = ("B04", "B03", "B02", "B08")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: torch.Tensor, q: float) -> float:
    return float(torch.quantile(values.float(), q).item())


def spectral_angle(reference: torch.Tensor, candidate: torch.Tensor) -> torch.Tensor:
    ref = reference.permute(0, 2, 3, 1).reshape(-1, 4)
    pred = candidate.permute(0, 2, 3, 1).reshape(-1, 4)
    denominator = ref.norm(dim=1) * pred.norm(dim=1)
    valid = denominator > 1e-12
    cosine = (ref[valid] * pred[valid]).sum(dim=1) / denominator[valid]
    return torch.rad2deg(torch.acos(cosine.clamp(-1, 1)))


def ndvi(values: torch.Tensor) -> torch.Tensor:
    red, nir = values[:, 0], values[:, 3]
    denominator = nir + red
    return torch.where(denominator.abs() > 1e-8, (nir - red) / denominator, torch.nan)


def gradient_energy(values: torch.Tensor) -> float:
    dx = values[..., :, 1:] - values[..., :, :-1]
    dy = values[..., 1:, :] - values[..., :-1, :]
    return float((dx.square().mean() + dy.square().mean()).item())


def save_rgb(values: torch.Tensor, path: Path) -> None:
    rgb = values[0, :3].detach().cpu().permute(1, 2, 0).numpy()
    low, high = np.percentile(rgb, (2, 98))
    rgb = np.clip((rgb - low) / max(high - low, 1e-6), 0, 1)
    Image.fromarray((rgb * 255).astype(np.uint8)).save(path)


def save_spread(values: torch.Tensor, path: Path) -> None:
    spread = values[0].detach().cpu().numpy()
    high = np.percentile(spread, 99)
    scaled = np.clip(spread / max(high, 1e-8), 0, 1)
    red = np.clip(1.8 * scaled, 0, 1)
    green = np.clip(1.8 * (1 - np.abs(scaled - 0.5) * 2), 0, 1)
    blue = np.clip(1.8 * (1 - scaled), 0, 1)
    image = np.stack((red, green, blue), axis=-1)
    Image.fromarray((image * 255).astype(np.uint8)).save(path)


def evaluate_case(
    name: str,
    source: Path,
    model: SRLatentDiffusion,
    output_dir: Path,
    sampling_steps: int,
    uncertainty_steps: int,
    uncertainty_samples: int,
) -> dict:
    raw = torch.load(source, map_location="cpu", weights_only=True).float()
    lr = (raw / 10000.0).to(model.device)
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    sr = model(
        lr,
        sampling_steps=sampling_steps,
        sampling_eta=0.95,
        histogram_matching=True,
    )
    bilinear = F.interpolate(lr, scale_factor=4, mode="bilinear", align_corners=False)
    down_sr = F.avg_pool2d(sr, kernel_size=4, stride=4)
    error = down_sr - lr
    detail = sr - bilinear
    sam = spectral_angle(lr, down_sr)
    ndvi_error = ndvi(down_sr) - ndvi(lr)
    ndvi_error = ndvi_error[torch.isfinite(ndvi_error)]

    variations = []
    for seed in range(100, 100 + uncertainty_samples):
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)
        variations.append(
            model(
                lr,
                sampling_steps=uncertainty_steps,
                sampling_eta=0.0,
                histogram_matching=True,
            ).detach()
        )
    stack = torch.stack(variations)
    spread = 2 * stack.std(dim=0).mean(dim=1)
    residual_magnitude = detail.abs().mean(dim=1)
    spread_flat = spread.flatten()
    residual_flat = residual_magnitude.flatten()
    spread_residual_correlation = float(
        torch.corrcoef(torch.stack((spread_flat, residual_flat)))[0, 1].item()
    )

    save_rgb(lr, output_dir / f"{name}_lr.png")
    save_rgb(bilinear, output_dir / f"{name}_bilinear.png")
    save_rgb(sr, output_dir / f"{name}_learned.png")
    save_spread(spread, output_dir / f"{name}_spread.png")

    return {
        "name": name,
        "source_sha256": sha256(source),
        "lr_shape": list(lr.shape),
        "sr_shape": list(sr.shape),
        "downsample_consistency": {
            "bias_by_band": [float(value) for value in error.mean(dim=(0, 2, 3)).tolist()],
            "mae_by_band": [float(value) for value in error.abs().mean(dim=(0, 2, 3)).tolist()],
            "rmse_by_band": [float(value) for value in error.square().mean(dim=(0, 2, 3)).sqrt().tolist()],
        },
        "spectral_angle_degrees": {
            "mean": float(sam.mean().item()),
            "p95": percentile(sam, 0.95),
        },
        "ndvi_downsample_error": {
            "bias": float(ndvi_error.mean().item()),
            "mae": float(ndvi_error.abs().mean().item()),
            "p95_absolute": percentile(ndvi_error.abs(), 0.95),
        },
        "learned_vs_bilinear": {
            "mae_by_band": [float(value) for value in detail.abs().mean(dim=(0, 2, 3)).tolist()],
            "gradient_energy_bilinear": gradient_energy(bilinear),
            "gradient_energy_learned": gradient_energy(sr),
            "gradient_energy_ratio": gradient_energy(sr) / max(gradient_energy(bilinear), 1e-12),
        },
        "stochastic_spread": {
            "samples": uncertainty_samples,
            "sampling_steps": uncertainty_steps,
            "mean_2sigma": float(spread.mean().item()),
            "p95_2sigma": percentile(spread, 0.95),
            "correlation_with_absolute_residual": spread_residual_correlation,
            "calibrated": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sampling-steps", type=int, default=100)
    parser.add_argument("--uncertainty-steps", type=int, default=25)
    parser.add_argument("--uncertainty-samples", type=int, default=5)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config_path = args.repo / "s2sr/configs/config_10m.yaml"
    checkpoint_path = args.repo / "s2sr/models/s2sr-ldsrs2_v1_0_0.ckpt"
    config = OmegaConf.load(config_path)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = SRLatentDiffusion(config, device=device)
    model.load_pretrained(str(checkpoint_path))

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=args.repo, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=args.repo, text=True
    ).strip()
    imported_package_path = Path(s2sr.__file__).resolve()
    if args.repo.resolve() not in imported_package_path.parents:
        raise RuntimeError(
            f"Imported s2sr package {imported_package_path} is not under {args.repo.resolve()}."
        )
    cases = [
        evaluate_case(
            name,
            args.repo / f"s2sr/models/example_{name}.pt",
            model,
            args.output_dir,
            args.sampling_steps,
            args.uncertainty_steps,
            args.uncertainty_samples,
        )
        for name in ("rural", "urban")
    ]
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": "Two bundled Sentinel-2 examples without independent HR truth; observation consistency, bilinear deviation and stochastic spread only",
        "source": {
            "commit": commit,
            "worktree_clean": not status,
            "imported_package_path": str(imported_package_path),
            "config_sha256": sha256(config_path),
            "checkpoint_sha256": sha256(checkpoint_path),
        },
        "runtime": {
            "python": platform.python_version(),
            "pytorch": torch.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "numpy": np.__version__,
            "scikit_image": importlib.metadata.version("scikit-image"),
            "omegaconf": importlib.metadata.version("omegaconf"),
            "pillow": importlib.metadata.version("pillow"),
        },
        "protocol": {
            "bands": list(BANDS),
            "scale": 4,
            "sampling_steps": args.sampling_steps,
            "sampling_eta": 0.95,
            "histogram_matching": True,
            "uncertainty_samples": args.uncertainty_samples,
            "uncertainty_steps": args.uncertainty_steps,
            "uncertainty_eta": 0.0,
        },
        "claims_not_supported": [
            "PSNR, SSIM or ERGAS without independent HR truth",
            "native 2.5 m resolving power",
            "calibrated uncertainty coverage",
            "population-level performance from two bundled examples",
        ],
        "cases": cases,
    }
    (args.output_dir / "evaluation.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
