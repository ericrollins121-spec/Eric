const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const sourcesEl = document.getElementById("sources");
const resultsEl = document.getElementById("results");
const mapEl = document.getElementById("map");
const button = form.querySelector("button[type=submit]");
const savedToggle = document.getElementById("saved-toggle");
const rssLink = document.getElementById("rss-link");
const viewBtns = document.querySelectorAll(".view-btn");

const SAVED_KEY = "rental-search:saved";
const SEEN_KEY = "rental-search:seen";
const GEO_KEY = "rental-search:geo";

let savedUrls = new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || "[]"));
let seenUrls = new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]"));
let geoCache = JSON.parse(localStorage.getItem(GEO_KEY) || "{}");
let showSavedOnly = false;
let lastListings = [];
let freshUrls = new Set();
let view = "list";
let map = null;
let markerLayer = null;
let geocodeJob = 0;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  await runSearch();
});

savedToggle.addEventListener("click", () => {
  showSavedOnly = !showSavedOnly;
  savedToggle.classList.toggle("active", showSavedOnly);
  render();
});

viewBtns.forEach((btn) =>
  btn.addEventListener("click", () => {
    view = btn.dataset.view;
    viewBtns.forEach((b) => b.classList.toggle("active", b === btn));
    render();
  })
);

resultsEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".save-btn");
  if (!btn) return;
  const url = btn.dataset.url;
  if (savedUrls.has(url)) savedUrls.delete(url);
  else savedUrls.add(url);
  localStorage.setItem(SAVED_KEY, JSON.stringify([...savedUrls]));
  btn.classList.toggle("saved");
  btn.textContent = savedUrls.has(url) ? "\u2665" : "\u2661";
  if (showSavedOnly) render();
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

    render();
    const freshNote = freshUrls.size ? ` \u00b7 ${freshUrls.size} new` : "";
    statusEl.textContent = `${json.count} listings in ${json.city}${freshNote}`;
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    button.disabled = false;
  }
}

function render() {
  if (view === "map") {
    resultsEl.hidden = true;
    mapEl.hidden = false;
    renderMap(currentFiltered());
  } else {
    mapEl.hidden = true;
    resultsEl.hidden = false;
    renderResults(currentFiltered());
  }
}

function currentFiltered() {
  return showSavedOnly
    ? lastListings.filter((l) => savedUrls.has(l.url))
    : lastListings;
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
  if (!listings.length) {
    resultsEl.innerHTML = `<p style="color:var(--muted);padding:0 0;">${
      showSavedOnly ? "No saved listings yet." : "No listings found. Try widening your filters."
    }</p>`;
    return;
  }
  resultsEl.innerHTML = listings.map(card).join("");
}

function ensureMap() {
  if (map) return map;
  map = L.map(mapEl).setView([30.2672, -97.7431], 11); // Austin default
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  return map;
}

async function renderMap(listings) {
  const m = ensureMap();
  setTimeout(() => m.invalidateSize(), 50);
  if (markerLayer) m.removeLayer(markerLayer);
  markerLayer = L.layerGroup().addTo(m);

  const withCoords = [];
  const job = ++geocodeJob;
  const city = (new FormData(form)).get("city") || "";

  // Plot already-cached locations immediately.
  const pending = [];
  for (const l of listings) {
    if (!l.location) continue;
    const key = l.location.toLowerCase();
    const cached = geoCache[key];
    if (cached) {
      withCoords.push({ ...l, lat: cached[0], lng: cached[1] });
    } else {
      pending.push(l);
    }
  }
  drawMarkers(withCoords);
  fitBounds(withCoords);
  statusEl.textContent = `Map: ${withCoords.length} pinned, ${pending.length} resolving...`;

  // Resolve the rest serially (server rate-limits to 1 req/s anyway).
  let processed = 0;
  for (const l of pending) {
    if (job !== geocodeJob) return; // search changed; bail
    const key = l.location.toLowerCase();
    try {
      const url = `/api/geocode?q=${encodeURIComponent(l.location)}&city=${encodeURIComponent(
        city
      )}`;
      const resp = await fetch(url);
      const data = await resp.json();
      if (data.found) {
        geoCache[key] = [data.lat, data.lng];
        localStorage.setItem(GEO_KEY, JSON.stringify(geoCache));
        const enriched = { ...l, lat: data.lat, lng: data.lng };
        withCoords.push(enriched);
        drawMarker(enriched);
      }
    } catch (e) {
      // skip and keep going
    }
    processed++;
    statusEl.textContent = `Map: ${withCoords.length} pinned \u00b7 ${
      pending.length - processed
    } resolving...`;
  }
  statusEl.textContent = `Map: ${withCoords.length} pinned`;
  fitBounds(withCoords);
}

function drawMarkers(items) {
  for (const l of items) drawMarker(l);
}

function drawMarker(l) {
  const popup = `
    <a href="${escapeAttr(l.url)}" target="_blank" rel="noopener">${escapeHtml(
    l.title || "Listing"
  )}</a>
    <div class="price">${l.price ? "$" + l.price.toLocaleString() : "\u2014"}${
    l.bedrooms != null ? " \u00b7 " + l.bedrooms + " bd" : ""
  }</div>
    ${l.location ? `<div>${escapeHtml(l.location)}</div>` : ""}
    <div class="src">${escapeHtml(l.source)}</div>
  `;
  L.marker([l.lat, l.lng]).addTo(markerLayer).bindPopup(popup);
}

function fitBounds(items) {
  if (!items.length || !map) return;
  const bounds = L.latLngBounds(items.map((l) => [l.lat, l.lng]));
  map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
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
