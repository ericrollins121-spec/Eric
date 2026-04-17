const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const sourcesEl = document.getElementById("sources");
const resultsEl = document.getElementById("results");
const button = form.querySelector("button[type=submit]");
const savedToggle = document.getElementById("saved-toggle");

const SAVED_KEY = "rental-search:saved";
let savedUrls = new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || "[]"));
let showSavedOnly = false;
let lastListings = [];

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  await runSearch();
});

savedToggle.addEventListener("click", () => {
  showSavedOnly = !showSavedOnly;
  savedToggle.classList.toggle("active", showSavedOnly);
  renderResults(lastListings);
});

resultsEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".save-btn");
  if (!btn) return;
  const url = btn.dataset.url;
  if (savedUrls.has(url)) savedUrls.delete(url);
  else savedUrls.add(url);
  localStorage.setItem(SAVED_KEY, JSON.stringify([...savedUrls]));
  btn.classList.toggle("saved");
  btn.textContent = savedUrls.has(url) ? "♥" : "♡";
  if (showSavedOnly) renderResults(lastListings);
});

async function runSearch() {
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
    renderSources(json.sources || [], json.deduped || 0);
    lastListings = json.results || [];
    renderResults(lastListings);
    statusEl.textContent = `${json.count} listings in ${json.city}`;
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderSources(sources, deduped) {
  const parts = sources.map((s) => {
    const cls = s.ok ? "ok" : "bad";
    const label = s.ok ? `${s.source}: ${s.count}` : `${s.source}: error`;
    return `<span class="src ${cls}">${label}</span>`;
  });
  if (deduped) parts.push(`<span class="src">${deduped} duplicates merged</span>`);
  sourcesEl.innerHTML = parts.join("");
}

function renderResults(listings) {
  const filtered = showSavedOnly
    ? listings.filter((l) => savedUrls.has(l.url))
    : listings;

  if (!filtered.length) {
    resultsEl.innerHTML = `<p style="color:var(--muted);padding:0 0;">${
      showSavedOnly ? "No saved listings yet." : "No listings found. Try widening your filters."
    }</p>`;
    return;
  }
  resultsEl.innerHTML = filtered.map(card).join("");
}

function card(l) {
  const price = l.price ? `$${l.price.toLocaleString()}` : "—";
  const beds = l.bedrooms != null ? `${l.bedrooms} bd` : "";
  const loc = l.location || "";
  const img = l.image
    ? `<img src="${escapeAttr(l.image)}" alt="" loading="lazy" />`
    : "";
  const desc = l.description ? `<div class="desc">${escapeHtml(l.description)}</div>` : "";
  const posted = l.posted_at ? new Date(l.posted_at).toLocaleDateString() : "";
  const isSaved = savedUrls.has(l.url);
  return `
    <article class="card">
      ${img}
      <button class="save-btn ${isSaved ? "saved" : ""}" data-url="${escapeAttr(
    l.url
  )}" title="Save listing">${isSaved ? "♥" : "♡"}</button>
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

runSearch();
