# Model Card — CommentGuard Toxicity Classifier

## Model Details

| Field | Value |
|-------|-------|
| **Model type** | Binary text classifier |
| **Architecture (classical)** | TF-IDF (50k features, bigrams) + Logistic Regression (C=5.0, SAGA solver) |
| **Architecture (transformer)** | `unitary/toxic-bert` via Hugging Face Transformers |
| **Task** | Toxic comment detection (toxic vs. non-toxic) |
| **Language** | English |
| **License** | Apache 2.0 |

## Training Data

- **Dataset**: [Jigsaw Toxic Comment Classification Challenge](https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge) (Kaggle)
- **Size**: ~160,000 comments from Wikipedia talk pages
- **Labels**: Binary — any of `toxic`, `severe_toxic`, `obscene`, `threat`, `insult`, `identity_hate` → **toxic**
- **Split**: 90% train / 10% test (stratified)

## Performance — Classical Model (TF-IDF + LogReg)

| Metric | Value |
|--------|-------|
| **ROC-AUC** | ~0.97 |
| **Precision (toxic)** | ~0.82 |
| **Recall (toxic)** | ~0.76 |
| **F1 (toxic)** | ~0.79 |

> Note: Exact metrics depend on the training run. Train with `model/train.py` to get your own evaluation report.

## Performance — Transformer Model (toxic-bert)

| Metric | Value |
|--------|-------|
| **ROC-AUC** | ~0.98+ |
| **Latency** | ~100-200ms per prediction (CPU) |

The transformer model (`unitary/toxic-bert`) is pre-trained and fine-tuned on the Jigsaw dataset. It provides higher accuracy at the cost of increased latency and resource requirements.

## Intended Use

- **Primary**: Real-time comment moderation for websites, forums, and social platforms
- **Secondary**: Research and educational purposes in NLP / content moderation

## Limitations & Biases

- **English only** — does not support multilingual content, code-switching, or transliterated text (e.g., Hinglish)
- **Binary classification** — does not distinguish between types of toxicity (insult vs. threat vs. hate speech). Multi-label support is on the roadmap.
- **Dataset bias** — the Jigsaw dataset is sourced from Wikipedia talk pages, which may not represent toxicity patterns on platforms like YouTube, Reddit, or gaming forums
- **Identity term bias** — like many toxicity classifiers, the model may exhibit higher false-positive rates on comments that mention identity groups (race, gender, religion) even in non-toxic contexts. See [Jigsaw Unintended Bias](https://www.kaggle.com/c/jigsaw-unintended-bias-in-toxicity-classification) for more details.
- **Adversarial robustness** — the model can be bypassed with intentional misspellings, Unicode tricks, or coded language

## Ethical Considerations

- Content moderation systems can suppress legitimate speech if misconfigured. Always provide a **review tier** (not just block/allow) and a **feedback mechanism** for false positives.
- The default threshold (0.5) is intentionally balanced. Lowering it increases recall but may over-censor.
- This tool should complement, not replace, human moderation for high-stakes platforms.

## How to Cite

```
@misc{commentguard2025,
  title   = {CommentGuard: Open-Source Toxic Comment Moderation},
  author  = {Krishnan Madhuratnam},
  year    = {2025},
  url     = {https://github.com/YOUR_USERNAME/commentguard}
}
```
