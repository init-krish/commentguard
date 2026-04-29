"""
CommentGuard — Multi-Label Model Training Script v3.0
─────────────────────────────────────────────────────
Dataset: Jigsaw Toxic Comment Classification (Kaggle)
Output:  backend/app/ml/vectorizer.joblib + models.joblib (dict of 6 classifiers)

Trains one Logistic Regression per toxicity category:
  toxic | severe_toxic | obscene | threat | insult | identity_hate

Run on Kaggle:
    1. Open any Kaggle notebook on the Jigsaw competition.
    2. Paste this script and run.
    3. Download artifacts from /kaggle/working/.

Run on Colab:
    1. Upload train.csv from the Jigsaw dataset.
    2. Set DATA_PATH = "/content/train.csv".
    3. Run.
"""

import os, joblib, json, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH  = "/kaggle/input/jigsaw-toxic-comment-classification-challenge/train.csv"
OUT_DIR    = "/kaggle/working"          # change to "/content" on Colab
THRESHOLD  = 0.5

TOXIC_COLS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

os.makedirs(OUT_DIR, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data…")
df = pd.read_csv(DATA_PATH)

texts  = df["comment_text"].fillna("").tolist()

# Binary label for backward compat + stratified split
df["any_toxic"] = (df[TOXIC_COLS].sum(axis=1) > 0).astype(int)

X_train, X_test, idx_train, idx_test = train_test_split(
    texts, df.index.tolist(), test_size=0.1, random_state=42,
    stratify=df["any_toxic"].tolist()
)
print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")
print(f"Toxic rate: {df['any_toxic'].mean():.1%}")

# ── Vectoriser ────────────────────────────────────────────────────────────────
print("\nFitting TF-IDF…")
vec = TfidfVectorizer(
    max_features=50_000,
    ngram_range=(1, 2),
    min_df=3,
    sublinear_tf=True,
    strip_accents="unicode",
    analyzer="word",
    token_pattern=r"\w{2,}"
)
X_train_vec = vec.fit_transform(X_train)
X_test_vec  = vec.transform(X_test)

# ── Train one model per category ──────────────────────────────────────────────
models = {}
metrics = {}

for col in TOXIC_COLS:
    y_train = df.loc[idx_train, col].values
    y_test  = df.loc[idx_test, col].values

    pos_rate = y_train.mean()
    print(f"\n{'─'*60}")
    print(f"Training: {col}  (positive rate: {pos_rate:.1%})")

    model = LogisticRegression(
        C=5.0,
        solver="saga",
        max_iter=1000,
        n_jobs=-1,
        class_weight="balanced"   # handles class imbalance (esp. threat, identity_hate)
    )
    model.fit(X_train_vec, y_train)

    probs = model.predict_proba(X_test_vec)[:, 1]
    preds = (probs >= THRESHOLD).astype(int)

    auc = roc_auc_score(y_test, probs) if y_test.sum() > 0 else 0.0
    print(f"ROC-AUC: {auc:.4f}")
    print(classification_report(y_test, preds, target_names=[f"non_{col}", col], zero_division=0))

    models[col] = model
    metrics[col] = {
        "roc_auc": round(auc, 4),
        "positive_rate": round(float(pos_rate), 4),
        "test_positives": int(y_test.sum()),
    }

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "═" * 60)
print("SUMMARY — Per-Category ROC-AUC")
print("═" * 60)
for col in TOXIC_COLS:
    print(f"  {col:20s}  AUC = {metrics[col]['roc_auc']:.4f}")
mean_auc = np.mean([m["roc_auc"] for m in metrics.values()])
print(f"\n  {'Mean AUC':20s}  {mean_auc:.4f}")

# ── Save artifacts ────────────────────────────────────────────────────────────
vec_path    = os.path.join(OUT_DIR, "vectorizer.joblib")
models_path = os.path.join(OUT_DIR, "models.joblib")       # dict of 6 models
meta_path   = os.path.join(OUT_DIR, "model_meta.json")

joblib.dump(vec,    vec_path)
joblib.dump(models, models_path)

meta = {
    "version": "3.0.0",
    "type": "multi-label",
    "categories": TOXIC_COLS,
    "vectorizer": "tfidf_50k_bigram",
    "classifier": "logistic_regression_balanced",
    "metrics": metrics,
    "mean_auc": round(mean_auc, 4),
}
with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)

print(f"\n✅ Saved → {vec_path}")
print(f"✅ Saved → {models_path}")
print(f"✅ Saved → {meta_path}")
print(f"\nNext: copy vectorizer.joblib + models.joblib + model_meta.json into backend/app/ml/")

# ── Backward compat: also save a single binary model as model.joblib ─────────
# This is the "toxic" model used as fallback for binary mode
binary_path = os.path.join(OUT_DIR, "model.joblib")
joblib.dump(models["toxic"], binary_path)
print(f"✅ Saved (binary compat) → {binary_path}")
