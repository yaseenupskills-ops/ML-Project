#!/usr/bin/env python3
"""Held-out evaluation of the Random Forest fall detector.

Splits the UR Fall dataset by WHOLE VIDEO (80% train / 20% test, stratified
by label, fixed seed) so no feature window from a test video can leak into
training, fits the baseline RF on the 80% only, and reports accuracy,
precision, recall, F1 and the confusion matrix on the held-out 20%.

Features are rebuilt from the cached keypoint files
(`data/processed/keypoints/URFD/*.npy`) using the current feature config.
Results are printed and saved to `evaluation_results.txt`.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features import FeatureEngineer  # noqa: E402
from model_rf import FallDetectionRF  # noqa: E402

KEYPOINTS_DIR = ROOT / "data" / "processed" / "keypoints" / "URFD"
OUTPUT_PATH = ROOT / "evaluation_results.txt"
TEST_FRACTION = 0.2
SEED = 42


def clip_label(clip_id: str) -> int:
    """Video-level ground truth: fall clips are positive, ADL clips negative."""
    if clip_id.startswith("fall"):
        return 1
    if clip_id.startswith("adl"):
        return 0
    raise ValueError(f"Unrecognized clip name (expected fall-*/adl-*): {clip_id}")


def build_features() -> tuple[pd.DataFrame, dict]:
    """Compute per-window features for every cached keypoint clip."""
    engineer = FeatureEngineer()
    window_frames = max(2, int(round(engineer.window_sec * engineer.sample_fps)))
    step_frames = max(1, int(round(window_frames * (1 - engineer.overlap))))
    meta = {
        "window_sec": engineer.window_sec,
        "overlap": engineer.overlap,
        "fps": engineer.fps,
        "window_frames": window_frames,
        "step_frames": step_frames,
    }

    frames: list[pd.DataFrame] = []
    skipped: list[str] = []
    for path in sorted(KEYPOINTS_DIR.glob("*.npy")):
        clip_id = path.stem
        keypoints = np.load(path)
        feats = engineer.compute_features(
            list(keypoints), subject_id="unknown", clip_id=clip_id
        )
        if feats.empty:
            skipped.append(clip_id)
            continue
        feats["label"] = clip_label(clip_id)
        frames.append(feats)

    if not frames:
        raise RuntimeError(f"No features produced from {KEYPOINTS_DIR}")
    df = pd.concat(frames, ignore_index=True)
    meta["skipped"] = skipped
    return df, meta


def split_by_video(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list, list]:
    """Stratified 80/20 split grouped by whole video (clip_id)."""
    clips = df[["clip_id", "label"]].drop_duplicates().sort_values("clip_id")
    if clips["clip_id"].duplicated().any():
        raise ValueError("Each clip_id must map to exactly one label")

    train_clips, test_clips = train_test_split(
        clips, test_size=TEST_FRACTION, stratify=clips["label"], random_state=SEED
    )
    train_ids = sorted(train_clips["clip_id"])
    test_ids = sorted(test_clips["clip_id"])

    overlap = set(train_ids) & set(test_ids)
    if overlap:
        raise RuntimeError(f"Video leakage between splits: {sorted(overlap)}")

    train_df = df[df["clip_id"].isin(train_ids)].copy()
    test_df = df[df["clip_id"].isin(test_ids)].copy()
    for name, part in (("train", train_df), ("test", test_df)):
        present = set(part["label"].unique())
        if present != {0, 1}:
            raise RuntimeError(f"{name} split must contain both classes, got {present}")
    return train_df, test_df, train_ids, test_ids


def evaluate(model: FallDetectionRF, test_df: pd.DataFrame) -> dict:
    """Compute window-level metrics and a per-video rollup on the test split."""
    X_test, y_test, _ = model.prepare_features(test_df)
    y_pred, y_proba = model.predict(X_test)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    result = {
        "n_windows": int(len(y_test)),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }

    # Video-level rollup: mean window probability >= 0.5 decides the clip.
    rollup = (
        test_df.assign(pred=y_pred, proba=y_proba)
        .groupby("clip_id")
        .agg(
            label=("label", "first"),
            n_windows=("label", "size"),
            mean_proba=("proba", "mean"),
            positive_votes=("pred", "sum"),
        )
        .reset_index()
        .sort_values(["label", "clip_id"])
    )
    rollup["predicted"] = (rollup["mean_proba"] >= 0.5).astype(int)
    result["rollup"] = rollup
    result["video_accuracy"] = float(
        (rollup["predicted"] == rollup["label"]).mean()
    )
    return result


def format_report(
    df: pd.DataFrame,
    meta: dict,
    train_ids: list,
    test_ids: list,
    result: dict,
    model: FallDetectionRF,
) -> str:
    """Render the full plain-text report."""
    train_df = df[df["clip_id"].isin(train_ids)]
    test_df = df[df["clip_id"].isin(test_ids)]
    rollup: pd.DataFrame = result["rollup"]

    lines = [
        "FallGuard Care - Random Forest Evaluation (held-out video split)",
        "=" * 64,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "Dataset: UR Fall Detection Dataset (UR Fall), cam0, deduplicated",
        "Label: video-level (fall-* = fall, adl-* = no fall)",
        "",
        "Feature config",
        "-" * 64,
        f"  window: {meta['window_sec']}s x {meta['fps']} fps = "
        f"{meta['window_frames']} frames, overlap {meta['overlap']:.0%} "
        f"(step {meta['step_frames']} frames)",
        f"  features per window: {len(model.feature_names or [])}",
        f"  source: cached keypoints ({KEYPOINTS_DIR.relative_to(ROOT)}/*.npy)",
        f"  clips skipped (too short): {', '.join(meta['skipped']) or 'none'}",
        "",
        "Split (by whole video, stratified, random_state=42)",
        "-" * 64,
        f"  train: {len(train_ids)} videos -> {len(train_df)} windows "
        f"({int(train_df['label'].sum())} fall / "
        f"{int((train_df['label'] == 0).sum())} no-fall)",
        f"  test:  {len(test_ids)} videos -> {len(test_df)} windows "
        f"({int(test_df['label'].sum())} fall / "
        f"{int((test_df['label'] == 0).sum())} no-fall)",
        f"  test videos: {', '.join(test_ids)}",
        "  leakage check: no video appears in both splits",
        "",
        f"Window-level results on {result['n_windows']} held-out windows",
        "-" * 64,
        f"  Accuracy:  {result['accuracy']:.4f}",
        f"  Precision: {result['precision']:.4f}",
        f"  Recall:    {result['recall']:.4f}",
        f"  F1 score:  {result['f1']:.4f}",
        "",
        "Confusion matrix (counts)",
        "-" * 64,
        f"  True positives  (TP): {result['tp']:>4}   "
        f"False positives (FP): {result['fp']:>4}",
        f"  True negatives  (TN): {result['tn']:>4}   "
        f"False negatives (FN): {result['fn']:>4}",
        "",
        f"Video-level results ({len(rollup)} test videos, "
        "mean window probability >= 0.5)",
        "-" * 64,
        f"  Accuracy: {result['video_accuracy']:.4f} "
        f"({int((rollup['predicted'] == rollup['label']).sum())}/"
        f"{len(rollup)} videos correct)",
        "",
        f"  {'video':<12} {'true':<6} {'pred':<6} {'windows':>8} "
        f"{'fall prob':>10}",
    ]
    for row in rollup.itertuples(index=False):
        true_name = "fall" if row.label else "no-fall"
        pred_name = "fall" if row.predicted else "no-fall"
        lines.append(
            f"  {row.clip_id:<12} {true_name:<6} {pred_name:<6} "
            f"{row.n_windows:>8} {row.mean_proba:>10.3f}"
        )

    importance = model.get_feature_importance()
    if importance is not None and model.feature_names:
        pairs = sorted(
            zip(model.feature_names, importance), key=lambda p: p[1], reverse=True
        )[:5]
        lines += [
            "",
            "Top feature importances",
            "-" * 64,
        ]
        lines += [f"  {name:<32} {value:.4f}" for name, value in pairs]

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    print("Building features from cached keypoints ...")
    df, meta = build_features()
    n_clips = df["clip_id"].nunique()
    n_fall_clips = df.loc[df["label"] == 1, "clip_id"].nunique()
    print(
        f"  {len(df)} windows from {n_clips} videos "
        f"({n_fall_clips} fall / {n_clips - n_fall_clips} no-fall)"
    )

    train_df, test_df, train_ids, test_ids = split_by_video(df)
    print(
        f"Split by video: {len(train_ids)} train / {len(test_ids)} test "
        f"(no overlap)"
    )

    print("Training Random Forest on the 80% train split ...")
    model = FallDetectionRF()
    X_train, y_train, _ = model.prepare_features(train_df)
    X_train_scaled = model.scaler.fit_transform(X_train)
    model.model.fit(X_train_scaled, y_train)
    model.is_fitted = True
    print(
        f"  fitted on {X_train.shape[0]} windows, "
        f"{X_train.shape[1]} features "
        f"(class_weight={model.model.class_weight})"
    )

    print(f"Evaluating on the held-out 20% ({len(test_df)} windows) ...")
    result = evaluate(model, test_df)

    report = format_report(df, meta, train_ids, test_ids, result, model)
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    print()
    print(f"  Accuracy:  {result['accuracy']:.4f}")
    print(f"  Precision: {result['precision']:.4f}")
    print(f"  Recall:    {result['recall']:.4f}")
    print(f"  F1 score:  {result['f1']:.4f}")
    print(
        f"  Confusion matrix: TP={result['tp']} TN={result['tn']} "
        f"FP={result['fp']} FN={result['fn']}"
    )
    print()
    print(f"Full report saved to {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
