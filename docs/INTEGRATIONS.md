# 🔌 Integration Examples

Integrating CommentGuard into your stack is ridiculously easy. You don't need any complex SDKs if you don't want them — just a simple HTTP POST request.

## Option 1: Node.js (Easiest)

We built an official NPM package for Node environments (Next.js, Express, Nuxt, etc).

```bash
npm install commentguard-sdk
```

```javascript
import { CommentGuard } from 'commentguard-sdk';

const guard = new CommentGuard({ endpoint: 'http://localhost:8000' });

// Example: Express.js Chat Route
app.post('/api/chat/send', async (req, res) => {
  const { message, userId } = req.body;

  // 1. Check the message BEFORE saving it to the database
  const result = await guard.moderate(message);
  
  if (result.decision === 'block') {
    // 2. Reject the message entirely!
    return res.status(403).json({ 
      error: "Message blocked.",
      reason: result.categories.join(', ') // e.g. "toxic, threat"
    });
  }

  // 3. If safe, save to database and broadcast to users
  await database.saveMessage(userId, message);
  return res.status(200).json({ success: true });
});
```

---

## Option 2: Frontend (Vanilla JavaScript / React)

You can call the API directly from the browser (CORS is enabled by default).

```javascript
async function moderateComment(text) {
  const res = await fetch("http://localhost:8000/moderate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  
  const data = await res.json();
  
  if (data.decision === 'block') {
    alert("Please be nice!");
  }
}
```

---

## Option 3: Python (Django / FastAPI / Flask)

```python
import httpx

def is_toxic(text: str) -> bool:
    response = httpx.post(
        "http://localhost:8000/moderate",
        json={"text": text}
    )
    return response.json()["decision"] == "block"
```

---

## Option 4: PHP (Laravel / WordPress)

```php
$url = "http://localhost:8000/moderate";
$data = json_encode(["text" => "Hello world"]);

$options = [
    'http' => [
        'method'  => 'POST',
        'header'  => "Content-Type: application/json\r\n",
        'content' => $data
    ]
];

$context = stream_context_create($options);
$result = file_get_contents($url, false, $context);
$response = json_decode($result);

if ($response->decision === "block") {
    echo "Comment blocked.";
}
```

---

## Perspective API Drop-in

If you currently use `https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze`, simply point your URL to `http://localhost:8000/v1/comments:analyze`. No code changes required! See the [Perspective Migration Guide](PERSPECTIVE_MIGRATION.md) for details.
