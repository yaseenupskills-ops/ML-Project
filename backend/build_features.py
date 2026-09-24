"""Batch-extract features from all URFD videos into one training CSV.
Run from backend/: python build_features.py
"""
import logging
from pathlib import Path

import pandas as pd

from features import compute_features_from_keypoints
from pose_extraction import PoseExtractor

logging.basicConfig(level=logging.INFO)

RAW_DIR = Path("data/raw/URFD")
OUT_CSV = Path("data/processed/features.csv")


MAX_FRAMES = 1000  # generous cap (>30s @30fps); guards against a pathological video hanging the batch


def extract_keypoints_from_video(extractor: PoseExtractor, video_path: str):
    extractor.keypoint_buffer = []  # reset smoothing state between clips
    keypoints = []
    for n, (_timestamp, kp) in enumerate(extractor.process_video(video_path)):
        if kp is not None:
            keypoints.append(kp)
        if n >= MAX_FRAMES:
            print(f"  WARNING: hit {MAX_FRAMES}-frame cap, truncating", flush=True)
            break
    return keypoints


def main():
    # falls first: with limited time, get both classes represented ASAP
    videos = sorted(RAW_DIR.glob("*-cam0.mp4"), key=lambda p: (not p.stem.startswith("fall"), p.stem))
    print(f"Found {len(videos)} videos", flush=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    done_clips = set()
    if OUT_CSV.exists():
        done_clips = set(pd.read_csv(OUT_CSV)["clip_id"].unique())
        print(f"Resuming: {len(done_clips)} clips already in {OUT_CSV}", flush=True)

    extractor = PoseExtractor()  # one MediaPipe model, reused across all videos
    total_windows = 0
    for i, video_path in enumerate(videos, 1):
        name = video_path.stem  # e.g. fall-01-cam0
        if name in done_clips:
            continue
        label = 1 if name.startswith("fall") else 0
        print(f"[{i}/{len(videos)}] {name}...", flush=True)
        keypoints = extract_keypoints_from_video(extractor, str(video_path))
        if len(keypoints) < 2:
            print(f"  skip (no keypoints): {name}", flush=True)
            continue
        df = compute_features_from_keypoints(keypoints, subject_id="S1", clip_id=name)
        if len(df) == 0:
            print(f"  skip (no windows): {name}", flush=True)
            continue
        df["label"] = label
        df.to_csv(OUT_CSV, mode="a", header=not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0, index=False)
        total_windows += len(df)
        print(f"  ok: {name} -> {len(df)} windows (label={label})", flush=True)

    full = pd.read_csv(OUT_CSV)
    print(f"Total in {OUT_CSV}: {len(full)} feature windows from {full['clip_id'].nunique()} clips", flush=True)
    print(f"Label distribution:\n{full['label'].value_counts()}", flush=True)


if __name__ == "__main__":
    main()
