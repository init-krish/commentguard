"""
CommentGuard API v3.0 — Multi-Label Toxic Comment Moderation
─────────────────────────────────────────────────────────────
POST /moderate            → single text moderation (multi-label)
POST /moderate/batch      → batch moderation (array of texts)
POST /predict             → alias for /moderate (extension compat)
POST /v1/comments:analyze → Perspective API compatible endpoint
GET  /health              → health check
GET  /stats               → live analytics
POST /feedback            → false positive/negative reporting
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from collections import deque
from datetime import datetime, timezone
import os, logging, time

from app.preprocess import preprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from environment ───────────────────────────────────────────────────
THRESHOLD   = float(os.getenv("THRESHOLD", "0.5"))
MODEL_TYPE  = os.getenv("MODEL_TYPE", "classical")  # "classical" or "transformer"
ENV         = os.getenv("ENV", "development")

# All toxicity categories (matches Jigsaw dataset labels)
CATEGORIES = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

app = FastAPI(
    title="CommentGuard",
    description=(
        "Open-source, self-hostable toxic comment moderation API.\n\n"
        "**Features:**\n"
        "- Multi-label classification (6 toxicity categories)\n"
        "- Perspective API compatible endpoint\n"
        "- Batch moderation\n"
        "- Anti-evasion text preprocessing\n"
        "- Configurable thresholds\n\n"
        "Drop-in replacement for Google's Perspective API (sunsetting Dec 2026)."
    ),
    version="3.0.0",
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
recent_log   = deque(maxlen=200)
stats_store  = {"total": 0, "toxic": 0, "non_toxic": 0, "by_category": {c: 0 for c in CATEGORIES}}
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

    def _predict_multi(text: str) -> Dict[str, float]:
        """Returns per-category probabilities using transformer model."""
        results = _clf(text[:512])[0]
        probs = {}
        for r in results:
            label = r["label"].lower()
            if label in ("toxic", "label_1", "1"):
                probs["toxic"] = r["score"]
            else:
                probs["toxic"] = 1.0 - r["score"]
        # toxic-bert is single-label; approximate other categories from toxic score
        toxic_p = probs.get("toxic", 0.0)
        return {
            "toxic":         toxic_p,
            "severe_toxic":  toxic_p * 0.4,   # conservative estimate
            "obscene":       toxic_p * 0.7,
            "threat":        toxic_p * 0.2,
            "insult":        toxic_p * 0.8,
            "identity_hate": toxic_p * 0.3,
        }

    logger.info("✅ Transformer model loaded (unitary/toxic-bert)")

else:
    # Classical path — TF-IDF + per-category Logistic Regression
    import joblib
    ML_DIR = os.path.join(os.path.dirname(__file__), "ml")

    # Try multi-label models first, fall back to single binary model
    models_path = os.path.join(ML_DIR, "models.joblib")
    vec_path    = os.path.join(ML_DIR, "vectorizer.joblib")
    single_path = os.path.join(ML_DIR, "model.joblib")

    try:
        _vec = joblib.load(vec_path)
        logger.info("✅ Vectorizer loaded")
    except FileNotFoundError as e:
        raise RuntimeError(f"❌ Missing vectorizer: {e} → place .joblib files in app/ml/")

    _multi_models = None
    _single_model = None

    if os.path.exists(models_path):
        _multi_models = joblib.load(models_path)
        logger.info(f"✅ Multi-label models loaded ({len(_multi_models)} categories)")
    elif os.path.exists(single_path):
        _single_model = joblib.load(single_path)
        logger.info("✅ Single binary model loaded (legacy mode)")
    else:
        raise RuntimeError("❌ No model files found → place models.joblib or model.joblib in app/ml/")

    def _predict_multi(text: str) -> Dict[str, float]:
        """Returns per-category probabilities using classical models."""
        vec = _vec.transform([text])
        if _multi_models:
            return {
                cat: float(model.predict_proba(vec)[0, 1])
                for cat, model in _multi_models.items()
            }
        else:
            # Legacy single model — approximate categories from binary score
            prob = float(_single_model.predict_proba(vec)[0, 1])
            return {
                "toxic":         prob,
                "severe_toxic":  prob * 0.4,
                "obscene":       prob * 0.7,
                "threat":        prob * 0.2,
                "insult":        prob * 0.8,
                "identity_hate": prob * 0.3,
            }

# ── Request / Response schemas ────────────────────────────────────────────────
class CategoryScores(BaseModel):
    toxic: float = 0.0
    severe_toxic: float = 0.0
    obscene: float = 0.0
    threat: float = 0.0
    insult: float = 0.0
    identity_hate: float = 0.0

class ModerateRequest(BaseModel):
    text: str
    threshold: Optional[float] = None   # per-request threshold override
    site: Optional[str] = None          # e.g. "youtube", "reddit"

class ModerateResponse(BaseModel):
    label: str                # "toxic" or "non_toxic"
    toxic_prob: float         # 0.0 – 1.0 (max across categories)
    decision: str             # "allow", "block", "review"
    categories: List[str]     # list of triggered category names
    scores: CategoryScores    # per-category probability scores
    flagged: bool             # true if any category >= threshold

class BatchRequest(BaseModel):
    texts: List[str] = Field(..., max_length=100, description="Array of texts to moderate (max 100)")
    threshold: Optional[float] = None
    site: Optional[str] = None

class BatchResponse(BaseModel):
    results: List[ModerateResponse]
    total: int
    toxic_count: int
    processing_time_ms: float

class FeedbackRequest(BaseModel):
    text: str
    correct_label: str       # "toxic" or "non_toxic"
    predicted_label: str

# ── Perspective API compatibility schemas ─────────────────────────────────────
class PerspectiveRequest(BaseModel):
    comment: dict             # {"text": "..."}
    requestedAttributes: dict # {"TOXICITY": {}, "INSULT": {}, ...}
    languages: Optional[List[str]] = None

class PerspectiveSpanScore(BaseModel):
    begin: int = 0
    end: int = 0
    score: dict

class PerspectiveAttributeScore(BaseModel):
    spanScores: List[PerspectiveSpanScore]
    summaryScore: dict

# ── Category mapping for Perspective API compat ──────────────────────────────
PERSPECTIVE_MAP = {
    "TOXICITY":         "toxic",
    "SEVERE_TOXICITY":  "severe_toxic",
    "INSULT":           "insult",
    "THREAT":           "threat",
    "IDENTITY_ATTACK":  "identity_hate",
    "PROFANITY":        "obscene",
    "OBSCENE":          "obscene",
}

# ── Core classification logic ─────────────────────────────────────────────────
def classify(text: str, threshold: float) -> ModerateResponse:
    """Classify a single text with anti-evasion preprocessing."""
    # Preprocess for anti-evasion
    cleaned = preprocess(text)

    # Get per-category scores
    scores = _predict_multi(cleaned)

    # Round scores
    scores = {k: round(v, 4) for k, v in scores.items()}

    # Find triggered categories
    triggered = [cat for cat, prob in scores.items() if prob >= threshold]

    # Overall toxic probability (max across categories)
    max_prob = max(scores.values())
    label = "toxic" if triggered else "non_toxic"

    # Three-tier decision
    if max_prob >= threshold:
        decision = "block"
    elif max_prob >= threshold * 0.6:
        decision = "review"
    else:
        decision = "allow"

    # Update stats
    stats_store["total"] += 1
    stats_store[label] += 1
    for cat in triggered:
        stats_store["by_category"][cat] = stats_store["by_category"].get(cat, 0) + 1

    recent_log.append({
        "text":       text[:120],
        "max_prob":   round(max_prob, 4),
        "label":      label,
        "decision":   decision,
        "categories": triggered,
        "time":       datetime.now(timezone.utc).isoformat(),
    })

    logger.info(f"prob={max_prob:.3f} | decision={decision} | cats={triggered} | text={text[:50]!r}")

    return ModerateResponse(
        label=label,
        toxic_prob=round(max_prob, 4),
        decision=decision,
        categories=triggered,
        scores=CategoryScores(**scores),
        flagged=bool(triggered),
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Health check — returns model type, version, and configuration."""
    return {
        "status": "ok",
        "model": MODEL_TYPE,
        "version": "3.0.0",
        "threshold": THRESHOLD,
        "categories": CATEGORIES,
        "features": ["multi-label", "anti-evasion", "batch", "perspective-compat"],
    }


@app.post("/moderate", response_model=ModerateResponse)
def moderate(req: ModerateRequest):
    """
    Main moderation endpoint — multi-label classification.

    Returns per-category toxicity scores (toxic, severe_toxic, obscene,
    threat, insult, identity_hate) with an overall decision.

    Call this BEFORE saving a comment to your DB.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text cannot be empty")
    t = req.threshold if req.threshold is not None else THRESHOLD
    return classify(text, t)


@app.post("/moderate/batch", response_model=BatchResponse)
def moderate_batch(req: BatchRequest):
    """
    Batch moderation — classify up to 100 texts in one request.

    Useful for moderating comment threads, bulk imports, or backfill operations.
    """
    if not req.texts:
        raise HTTPException(status_code=422, detail="texts array cannot be empty")
    if len(req.texts) > 100:
        raise HTTPException(status_code=422, detail="Maximum 100 texts per batch")

    t = req.threshold if req.threshold is not None else THRESHOLD
    start = time.time()

    results = []
    for text in req.texts:
        text = text.strip()
        if text:
            results.append(classify(text, t))
        else:
            # Skip empty texts but include a placeholder
            results.append(ModerateResponse(
                label="non_toxic", toxic_prob=0.0, decision="allow",
                categories=[], scores=CategoryScores(), flagged=False,
            ))

    elapsed = (time.time() - start) * 1000
    toxic_count = sum(1 for r in results if r.flagged)

    return BatchResponse(
        results=results,
        total=len(results),
        toxic_count=toxic_count,
        processing_time_ms=round(elapsed, 2),
    )


@app.post("/predict", response_model=ModerateResponse)
def predict(req: ModerateRequest):
    """Alias for /moderate — backwards compatible with Chrome extension v2."""
    return moderate(req)


@app.post("/v1/comments:analyze")
def perspective_compat(req: PerspectiveRequest):
    """
    Perspective API compatible endpoint.

    Drop-in replacement for Google's Perspective API (sunsetting Dec 2026).
    Accepts the same request format and returns the same response structure.

    Migrate by changing your base URL:
      - Before: https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze
      - After:  http://your-server:8000/v1/comments:analyze

    No API key required. No rate limits. Self-hosted.
    """
    text = req.comment.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="comment.text cannot be empty")

    # Get multi-label scores
    cleaned = preprocess(text)
    scores = _predict_multi(cleaned)
    scores = {k: round(v, 4) for k, v in scores.items()}

    # Build Perspective-format response
    attribute_scores = {}
    for perspective_name, our_name in PERSPECTIVE_MAP.items():
        if perspective_name in req.requestedAttributes:
            prob = scores.get(our_name, 0.0)
            attribute_scores[perspective_name] = {
                "spanScores": [{
                    "begin": 0,
                    "end": len(text),
                    "score": {"value": prob, "type": "PROBABILITY"},
                }],
                "summaryScore": {"value": prob, "type": "PROBABILITY"},
            }

    return {
        "attributeScores": attribute_scores,
        "languages": req.languages or ["en"],
        "detectedLanguages": ["en"],
    }


@app.get("/stats")
def get_stats():
    """Live moderation analytics — category breakdown included."""
    total = max(stats_store["total"], 1)
    return {
        "total":        stats_store["total"],
        "toxic":        stats_store["toxic"],
        "non_toxic":    stats_store["non_toxic"],
        "toxic_rate":   round(stats_store["toxic"] / total * 100, 1),
        "by_category":  stats_store["by_category"],
        "model":        MODEL_TYPE,
        "version":      "3.0.0",
        "recent":       list(recent_log)[-10:],
    }


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """
    Collect false positives / false negatives from users.
    Used to improve the model over time via active learning.
    """
    entry = {
        "text":            req.text,
        "correct_label":   req.correct_label,
        "predicted_label": req.predicted_label,
        "time":            datetime.now(timezone.utc).isoformat(),
    }
    feedback_log.append(entry)
    logger.info(f"Feedback: {entry}")
    return {"status": "recorded", "total_feedback": len(feedback_log)}
