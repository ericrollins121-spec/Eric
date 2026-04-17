import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlencode

import requests

from .base import Listing


class CraigslistScraper:
    """
    Queries Craigslist's public RSS feed for apartment/rental listings.

    Craigslist exposes RSS via `?format=rss` on any search URL. No auth
    required. We keep requests infrequent and identify ourselves via UA.
    """

    name = "Craigslist"
    BASE = "https://{city}.craigslist.org/search/apa"
    UA = "RentalSearchApp/1.0 (+https://example.com)"

    # RSS 1.0 / RDF namespaces Craigslist actually emits.
    NS = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    def search(
        self,
        city: str = "austin",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Listing]:
        params = {"format": "rss"}
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if min_bedrooms is not None:
            params["min_bedrooms"] = min_bedrooms
        if query:
            params["query"] = query

        url = f"{self.BASE.format(city=city)}?{urlencode(params)}"
        try:
            resp = requests.get(url, headers={"User-Agent": self.UA}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[Craigslist] request failed: {e}")
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            print(f"[Craigslist] XML parse error: {e}")
            return []

        listings: List[Listing] = []
        items = root.findall("rss:item", self.NS)
        if not items:
            items = root.findall(".//item")  # fallback for RSS 2.0

        for item in items[:limit]:
            title = self._text(item, "rss:title") or self._text(item, "title")
            link = self._text(item, "rss:link") or self._text(item, "link")
            summary = self._text(item, "rss:description") or self._text(item, "description")
            posted = self._text(item, "dc:date")

            price = self._extract_price(title, summary)
            bedrooms = self._extract_bedrooms(title, summary)
            location = self._extract_location(title)

            listings.append(
                Listing(
                    source=self.name,
                    title=self._strip_meta_from_title(title),
                    url=link or "",
                    price=price,
                    location=location,
                    bedrooms=bedrooms,
                    posted_at=posted,
                    image=None,
                    description=self._clean_summary(summary),
                )
            )
        return listings

    def _text(self, item, tag: str) -> str:
        el = item.find(tag, self.NS)
        return (el.text or "").strip() if el is not None and el.text else ""

    @staticmethod
    def _extract_price(*texts: str) -> Optional[int]:
        for t in texts:
            m = re.search(r"\$([\d,]+)", t or "")
            if m:
                try:
                    return int(m.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_bedrooms(*texts: str) -> Optional[float]:
        for t in texts:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:br|bed|bedroom)s?", t or "", re.I)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_location(title: str) -> Optional[str]:
        m = re.search(r"\(([^)]+)\)\s*$", title or "")
        return m.group(1).strip() if m else None

    @staticmethod
    def _strip_meta_from_title(title: str) -> str:
        t = re.sub(r"\$[\d,]+\s*/\s*\d+br\s*-?\s*", "", title or "")
        t = re.sub(r"\s*\([^)]+\)\s*$", "", t)
        return t.strip()

    @staticmethod
    def _clean_summary(summary: str) -> str:
        text = re.sub(r"<[^>]+>", " ", summary or "")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:400]
