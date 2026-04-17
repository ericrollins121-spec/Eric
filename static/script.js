const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const sourcesEl = document.getElementById("sources");
const resultsEl = document.getElementById("results");
const button = form.querySelector("button[type=submit]");
const savedToggle = document.getElementById("saved-toggle");
const rssLink = document.getElementById("rss-link");

const SAVED_KEY = "rental-search:saved";
const SEEN_KEY = "rental-search:seen";

let savedUrls = new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || "[]"));
let seenUrls = new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]"));
let showSavedOnly = false;
let lastListings = [];
let freshUrls = new Set();

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
  btn.textContent = savedUrls.has(url) ? "\u2665" : "\u2661";
  if (showSavedOnly) renderResults(lastListings);
});

function currentQueryString() {
  const data = new FormData(form);
  const params = new URLSearchParams();
  for (const [k, v] of data.entries()) if (v) params.append(k, v);
  return params.toString();
}

async function runSearch() {
  const qs = currentQueryString();
  rssLink.href = `/feed.rss?${qs}`;

  button.disabled = true;
  statusEl.textContent = "Searching...";
  sourcesEl.innerHTML = "";
  resultsEl.innerHTML = "";

  try {
    const resp = await fetch(`/api/search?${qs}`);
    const json = await resp.json();
    renderSources(json.sources || [], json.deduped || 0);

    lastListings = json.results || [];
    freshUrls = new Set(
      lastListings.map((l) => l.url).filter((u) => u && !seenUrls.has(u))
    );
    for (const u of freshUrls) seenUrls.add(u);
    localStorage.setItem(SEEN_KEY, JSON.stringify([...seenUrls].slice(-2000)));

    renderResults(lastListings);
    const freshNote = freshUrls.size ? ` · ${freshUrls.size} new` : "";
    statusEl.textContent = `${json.count} listings in ${json.city}${freshNote}`;
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
  const price = l.price ? `$${l.price.toLocaleString()}` : "\u2014";
  const beds = l.bedrooms != null ? `${l.bedrooms} bd` : "";
  const loc = l.location || "";
  const img = l.image
    ? `<img src="${escapeAttr(l.image)}" alt="" loading="lazy" />`
    : "";
  const desc = l.description ? `<div class="desc">${escapeHtml(l.description)}</div>` : "";
  const posted = l.posted_at ? new Date(l.posted_at).toLocaleDateString() : "";
  const isSaved = savedUrls.has(l.url);
  const isFresh = freshUrls.has(l.url);
  return `
    <article class="card ${isFresh ? "fresh" : ""}">
      ${img}
      ${isFresh ? '<span class="fresh-badge">NEW</span>' : ""}
      <button class="save-btn ${isSaved ? "saved" : ""}" data-url="${escapeAttr(
    l.url
  )}" title="Save listing">${isSaved ? "\u2665" : "\u2661"}</button>
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
