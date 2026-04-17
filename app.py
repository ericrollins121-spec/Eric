import os
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

from flask import Flask, Response, jsonify, render_template, request

from scrapers import (
    ApartmentsScraper,
    CraigslistScraper,
    FacebookMarketplaceScraper,
    Listing,
    TTLCache,
    ZumperScraper,
    dedupe,
)

app = Flask(__name__)

SCRAPERS = [
    CraigslistScraper(),
    ApartmentsScraper(),
    ZumperScraper(),
    FacebookMarketplaceScraper(),
]
DEFAULT_CITY = os.environ.get("RENTAL_DEFAULT_CITY", "austin")
CACHE_TTL = int(os.environ.get("RENTAL_CACHE_TTL", "300"))

_cache = TTLCache(ttl_seconds=CACHE_TTL)

SORTS = {
    "price_asc": lambda l: (l.price is None, l.price or 0),
    "price_desc": lambda l: (l.price is None, -(l.price or 0)),
    "beds_desc": lambda l: (l.bedrooms is None, -(l.bedrooms or 0)),
    "newest": lambda l: (l.posted_at is None, l.posted_at or ""),
}


def _parse_int(val):
    if val in (None, ""):
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _params_from_request() -> Tuple[str, str, dict]:
    city = (request.args.get("city") or DEFAULT_CITY).strip().lower()
    sort = request.args.get("sort", "price_asc")
    if sort not in SORTS:
        sort = "price_asc"
    params = {
        "city": city,
        "min_price": _parse_int(request.args.get("min_price")),
        "max_price": _parse_int(request.args.get("max_price")),
        "min_bedrooms": _parse_int(request.args.get("min_bedrooms")),
        "query": (request.args.get("query") or "").strip() or None,
        "limit": 50,
    }
    return city, sort, params


def _run_scraper(scraper, params):
    key = (scraper.name, tuple(sorted(params.items())))
    return _cache.get_or_set(key, lambda: scraper.search(**params) or [])


def _aggregate(params: dict, sort: str):
    results: List[Listing] = []
    sources_status = []

    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as pool:
        futures = {pool.submit(_run_scraper, s, params): s for s in SCRAPERS}
        for fut, scraper in futures.items():
            try:
                items = fut.result(timeout=25) or []
                results.extend(items)
                sources_status.append({"source": scraper.name, "count": len(items), "ok": True})
            except Exception as e:
                sources_status.append(
                    {"source": scraper.name, "count": 0, "ok": False, "error": str(e)}
                )

    before = len(results)
    results = dedupe(results)
    deduped = before - len(results)
    results.sort(key=SORTS[sort])
    return results, sources_status, deduped


@app.route("/")
def index():
    return render_template("index.html", default_city=DEFAULT_CITY)


@app.route("/api/search")
def search():
    city, sort, params = _params_from_request()
    results, sources_status, deduped = _aggregate(params, sort)
    return jsonify(
        {
            "city": city,
            "sort": sort,
            "sources": sources_status,
            "count": len(results),
            "deduped": deduped,
            "results": [l.to_dict() for l in results],
        }
    )


@app.route("/feed.rss")
def feed():
    """RSS 2.0 feed of the same search — drop it into a feed reader to get
    notified when new listings match your query."""
    city, sort, params = _params_from_request()
    results, _, _ = _aggregate(params, sort)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = f"Rental Search — {city}"
    ET.SubElement(channel, "link").text = request.url_root
    ET.SubElement(channel, "description").text = (
        f"Rental listings aggregated from {', '.join(s.name for s in SCRAPERS)}."
    )

    for l in results:
        item = ET.SubElement(channel, "item")
        price = f"${l.price:,}" if l.price else ""
        ET.SubElement(item, "title").text = f"{price} {l.title}".strip()
        if l.url:
            ET.SubElement(item, "link").text = l.url
            ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = l.url
        desc_parts = []
        if l.bedrooms is not None:
            desc_parts.append(f"{l.bedrooms} bd")
        if l.location:
            desc_parts.append(l.location)
        if l.description:
            desc_parts.append(l.description)
        ET.SubElement(item, "description").text = " · ".join(desc_parts)
        ET.SubElement(item, "category").text = l.source
        if l.posted_at:
            ET.SubElement(item, "pubDate").text = l.posted_at

    xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="utf-8")
    return Response(xml, mimetype="application/rss+xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
