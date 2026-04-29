# CommentGuard — Developer Integration Guide

Copy-paste examples for adding CommentGuard moderation to your website backend.

## API Contract

```
POST /moderate
Content-Type: application/json

{
  "text":      "comment text here",
  "threshold": 0.5,          // optional: override default threshold per request
  "site":      "my_forum"    // optional: tag for analytics
}
```

Response:
```json
{
  "label":      "toxic",
  "toxic_prob": 0.93,
  "decision":   "block",
  "categories": ["toxic"]
}
```

Decisions: `allow` → save the comment | `review` → queue for human review | `block` → reject

---

## Node.js / Express

```js
const express = require("express");
const app     = express();
app.use(express.json());

async function moderate(text) {
  const res  = await fetch("http://127.0.0.1:8000/moderate", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ text })
  });
  return res.json();  // { label, toxic_prob, decision, categories }
}

app.post("/comments", async (req, res) => {
  const { userId, text } = req.body;
  const result = await moderate(text);

  if (result.decision === "allow") {
    // db.saveComment(userId, text, "published");
    return res.json({ status: "published" });
  } else if (result.decision === "review") {
    // db.saveComment(userId, text, "pending_review");
    return res.json({ status: "pending_review", message: "Your comment is under review." });
  } else {
    // db.saveComment(userId, text, "blocked");  // optional: keep for audit log
    return res.status(400).json({ status: "blocked", message: "Comment contains inappropriate content." });
  }
});
```

---

## Python / Django

```python
import requests

COMMENTGUARD_URL = "http://127.0.0.1:8000/moderate"

def submit_comment(request):
    text    = request.POST.get("text", "")
    user_id = request.user.id

    resp   = requests.post(COMMENTGUARD_URL, json={"text": text}, timeout=5)
    result = resp.json()  # { label, toxic_prob, decision }

    if result["decision"] == "allow":
        Comment.objects.create(user_id=user_id, text=text, status="published")
        return JsonResponse({"status": "published"})
    elif result["decision"] == "review":
        Comment.objects.create(user_id=user_id, text=text, status="pending_review")
        return JsonResponse({"status": "pending_review"})
    else:
        return JsonResponse({"status": "blocked", "error": "Inappropriate content"}, status=400)
```

---

## PHP / Laravel

```php
use Illuminate\Support\Facades\Http;

public function store(Request $request) {
    $text   = $request->input('text');
    $result = Http::post('http://127.0.0.1:8000/moderate', ['text' => $text])->json();

    if ($result['decision'] === 'allow') {
        Comment::create(['user_id' => auth()->id(), 'text' => $text, 'status' => 'published']);
        return response()->json(['status' => 'published']);
    } elseif ($result['decision'] === 'review') {
        Comment::create(['user_id' => auth()->id(), 'text' => $text, 'status' => 'pending_review']);
        return response()->json(['status' => 'pending_review']);
    } else {
        return response()->json(['status' => 'blocked'], 400);
    }
}
```

---

## Next.js (API route)

```js
// pages/api/comments.js
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const { text } = req.body;

  const guard = await fetch("http://127.0.0.1:8000/moderate", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ text })
  }).then(r => r.json());

  if (guard.decision === "block") {
    return res.status(400).json({ error: "Comment blocked", toxic_prob: guard.toxic_prob });
  }

  // save to DB here…
  return res.json({ status: guard.decision });
}
```

---

## Self-Host with Docker

```bash
# 1. Clone the repo
git clone https://github.com/init-krish/commentguard
cd commentguard/backend

# 2. Copy your trained model files
cp path/to/vectorizer.joblib app/ml/
cp path/to/model.joblib       app/ml/

# 3. Start
docker compose up -d

# 4. Test
curl -X POST http://localhost:8000/moderate \
  -H "Content-Type: application/json" \
  -d '{"text": "I hate you"}'
```

