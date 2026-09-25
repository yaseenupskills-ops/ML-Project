#!/usr/bin/env python3
"""Build reproducible pose-feature datasets from a video directory.

The script deliberately refuses to use a dataset name as a subject ID. Every
clip must be associated with an actor/subject identifier so downstream
subject-independent evaluation cannot silently group all rows together.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features import FeatureEngineer  # noqa: E402
from pose_extraction import PoseExtractor  # noqa: E402

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
SUBJECT_PATTERN = re.compile(r"(?:subject|actor|person)[_-]?([A-Za-z0-9]+)", re.I)


def infer_subject(path: Path, input_dir: Path, metadata: dict[str, str]) -> str | None:
    """Infer an actor ID from metadata or a subject/actor path component."""
    for key in (str(path.relative_to(input_dir)), path.name, path.stem):
        if key in metadata:
            return str(metadata[key])
    for part in path.relative_to(input_dir).parts:
        match = SUBJECT_PATTERN.search(part)
        if match:
            return match.group(1)
    return None


def load_metadata(input_dir: Path) -> dict[str, str]:
    metadata_path = input_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("metadata.json must contain an object mapping clips to subjects")
    return {str(key): str(value) for key, value in raw.items()}


def label_for_clip(path: Path) -> int:
    name = path.stem.lower()
    if name.startswith("fall"):
        return 1
    if name.startswith("adl") or name.startswith("normal"):
        return 0
    raise ValueError(
        f"Cannot infer fall/non-fall label from {path.name}; use a fall*/adl* naming convention"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, help="Directory containing labeled videos")
    parser.add_argument("--output-dir", default="data/processed/features")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    metadata = load_metadata(input_dir)
    videos = sorted(
        path for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    if not videos:
        print(f"No supported video files found under {input_dir}", file=sys.stderr)
        return 1

    extractor = PoseExtractor(args.config)
    engineer = FeatureEngineer(args.config)
    rows: list[pd.DataFrame] = []
    manifest: list[dict] = []
    try:
        for video in videos:
            subject_id = infer_subject(video, input_dir, metadata)
            if not subject_id:
                print(
                    f"ERROR: no subject ID for {video}. Add metadata.json or a "
                    "subject/actor path component; refusing to create a leakage-prone dataset.",
                    file=sys.stderr,
                )
                return 2
            label = label_for_clip(video)
            sequence = [
                keypoints
                for _, keypoints in extractor.process_video(str(video))
                if keypoints is not None
            ]
            if len(sequence) < 2:
                print(f"WARNING: no usable pose frames in {video}", file=sys.stderr)
                continue
            features = engineer.compute_features(
                sequence, subject_id=subject_id, clip_id=video.stem
            )
            if features.empty:
                print(f"WARNING: no feature windows for {video}", file=sys.stderr)
                continue
            features["label"] = label
            rows.append(features)
            manifest.append({
                "video": str(video),
                "clip_id": video.stem,
                "subject_id": subject_id,
                "label": label,
                "frames": len(sequence),
                "feature_rows": len(features),
            })
    finally:
        extractor.close()

    if not rows:
        print("No usable feature rows were produced.", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(rows, ignore_index=True)
    combined_path = output_dir / "dataset.csv"
    combined.to_csv(combined_path, index=False)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "config": str(Path(args.config).resolve()),
        "feature_rows": len(combined),
        "clips": manifest,
        "subjects": sorted({item["subject_id"] for item in manifest}),
    }, indent=2), encoding="utf-8")
    print(f"Wrote {len(combined)} rows to {combined_path}")
    print(f"Wrote provenance manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
