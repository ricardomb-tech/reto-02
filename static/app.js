const textEl = document.getElementById("text");
const buttonEl = document.getElementById("analyze");
const resultEl = document.getElementById("result");

async function analyze() {
  const text = textEl.value.trim();
  if (!text) return;

  buttonEl.disabled = true;
  buttonEl.textContent = "Analyzing…";
  resultEl.className = "visible";
  resultEl.textContent = "";

  try {
    const response = await fetch("/sentiment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const body = await response.json();

    if (!response.ok) {
      showError(`Error ${response.status}: ${body.detail || "request failed"}`);
      return;
    }

    showResult(body);
  } catch (err) {
    showError(`Request failed: ${err}`);
  } finally {
    buttonEl.disabled = false;
    buttonEl.textContent = "Analyze";
  }
}

function clearResult() {
  while (resultEl.firstChild) resultEl.removeChild(resultEl.firstChild);
}

function showError(message) {
  clearResult();
  const span = document.createElement("span");
  span.className = "error";
  span.textContent = message;
  resultEl.appendChild(span);
}

const EMOJI_BY_LABEL = {
  POSITIVE: "😊",
  NEGATIVE: "😞",
  NEUTRAL: "😐",
};

function showResult(body) {
  clearResult();
  const labelDiv = document.createElement("div");
  labelDiv.className = `label ${body.label}`;

  const emojiSpan = document.createElement("span");
  emojiSpan.className = "emoji";
  emojiSpan.textContent = EMOJI_BY_LABEL[body.label] || "🤔";

  labelDiv.append(emojiSpan, document.createTextNode(body.label));

  const confidenceDiv = document.createElement("div");
  confidenceDiv.className = "confidence";

  const barEl = document.createElement("div");
  barEl.className = "confidence-bar";
  const fillEl = document.createElement("div");
  fillEl.className = `confidence-fill ${body.label}`;
  fillEl.style.width = `${Math.round(body.score * 100)}%`;
  barEl.appendChild(fillEl);

  const confidenceLabelEl = document.createElement("span");
  confidenceLabelEl.className = "confidence-label";
  confidenceLabelEl.textContent = `${Math.round(body.score * 100)}% confidence`;

  confidenceDiv.append(barEl, confidenceLabelEl);

  const metaDiv = document.createElement("div");
  metaDiv.className = "meta";
  metaDiv.textContent = `cached: ${body.cached}`;

  resultEl.append(labelDiv, confidenceDiv, metaDiv);
}

buttonEl.addEventListener("click", analyze);
textEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) analyze();
});
