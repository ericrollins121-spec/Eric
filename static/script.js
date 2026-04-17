const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const sourcesEl = document.getElementById("sources");
const resultsEl = document.getElementById("results");
const button = form.querySelector("button");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = new FormData(form);
  const params = new URLSearchParams();
  for (const [k, v] of data.entries()) {
    if (v) params.append(k, v);
  }

  button.disabled = true;
  statusEl.textContent = "Searching...";
  sourcesEl.innerHTML = "";
  resultsEl.innerHTML = "";

  try {
    const resp = await fetch(`/api/search?${params.toString()}`);
    const json = await resp.json();
    renderSources(json.sources || []);
    renderResults(json.results || []);
    statusEl.textContent = `${json.count} listings in ${json.city}`;
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    button.disabled = false;
  }
});

function renderSources(sources) {
  sourcesEl.innerHTML = sources
    .map((s) => {
      const cls = s.ok ? "ok" : "bad";
      const label = s.ok ? `${s.source}: ${s.count}` : `${s.source}: error`;
      return `<span class="src ${cls}">${label}</span>`;
    })
    .join("");
}

function renderResults(listings) {
  if (!listings.length) {
    resultsEl.innerHTML = `<p style="color:var(--muted);padding:0 0;">No listings found. Try widening your filters.</p>`;
    return;
  }
  resultsEl.innerHTML = listings.map(card).join("");
}

function card(l) {
  const price = l.price ? `$${l.price.toLocaleString()}` : "—";
  const beds = l.bedrooms != null ? `${l.bedrooms} bd` : "";
  const loc = l.location || "";
  const img = l.image
    ? `<img src="${escapeHtml(l.image)}" alt="" loading="lazy" />`
    : "";
  const desc = l.description ? `<div class="desc">${escapeHtml(l.description)}</div>` : "";
  const posted = l.posted_at ? new Date(l.posted_at).toLocaleDateString() : "";
  return `
    <article class="card">
      ${img}
      <div class="body">
        <a class="title" href="${escapeAttr(l.url)}" target="_blank" rel="noopener">${escapeHtml(
    l.title || "Listing"
  )}</a>
        <div class="meta">
          <span class="price">${price}</span>
          ${beds ? `<span>${beds}</span>` : ""}
          ${loc ? `<span>${escapeHtml(loc)}</span>` : ""}
        </div>
        ${desc}
        <div class="footer">
          <span class="src-badge">${escapeHtml(l.source)}</span>
          <span>${posted}</span>
        </div>
      </div>
    </article>
  `;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, "&#39;");
}

form.dispatchEvent(new Event("submit"));
