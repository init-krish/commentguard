// CommentGuard popup.js — v2.0

chrome.storage.sync.get(
  { apiUrl: "http://127.0.0.1:8000/moderate", threshold: 50, enabled: true },
  (s) => {
    document.getElementById("apiUrl").value    = s.apiUrl;
    document.getElementById("threshold").value = s.threshold;
    document.getElementById("enabled").checked = s.enabled;
    updateThresholdLabel(s.threshold);
  }
);

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (!tabs[0]) return;
  chrome.tabs.sendMessage(tabs[0].id, { type: "getStats" }, (resp) => {
    if (chrome.runtime.lastError) return;
    if (resp?.stats) renderStats(resp.stats);
  });
});

document.getElementById("threshold").addEventListener("input", (e) => {
  updateThresholdLabel(parseInt(e.target.value));
});

function updateThresholdLabel(val) {
  const pct = parseInt(val);
  document.getElementById("threshold-display").textContent =
    pct <= 20 ? `${pct}% — Max strict` :
    pct <= 35 ? `${pct}% — Very strict` :
    pct <= 55 ? `${pct}% — Standard` :
    pct <= 70 ? `${pct}% — Lenient` :
                `${pct}% — Very lenient`;
}

document.getElementById("save").addEventListener("click", () => {
  const settings = {
    apiUrl:    document.getElementById("apiUrl").value.trim(),
    threshold: parseInt(document.getElementById("threshold").value),
    enabled:   document.getElementById("enabled").checked
  };
  chrome.storage.sync.set(settings, () => {
    const btn = document.getElementById("save");
    btn.textContent = "✓ Saved! Reload tab to apply.";
    btn.style.background = "#166534";
    setTimeout(() => {
      btn.textContent = "Save Settings";
      btn.style.background = "#cc0000";
    }, 2500);
  });
});

document.getElementById("reset").addEventListener("click", () => {
  const defaults = { apiUrl: "http://127.0.0.1:8000/moderate", threshold: 50, enabled: true };
  chrome.storage.sync.set(defaults, () => {
    document.getElementById("apiUrl").value    = defaults.apiUrl;
    document.getElementById("threshold").value = defaults.threshold;
    document.getElementById("enabled").checked = defaults.enabled;
    updateThresholdLabel(defaults.threshold);
  });
});

document.getElementById("clear-stats").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) return;
    chrome.tabs.sendMessage(tabs[0].id, { type: "clearStats" }, (resp) => {
      if (chrome.runtime.lastError) return;
      renderStats({ scanned: 0, blurred: 0, blocked: 0, topProb: 0, topText: "" });
      document.getElementById("top-hit-card").classList.remove("visible");
    });
  });
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "statsUpdate") renderStats(msg.stats);
});

function renderStats(stats) {
  setStatNum("stat-scanned", stats.scanned || 0);
  setStatNum("stat-blurred",  stats.blurred  || 0);
  setStatNum("stat-blocked",  stats.blocked  || 0);

  const prob = stats.topProb || 0;
  document.getElementById("stat-top-prob").textContent = prob > 0 ? Math.round(prob * 100) + "%" : "—";

  if (stats.topText && prob > 0) {
    document.getElementById("top-hit-card").classList.add("visible");
    document.getElementById("top-hit-text").textContent  = stats.topText;
    document.getElementById("top-hit-score").textContent =
      `Toxicity: ${Math.round(prob * 100)}% — ${getToxLabel(prob)}`;
  }
}

function setStatNum(id, val) {
  const el = document.getElementById(id);
  if (el.textContent != String(val)) {
    el.textContent = val;
    el.classList.add("flash");
    setTimeout(() => el.classList.remove("flash"), 400);
  }
}

function getToxLabel(prob) {
  if (prob >= 0.9)  return "Extremely toxic";
  if (prob >= 0.75) return "Highly toxic";
  if (prob >= 0.5)  return "Toxic";
  return "Borderline";
}