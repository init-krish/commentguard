/**
 * CommentGuard — Multi-Site Content Script v2.0
 * Supports: YouTube, Reddit, Hacker News
 */

const SITE_SELECTORS = {
  "youtube.com": "ytd-comment-thread-renderer #content-text",
  "reddit.com": "[data-testid='comment'] p",
  "news.ycombinator.com": ".comment .commtext"
};

const hostname = window.location.hostname;
const siteKey = Object.keys(SITE_SELECTORS).find(k => hostname.includes(k));
const COMMENT_SELECTOR = SITE_SELECTORS[siteKey];

if (!COMMENT_SELECTOR) {
  console.log("[CommentGuard] Site not supported:", hostname);
}

let API_URL = "http://127.0.0.1:8000/moderate";
let THRESHOLD = 50; // stored as percent in popup
let ENABLED = true;

let SESSION_STATS = {
  scanned: 0,
  blurred: 0,
  blocked: 0,
  topProb: 0,
  topText: ""
};

chrome.storage.sync.get(
  { apiUrl: "http://127.0.0.1:8000/moderate", threshold: 50, enabled: true },
  (s) => {
    API_URL = s.apiUrl;
    THRESHOLD = s.threshold;
    ENABLED = s.enabled;

    console.log(`[CommentGuard] Loaded | API=${API_URL} | threshold=${THRESHOLD}% | enabled=${ENABLED}`);

    if (ENABLED && COMMENT_SELECTOR) {
      processVisible();
      observeNewComments();
    }
  }
);

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "getStats") {
    sendResponse({ stats: SESSION_STATS });
  }

  if (msg.type === "clearStats") {
    SESSION_STATS = {
      scanned: 0,
      blurred: 0,
      blocked: 0,
      topProb: 0,
      topText: ""
    };
    sendResponse({ ok: true });
  }

  return true;
});

const processed = new WeakSet();

async function classifyComment(el) {
  if (!ENABLED || processed.has(el)) return;
  processed.add(el);

  const text = el.innerText?.trim();
  if (!text || text.length < 3) return;

  SESSION_STATS.scanned++;

  try {
    const thresholdDecimal = THRESHOLD / 100;

    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        threshold: thresholdDecimal,
        site: siteKey
      })
    });

    if (!res.ok) {
      console.warn("[CommentGuard] API error:", res.status);
      return;
    }

    const data = await res.json();

    if (data.toxic_prob > SESSION_STATS.topProb) {
      SESSION_STATS.topProb = data.toxic_prob;
      SESSION_STATS.topText = text.slice(0, 80);
    }

    if (data.decision === "block") {
      SESSION_STATS.blocked++;
      applyBlockStyle(el, data);
    } else if (data.decision === "review") {
      SESSION_STATS.blurred++;
      applyReviewStyle(el, data);
    }

    chrome.runtime.sendMessage({
      type: "statsUpdate",
      stats: SESSION_STATS
    }).catch(() => {});

  } catch (err) {
    console.error("[CommentGuard] API unreachable:", err.message);
  }
}

function applyBlockStyle(el, data) {
  el.style.cssText += `
    filter: blur(6px);
    background: rgba(220,0,0,0.04);
    border-radius: 6px;
    transition: filter 0.3s ease;
    cursor: pointer;
  `;

  const pct = (data.toxic_prob * 100).toFixed(0);
  const badge = makeBadge(`⛔ Toxic ${pct}%`, "#cc0000");
  el.appendChild(badge);

  el.addEventListener("click", () => {
    el.style.filter = "none";
    el.style.background = "transparent";
    badge.textContent = "✅ Revealed";
    badge.style.background = "#555";
    sendFeedback(textFromElement(el), "non_toxic", "toxic");
  }, { once: true });
}

function applyReviewStyle(el, data) {
  el.style.cssText += `
    filter: blur(3px);
    border-left: 3px solid #f59e0b;
    padding-left: 8px;
    background: rgba(245,158,11,0.05);
    border-radius: 4px;
    transition: filter 0.3s ease;
    cursor: pointer;
  `;

  const pct = (data.toxic_prob * 100).toFixed(0);
  const badge = makeBadge(`⚠ Review ${pct}%`, "#b45309");
  el.appendChild(badge);

  el.addEventListener("click", () => {
    el.style.filter = "none";
    el.style.background = "transparent";
    badge.textContent = "✅ Revealed";
    badge.style.background = "#555";
    sendFeedback(textFromElement(el), "non_toxic", "borderline");
  }, { once: true });
}

function makeBadge(text, bg) {
  const b = document.createElement("span");
  b.textContent = text;
  b.style.cssText = `
    display: inline-block;
    background: ${bg};
    color: #fff;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 7px;
    border-radius: 12px;
    margin-left: 8px;
    vertical-align: middle;
    font-family: -apple-system, sans-serif;
    letter-spacing: 0.3px;
  `;
  return b;
}

function textFromElement(el) {
  return el.innerText?.replace(/⛔ Toxic \\d+%|⚠ Review \\d+%|✅ Revealed/g, "").trim() || "";
}

async function sendFeedback(text, correctLabel, predictedLabel) {
  try {
    await fetch(API_URL.replace("/moderate", "/feedback"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        correct_label: correctLabel,
        predicted_label: predictedLabel
      })
    });
  } catch (_) {}
}

function processVisible() {
  document.querySelectorAll(COMMENT_SELECTOR).forEach(classifyComment);
}

function observeNewComments() {
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;

        if (node.matches?.(COMMENT_SELECTOR)) {
          classifyComment(node);
        } else {
          node.querySelectorAll?.(COMMENT_SELECTOR).forEach(classifyComment);
        }
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}