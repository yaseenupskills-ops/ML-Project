"""Batch-extract features from data/raw/URFD/*.mp4 into one labeled CSV for model_rf.py."""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from features import compute_features_from_video  # noqa: E402
import pandas as pd  # noqa: E402

logging.basicConfig(level=logging.INFO)


def main():
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw" / "URFD"
    videos = sorted(raw_dir.glob("*.mp4"))
    frames = []
    for video in videos:
        label = 1 if video.stem.startswith("fall") else 0
        # ponytail: URFD has only 1 real actor, so GroupKFold in model_rf.py needs
        # per-clip grouping (matches PROJECT_SUMMARY.md's "clip-level groups") --
        # use the clip id as subject_id too, or CV degenerates to 1 group.
        df = compute_features_from_video(str(video), subject_id=video.stem, clip_id=video.stem)
        if df.empty:
            print(f"WARNING: no features for {video.name}")
            continue
        df["label"] = label
        frames.append(df)

    if not frames:
        print("No features extracted from any video.")
        sys.exit(1)

    out = pd.concat(frames, ignore_index=True)
    out_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "features.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Saved {len(out)} feature windows from {len(frames)}/{len(videos)} clips to {out_path}")


if __name__ == "__main__":
    main()
