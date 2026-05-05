#!/usr/bin/env python3
"""
CommentGuard — Threshold Sweep Analysis
────────────────────────────────────────
Hits the API once for 500 Jigsaw comments, saves raw scores,
then sweeps through thresholds 0.30 → 0.90 to find the
optimal F1-maximizing threshold.

Usage:
    python threshold_sweep.py
"""

import json
import time
import sys
from pathlib import Path

try:
    import requests
    import pandas as pd
except ImportError:
    print("❌ Install deps: pip install requests pandas")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
TEST_CSV = SCRIPT_DIR / "test.csv"
LABELS_CSV = SCRIPT_DIR / "test_labels.csv"
CATEGORIES = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
API_URL = "http://localhost:8000"
N_SAMPLES = 500
SEED = 42

THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]


def load_dataset():
    texts = pd.read_csv(TEST_CSV)
    labels = pd.read_csv(LABELS_CSV)
    df = texts.merge(labels, on="id")
    df = df[df["toxic"] != -1].copy()
    df["ground_truth"] = df[CATEGORIES].max(axis=1).apply(lambda x: "toxic" if x == 1 else "non_toxic")
    return df.sample(n=N_SAMPLES, random_state=SEED).reset_index(drop=True)


def main():
    print()
    print("=" * 65)
    print("  📊 CommentGuard — Threshold Sweep Analysis")
    print("=" * 65)
    print()

    # ── Health check ──────────────────────────────────────────────────────────
    try:
        requests.get(f"{API_URL}/health", timeout=5)
        print("  ✅ API is live\n")
    except:
        print("  ❌ Server not running. Start it: ./start.sh")
        sys.exit(1)

    # ── Load dataset ──────────────────────────────────────────────────────────
    df = load_dataset()
    total_toxic = (df["ground_truth"] == "toxic").sum()
    total_clean = (df["ground_truth"] == "non_toxic").sum()
    print(f"  Dataset: {N_SAMPLES} comments ({total_toxic} toxic, {total_clean} clean)")
    print()

    # ── Phase 1: Hit the API once, save raw scores ────────────────────────────
    print("  Phase 1: Collecting raw scores from API...")
    print("  (This only happens once — threshold sweep is instant after)\n")

    raw_scores_path = SCRIPT_DIR / "raw_scores.json"

    if raw_scores_path.exists():
        print("  📂 Found cached scores, skipping API calls...")
        with open(raw_scores_path) as f:
            raw_data = json.load(f)
        print(f"  Loaded {len(raw_data)} cached results\n")
    else:
        raw_data = []
        for idx, row in df.iterrows():
            text = str(row["comment_text"])[:1000]
            ground_truth = row["ground_truth"]

            try:
                resp = requests.post(
                    f"{API_URL}/moderate",
                    json={"text": text},
                    timeout=60,
                )
                result = resp.json()
                raw_data.append({
                    "ground_truth": ground_truth,
                    "toxic_prob": result["toxic_prob"],
                    "scores": result["scores"],
                })
            except:
                continue

            if (idx + 1) % 50 == 0 or idx + 1 == len(df):
                pct = (idx + 1) / len(df) * 100
                filled = int(30 * (idx + 1) / len(df))
                bar = "█" * filled + "░" * (30 - filled)
                sys.stdout.write(f"\r  [{bar}] {idx+1}/{len(df)} ({pct:.0f}%)")
                sys.stdout.flush()

        print("\n")

        # Cache the raw scores
        with open(raw_scores_path, "w") as f:
            json.dump(raw_data, f)
        print(f"  💾 Raw scores cached to {raw_scores_path.name}\n")

    # ── Phase 2: Sweep thresholds instantly ───────────────────────────────────
    print("  Phase 2: Sweeping thresholds...\n")

    best_f1 = 0
    best_threshold = 0.5
    sweep_results = []

    print("  ┌───────────┬──────────┬───────────┬────────┬──────────┬──────┬──────┬──────┬──────┐")
    print("  │ Threshold │ Accuracy │ Precision │ Recall │ F1 Score │  TP  │  FP  │  TN  │  FN  │")
    print("  ├───────────┼──────────┼───────────┼────────┼──────────┼──────┼──────┼──────┼──────┤")

    for threshold in THRESHOLDS:
        tp = fp = tn = fn = 0

        for item in raw_data:
            actual_toxic = item["ground_truth"] == "toxic"
            predicted_toxic = item["toxic_prob"] >= threshold

            if actual_toxic and predicted_toxic:
                tp += 1
            elif not actual_toxic and predicted_toxic:
                fp += 1
            elif not actual_toxic and not predicted_toxic:
                tn += 1
            else:
                fn += 1

        total = tp + fp + tn + fn
        accuracy  = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1        = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        marker = " ◀── BEST" if f1 > best_f1 else ""
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

        sweep_results.append({
            "threshold": threshold,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        })

        print(f"  │   {threshold:.2f}    │  {accuracy*100:5.1f}%  │   {precision*100:5.1f}%  │ {recall*100:4.1f}% │  {f1*100:5.1f}%  │ {tp:4d} │ {fp:4d} │ {tn:4d} │ {fn:4d} │{marker}")

    print("  └───────────┴──────────┴───────────┴────────┴──────────┴──────┴──────┴──────┴──────┘")
    print()

    # ── Find the best ─────────────────────────────────────────────────────────
    best = [r for r in sweep_results if r["threshold"] == best_threshold][0]

    print(f"  🏆 OPTIMAL THRESHOLD: {best_threshold}")
    print(f"  ════════════════════════════════════")
    print(f"  Accuracy:    {best['accuracy']*100:.1f}%")
    print(f"  Precision:   {best['precision']*100:.1f}%")
    print(f"  Recall:      {best['recall']*100:.1f}%")
    print(f"  F1 Score:    {best['f1_score']*100:.1f}%")
    print(f"  False Positives: {best['fp']} (down from {sweep_results[0]['fp']} at threshold 0.30)")
    print()

    # ── Save results ──────────────────────────────────────────────────────────
    report_path = SCRIPT_DIR / "threshold_analysis.md"
    with open(report_path, "w") as f:
        f.write("# 📊 Threshold Sweep Analysis\n\n")
        f.write(f"> Dataset: Jigsaw Toxic Comment Classification — {len(raw_data)} comments (seed={SEED})\n\n")
        f.write("| Threshold | Accuracy | Precision | Recall | F1 Score | TP | FP | TN | FN |\n")
        f.write("|-----------|----------|-----------|--------|----------|----|----|----|----|---|\n")
        for r in sweep_results:
            star = " ⭐" if r["threshold"] == best_threshold else ""
            f.write(f"| **{r['threshold']:.2f}**{star} | {r['accuracy']*100:.1f}% | "
                    f"{r['precision']*100:.1f}% | {r['recall']*100:.1f}% | "
                    f"{r['f1_score']*100:.1f}% | {r['tp']} | {r['fp']} | {r['tn']} | {r['fn']} |\n")
        f.write(f"\n**Optimal Threshold: {best_threshold}** (maximizes F1 Score)\n")

    print(f"  📝 Report saved: {report_path}")
    print(f"\n  💡 To apply this threshold, set THRESHOLD={best_threshold} in your .env file")
    print()


if __name__ == "__main__":
    main()
