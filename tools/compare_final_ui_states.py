#!/usr/bin/env python3
"""Compare the six rendered Huawei UI states with the locked approved references."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

STATES = (
    ("01-firmware-flash.png", "01-firmware-flash.png"),
    ("02-settings.png", "02-settings.png"),
    ("03-about.png", "03-about.png"),
    ("04-fix-drivers.png", "04-fix-drivers.png"),
    ("05-register-device.png", "05-register-device.png"),
    ("06-terminal.png", "07-terminal.png"),
)
CURRENT_SIZE = (1586, 992)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mean_channel_difference(image: Image.Image) -> float:
    means = ImageStat.Stat(image).mean
    return sum(means) / len(means)


def similarity(a: Image.Image, b: Image.Image) -> tuple[float, float, float]:
    a_rgb = a.convert("RGB")
    b_rgb = b.resize(a.size, Image.Resampling.LANCZOS).convert("RGB")
    pixel_diff = ImageChops.difference(a_rgb, b_rgb)
    pixel = 1.0 - _mean_channel_difference(pixel_diff) / 255.0

    ac = a_rgb.resize((160, 100), Image.Resampling.LANCZOS)
    bc = b_rgb.resize((160, 100), Image.Resampling.LANCZOS)
    coarse_diff = ImageChops.difference(ac, bc)
    coarse = 1.0 - _mean_channel_difference(coarse_diff) / 255.0

    ae = a_rgb.convert("L").resize((320, 200), Image.Resampling.LANCZOS).filter(ImageFilter.FIND_EDGES)
    be = b_rgb.convert("L").resize((320, 200), Image.Resampling.LANCZOS).filter(ImageFilter.FIND_EDGES)
    edge_diff = ImageChops.difference(ae, be)
    edge = 1.0 - _mean_channel_difference(edge_diff) / 255.0
    return pixel, coarse, edge


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved", type=Path, default=Path("resources/expected ui"))
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    authority = args.approved / "README.md"
    text = authority.read_text(encoding="utf-8")
    locked_section = text.split("## Required seventh Phase 15 state", 1)[0]
    hashes = [h.lower() for h in re.findall(r"`([a-fA-F0-9]{64})`", locked_section)]
    if len(hashes) != len(STATES) or len(set(hashes)) != len(STATES):
        raise SystemExit(f"locked visual authority must contain exactly {len(STATES)} unique SHA-256 values")

    args.output.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "schema": "techguytool-huawei.visual-qa.v1",
        "approved_authority": str(authority),
        "current_render_size": list(CURRENT_SIZE),
        "states": [],
    }

    for (approved_name, current_name), expected_hash in zip(STATES, hashes):
        ref_path = args.approved / approved_name
        cur_path = args.current / current_name
        if not ref_path.is_file():
            raise SystemExit(f"approved reference missing: {ref_path}")
        if not cur_path.is_file():
            raise SystemExit(f"current render missing: {cur_path}")
        actual_hash = sha256(ref_path)
        if actual_hash != expected_hash:
            raise SystemExit(f"approved reference hash mismatch for {approved_name}: {actual_hash} != {expected_hash}")

        ref = Image.open(ref_path).convert("RGB")
        cur = Image.open(cur_path).convert("RGB")
        if cur.size != CURRENT_SIZE:
            raise SystemExit(f"current render size mismatch for {current_name}: {cur.size} != {CURRENT_SIZE}")

        pixel, coarse, edge = similarity(ref, cur)
        if coarse < 0.70 or edge < 0.70:
            raise SystemExit(f"gross visual drift for {current_name}: coarse={coarse:.4f}, edge={edge:.4f}")

        normalized = cur.resize(ref.size, Image.Resampling.LANCZOS)
        side = Image.new("RGB", (ref.width * 2, ref.height + 38), "#050810")
        side.paste(ref, (0, 38))
        side.paste(normalized, (ref.width, 38))
        draw = ImageDraw.Draw(side)
        draw.text((12, 11), f"APPROVED - {approved_name}", fill="white")
        draw.text((ref.width + 12, 11), f"CURRENT - {current_name}", fill="white")
        side.save(args.output / f"compare-{current_name}", optimize=True)

        diff = ImageChops.difference(ref, normalized)
        amplified = diff.point(lambda value: min(255, value * 3))
        amplified.save(args.output / f"diff-x3-{current_name}", optimize=True)

        report["states"].append({
            "approved_name": approved_name,
            "current_name": current_name,
            "approved_sha256": expected_hash,
            "approved_size": list(ref.size),
            "current_size": list(cur.size),
            "pixel_similarity": round(pixel, 6),
            "coarse_similarity": round(coarse, 6),
            "edge_similarity": round(edge, 6),
        })

    report["verdict"] = "VISUAL_EVIDENCE_READY"
    (args.output / "visual-qa-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
