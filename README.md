# Rental Search

A small Flask app that aggregates rental listings from multiple sources into one
search UI. Default area is **Austin, TX**, but you can change the city in the
search form.

## Sources

| Source               | Status  | Notes                                                                                                              |
| -------------------- | ------- | ------------------------------------------------------------------------------------------------------------------ |
| Craigslist           | Working | Uses the public RSS feed (`?format=rss`). No auth needed.                                                          |
| Apartments.com       | Working | Parses public result pages. Subject to anti-bot measures; cache results.                                           |
| Facebook Marketplace | Stub    | Requires login and scraping violates Meta's ToS. See `scrapers/facebook.py` for how to plug in a legitimate source. |

The Facebook Marketplace scraper is intentionally a documented stub. Rather than
silently failing or returning fake data, it logs a notice explaining why and
leaves room for you to plug in an authenticated session or licensed data feed.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://localhost:5000>.

Override the default city without editing code:

```bash
RENTAL_DEFAULT_CITY=seattle python app.py
```

## Project layout

```
app.py                 Flask app + /api/search endpoint
scrapers/
  base.py              Listing dataclass
  craigslist.py        RSS-based scraper
  apartments.py        HTML scraper for apartments.com
  facebook.py          Stub with plug-in instructions
templates/index.html
static/style.css
static/script.js
```

## Adding a new source

1. Create `scrapers/my_source.py` with a class exposing
   `.search(city, min_price, max_price, min_bedrooms, query, limit)` that
   returns a list of `Listing`.
2. Register it in `scrapers/__init__.py` and add it to `SCRAPERS` in `app.py`.
3. The `/api/search` endpoint fans out to every scraper in parallel, merges
   results, and sorts by price.

## Notes on scraping etiquette

- Respect `robots.txt` and each site's ToS in production.
- Cache aggressively; don't hammer upstream on every pageview.
- Set a descriptive `User-Agent` so site operators can reach you.
