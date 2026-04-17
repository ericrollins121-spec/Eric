import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

from flask import Flask, jsonify, render_template, request

from scrapers import (
    ApartmentsScraper,
    CraigslistScraper,
    FacebookMarketplaceScraper,
    Listing,
)

app = Flask(__name__)

SCRAPERS = [CraigslistScraper(), ApartmentsScraper(), FacebookMarketplaceScraper()]
DEFAULT_CITY = os.environ.get("RENTAL_DEFAULT_CITY", "austin")


def _parse_int(val):
    if val in (None, ""):
        return None
    try:
        return int(val)
    except ValueError:
        return None


@app.route("/")
def index():
    return render_template("index.html", default_city=DEFAULT_CITY)


@app.route("/api/search")
def search():
    city = (request.args.get("city") or DEFAULT_CITY).strip().lower()
    params = {
        "city": city,
        "min_price": _parse_int(request.args.get("min_price")),
        "max_price": _parse_int(request.args.get("max_price")),
        "min_bedrooms": _parse_int(request.args.get("min_bedrooms")),
        "query": (request.args.get("query") or "").strip() or None,
        "limit": 50,
    }

    results: List[Listing] = []
    sources_status = []

    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as pool:
        futures = {pool.submit(s.search, **params): s for s in SCRAPERS}
        for fut, scraper in futures.items():
            try:
                items = fut.result(timeout=25) or []
                results.extend(items)
                sources_status.append({"source": scraper.name, "count": len(items), "ok": True})
            except Exception as e:
                sources_status.append(
                    {"source": scraper.name, "count": 0, "ok": False, "error": str(e)}
                )

    results.sort(key=lambda l: (l.price is None, l.price or 0))

    return jsonify(
        {
            "city": city,
            "sources": sources_status,
            "count": len(results),
            "results": [l.to_dict() for l in results],
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
