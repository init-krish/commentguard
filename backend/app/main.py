"""
CommentGuard API — Production-Grade Toxic Comment Moderation
─────────────────────────────────────────────────────────────
POST /moderate    → { text }  →  { label, toxic_prob, decision, categories }
POST /predict     → alias for /moderate (backwards compat with extension)
GET  /health      → { status, model, version }
GET  /stats       → { total, toxic, non_toxic, toxic_rate, recent }
POST /feedback    → { text, correct_label } → stores false positive/negative
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from collections import deque
from datetime import datetime
import os, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from environment ───────────────────────────────────────────────────
THRESHOLD   = float(os.getenv("THRESHOLD", "0.5"))
MODEL_TYPE  = os.getenv("MODEL_TYPE", "classical")  # "classical" or "transformer"
ENV         = os.getenv("ENV", "development")

app = FastAPI(
    title="CommentGuard",
    description="Open-source toxic comment moderation API. POST /moderate with {text} to classify.",
    version="2.0.0",
    contact={"name": "CommentGuard OSS", "url": "https://github.com/init-krish/commentguard"},
)

# CORS — required for browser extensions and third-party websites
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stats store ─────────────────────────────────────────────────────
recent_log  = deque(maxlen=100)
stats_store = {"total": 0, "toxic": 0, "non_toxic": 0}
feedback_log = []

# ── Load model based on MODEL_TYPE env var ────────────────────────────────────
if MODEL_TYPE == "transformer":
    # Transformer path — uses unitary/toxic-bert via Hugging Face pipeline
    from transformers import pipeline as hf_pipeline
    logger.info("⏳ Loading transformer model (toxic-bert)…")
    _clf = hf_pipeline(
        "text-classification",
        model="unitary/toxic-bert",
        top_k=None,
        device=-1   # -1 = CPU; set to 0 for GPU
    )
    def _predict_prob(text: str) -> float:
        results = _clf(text[:512])[0]   # truncate long text
        for r in results:
            if r["label"].lower() in ("toxic", "label_1", "1"):
                return r["score"]
        return 1.0 - results[0]["score"]
    logger.info("✅ Transformer model loaded (unitary/toxic-bert)")

else:
    # Classical path — TF-IDF + Logistic Regression (your trained .joblib files)
    import joblib
    ML_DIR = os.path.join(os.path.dirname(__file__), "ml")
    try:
        _vec   = joblib.load(os.path.join(ML_DIR, "vectorizer.joblib"))
        _model = joblib.load(os.path.join(ML_DIR, "model.joblib"))
        logger.info("✅ Classical model loaded (TF-IDF + LogReg)")
    except FileNotFoundError as e:
        raise RuntimeError(f"❌ Missing model file: {e} → place .joblib files in app/ml/")

    def _predict_prob(text: str) -> float:
        vec = _vec.transform([text])
        return float(_model.predict_proba(vec)[0, 1])

# ── Request / Response schemas ────────────────────────────────────────────────
class ModerateRequest(BaseModel):
    text: str
    threshold: Optional[float] = None   # per-request threshold override
    site: Optional[str] = None          # e.g. "youtube", "reddit"

class ModerateResponse(BaseModel):
    label: str          # "toxic" or "non_toxic"
    toxic_prob: float   # 0.0 – 1.0
    decision: str       # "allow", "block", "review"
    categories: list    # placeholder — expand with multi-label model later

class FeedbackRequest(BaseModel):
    text: str
    correct_label: str  # "toxic" or "non_toxic"
    predicted_label: str

# ── Core classification logic ─────────────────────────────────────────────────
def classify(text: str, threshold: float) -> ModerateResponse:
    prob  = _predict_prob(text)
    label = "toxic" if prob >= threshold else "non_toxic"

    # Three-tier decision: block (high confidence) / review (borderline) / allow
    if prob >= threshold:
        decision = "block"
    elif prob >= threshold * 0.6:   # e.g. 0.3 if threshold=0.5
        decision = "review"
    else:
        decision = "allow"

    # Update stats
    stats_store["total"] += 1
    stats_store[label]   += 1
    recent_log.append({
        "text":    text[:100],
        "prob":    round(prob, 4),
        "label":   label,
        "decision": decision,
        "time":    datetime.utcnow().isoformat()
    })

    logger.info(f"prob={prob:.3f} | decision={decision} | text={text[:50]!r}")
    return ModerateResponse(
        label=label,
        toxic_prob=round(prob, 4),
        decision=decision,
        categories=["toxic"] if label == "toxic" else []
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_TYPE, "version": "2.0.0", "threshold": THRESHOLD}


@app.post("/moderate", response_model=ModerateResponse)
def moderate(req: ModerateRequest):
    """
    Main endpoint for website devs.
    Call this BEFORE saving a comment to your DB.
    Use req.threshold to override the default threshold per-site.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text cannot be empty")
    t = req.threshold if req.threshold is not None else THRESHOLD
    return classify(text, t)


@app.post("/predict", response_model=ModerateResponse)
def predict(req: ModerateRequest):
    """Alias for /moderate — backwards compatible with Chrome extension."""
    return moderate(req)


@app.get("/stats")
def get_stats():
    """Live moderation analytics — use this for your dashboard."""
    total = max(stats_store["total"], 1)
    return {
        "total":       stats_store["total"],
        "toxic":       stats_store["toxic"],
        "non_toxic":   stats_store["non_toxic"],
        "toxic_rate":  round(stats_store["toxic"] / total * 100, 1),
        "model":       MODEL_TYPE,
        "recent":      list(recent_log)[-10:]
    }


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """
    Collect false positives / false negatives from users.
    Used to improve the model over time.
    """
    entry = {
        "text":            req.text,
        "correct_label":   req.correct_label,
        "predicted_label": req.predicted_label,
        "time":            datetime.utcnow().isoformat()
    }
    feedback_log.append(entry)
    logger.info(f"Feedback: {entry}")
    return {"status": "recorded", "total_feedback": len(feedback_log)}
