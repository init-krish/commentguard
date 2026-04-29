document.addEventListener("DOMContentLoaded", () => {
  const apiUrlInput = document.getElementById("apiUrl");
  const thresholdInput = document.getElementById("threshold");
  const thresholdVal = document.getElementById("thresholdVal");
  const enabledToggle = document.getElementById("enabledToggle");
  const saveBtn = document.getElementById("saveBtn");
  const saveStatus = document.getElementById("saveStatus");
  const apiStatus = document.getElementById("apiStatus");

  // Load saved settings
  chrome.storage.sync.get(
    { apiUrl: "http://127.0.0.1:8000/moderate", threshold: 50, enabled: true },
    (items) => {
      apiUrlInput.value = items.apiUrl;
      thresholdInput.value = items.threshold;
      thresholdVal.textContent = items.threshold + "%";
      enabledToggle.checked = items.enabled;
      
      checkApiHealth(items.apiUrl);
    }
  );

  // Live update threshold text
  thresholdInput.addEventListener("input", (e) => {
    thresholdVal.textContent = e.target.value + "%";
  });

  // Save settings
  saveBtn.addEventListener("click", () => {
    const apiUrl = apiUrlInput.value.trim();
    const threshold = parseInt(thresholdInput.value, 10);
    const enabled = enabledToggle.checked;

    chrome.storage.sync.set({ apiUrl, threshold, enabled }, () => {
      saveStatus.style.opacity = "1";
      setTimeout(() => { saveStatus.style.opacity = "0"; }, 2000);
      
      checkApiHealth(apiUrl);
    });
  });

  // Check backend health
  async function checkApiHealth(url) {
    try {
      const healthUrl = url.replace("/moderate", "/health");
      const res = await fetch(healthUrl, { method: "GET" });
      if (res.ok) {
        apiStatus.textContent = "Online";
        apiStatus.className = "status-badge";
      } else {
        throw new Error("Bad status");
      }
    } catch (err) {
      apiStatus.textContent = "Offline";
      apiStatus.className = "status-badge offline";
    }
  }

  // Request stats from the active tab's content script
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { type: "getStats" }, (response) => {
        if (response && response.stats) {
          document.getElementById("statScanned").textContent = response.stats.scanned;
          document.getElementById("statBlocked").textContent = response.stats.blocked;
        }
      });
    }
  });
});