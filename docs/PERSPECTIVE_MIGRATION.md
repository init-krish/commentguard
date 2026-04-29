# Migrating from Google Perspective API to CommentGuard

> **Google's Perspective API is shutting down December 31, 2026.**
> CommentGuard is an open-source, self-hosted drop-in replacement.

## Overview

| | Perspective API | CommentGuard |
|---|---|---|
| **Status** | ❌ Sunsetting Dec 2026  | ✅ Active, open-source |
| **Hosting** | Cloud only (Google) | Self-hosted (your infra) |
| **Privacy** | Data sent to Google | Data never leaves your servers |
| **Cost** | Free (was) | Free (forever) |
| **Categories** | 7 attributes | 6 categories |
| **Rate limits** | 1 QPS default | Unlimited (your hardware) |
| **API Key** | Required | Optional |

## Step 1: Deploy CommentGuard

```bash
git clone https://github.com/init-krish/commentguard
cd commentguard/backend
cp .env.example .env
docker compose up -d
```

Your API is now live at `http://localhost:8000`.

## Step 2: Change One Line of Code

CommentGuard has a Perspective-compatible endpoint. Just change the URL:

### Before (Perspective API)
```python
PERSPECTIVE_URL = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
params = {"key": "YOUR_API_KEY"}
response = requests.post(PERSPECTIVE_URL, params=params, json=payload)
```

### After (CommentGuard)
```python
COMMENTGUARD_URL = "http://localhost:8000/v1/comments:analyze"
# No API key needed!
response = requests.post(COMMENTGUARD_URL, json=payload)
```

**That's it.** The request and response format is identical.

## Step 3: Verify

The request format is the same:

```json
{
  "comment": { "text": "You are terrible" },
  "requestedAttributes": {
    "TOXICITY": {},
    "INSULT": {},
    "THREAT": {}
  }
}
```

The response format is the same:

```json
{
  "attributeScores": {
    "TOXICITY": {
      "spanScores": [{ "begin": 0, "end": 16, "score": { "value": 0.87, "type": "PROBABILITY" } }],
      "summaryScore": { "value": 0.87, "type": "PROBABILITY" }
    },
    "INSULT": {
      "summaryScore": { "value": 0.82, "type": "PROBABILITY" }
    },
    "THREAT": {
      "summaryScore": { "value": 0.12, "type": "PROBABILITY" }
    }
  },
  "languages": ["en"]
}
```

## Attribute Mapping

| Perspective Attribute | CommentGuard Category |
|---|---|
| `TOXICITY` | `toxic` |
| `SEVERE_TOXICITY` | `severe_toxic` |
| `INSULT` | `insult` |
| `THREAT` | `threat` |
| `IDENTITY_ATTACK` | `identity_hate` |
| `PROFANITY` | `obscene` |
| `OBSCENE` | `obscene` |

## Bonus: Use the Native API

While the Perspective-compatible endpoint works, CommentGuard's native API is simpler:

```bash
curl -X POST http://localhost:8000/moderate \
  -H "Content-Type: application/json" \
  -d '{"text": "You are terrible"}'
```

```json
{
  "label": "toxic",
  "toxic_prob": 0.87,
  "decision": "block",
  "categories": ["toxic", "insult"],
  "scores": {
    "toxic": 0.87,
    "severe_toxic": 0.12,
    "obscene": 0.34,
    "threat": 0.08,
    "insult": 0.82,
    "identity_hate": 0.05
  },
  "flagged": true
}
```

## Need Help?

- [API Documentation](http://localhost:8000/docs) (auto-generated Swagger UI)
- [Integration Examples](INTEGRATIONS.md) (Node, Django, Laravel, Next.js)
- [GitHub Issues](https://github.com/init-krish/commentguard/issues)
