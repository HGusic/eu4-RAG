const form = document.getElementById("ask-form");
const questionEl = document.getElementById("question");
const kEl = document.getElementById("k");
const btn = document.getElementById("ask-btn");
const statusEl = document.getElementById("status");
const answerPanel = document.getElementById("answer-panel");
const answerEl = document.getElementById("answer");
const sourcesPanel = document.getElementById("sources-panel");
const sourcesEl = document.getElementById("sources");

function setStatus(text, isError) {
  statusEl.hidden = !text;
  statusEl.textContent = text;
  statusEl.classList.toggle("error", Boolean(isError));
}

function renderSources(sources) {
  sourcesEl.innerHTML = "";
  sources.forEach((s) => {
    const div = document.createElement("article");
    div.className = "source";
    div.innerHTML = `
      <div><a href="${s.url}" target="_blank" rel="noopener">${s.title} — ${s.section}</a></div>
      <div class="meta">distance ${s.distance}</div>
      <p></p>
    `;
    div.querySelector("p").textContent = s.text;
    sourcesEl.appendChild(div);
  });
  sourcesPanel.hidden = sources.length === 0;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionEl.value.trim();
  const k = Number(kEl.value) || 5;
  if (!question) return;

  btn.disabled = true;
  answerEl.textContent = "";
  answerPanel.hidden = false;
  sourcesPanel.hidden = true;
  setStatus("Searching wiki and generating…");

  try {
    const response = await fetch("/api/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, k }),
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const err = await response.json();
        detail = err.detail || detail;
      } catch (_) {
        /* ignore */
      }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "sources") {
          renderSources(payload.sources);
          setStatus("Writing answer…");
        } else if (payload.type === "token") {
          answerEl.textContent += payload.text;
        } else if (payload.type === "error") {
          throw new Error(payload.detail);
        } else if (payload.type === "done") {
          setStatus("");
        }
      }
    }
    setStatus("");
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    btn.disabled = false;
  }
});
