"""
CommentGuard — Model Training Script
─────────────────────────────────────
Dataset: Jigsaw Toxic Comment Classification (Kaggle)
Output:  backend/app/ml/vectorizer.joblib + model.joblib

Run on Kaggle:
    1. Open any Kaggle notebook on the Jigsaw competition.
    2. Paste this script and run.
    3. Download artifacts from /kaggle/working/.

Run on Colab:
    1. Upload train.csv from the Jigsaw dataset.
    2. Set DATA_PATH = "/content/train.csv".
    3. Run.
"""

import os, joblib, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH  = "/kaggle/input/jigsaw-toxic-comment-classification-challenge/train.csv"
OUT_DIR    = "/kaggle/working"          # change to "/content" on Colab
THRESHOLD  = 0.5

os.makedirs(OUT_DIR, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data…")
df = pd.read_csv(DATA_PATH)

TOXIC_COLS = ["toxic","severe_toxic","obscene","threat","insult","identity_hate"]
df["label"] = (df[TOXIC_COLS].sum(axis=1) > 0).astype(int)

texts  = df["comment_text"].fillna("").tolist()
labels = df["label"].tolist()

X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.1, random_state=42, stratify=labels
)
print(f"Train: {len(X_train):,} | Test: {len(X_test):,} | Toxic rate: {sum(labels)/len(labels):.1%}")

# ── Vectoriser ────────────────────────────────────────────────────────────────
print("Fitting TF-IDF…")
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

# ── Model ─────────────────────────────────────────────────────────────────────
print("Training Logistic Regression…")
model = LogisticRegression(C=5.0, solver="saga", max_iter=1000, n_jobs=-1)
model.fit(X_train_vec, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
probs = model.predict_proba(X_test_vec)[:, 1]
preds = (probs >= THRESHOLD).astype(int)
auc   = roc_auc_score(y_test, probs)
print(f"\nROC-AUC: {auc:.4f}")
print(classification_report(y_test, preds, target_names=["non_toxic","toxic"]))

# ── Save artifacts ────────────────────────────────────────────────────────────
vec_path   = os.path.join(OUT_DIR, "vectorizer.joblib")
model_path = os.path.join(OUT_DIR, "model.joblib")
joblib.dump(vec,   vec_path)
joblib.dump(model, model_path)
print(f"\n✅ Saved → {vec_path}")
print(f"✅ Saved → {model_path}")
print("\nNext: copy these two files into backend/app/ml/ then run uvicorn.")
