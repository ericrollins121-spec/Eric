import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import Listing


class ApartmentsScraper:
    """
    Scrapes public result pages from apartments.com.

    apartments.com serves rendered HTML for search results, unlike FB
    Marketplace which gates everything behind a login. Their robots.txt
    disallows some paths; respect it in production and cache aggressively.
    """

    name = "Apartments.com"
    UA = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    def search(
        self,
        city: str = "austin",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Listing]:
        slug = city.strip().lower().replace(" ", "-")
        parts = [f"https://www.apartments.com/{slug}"]
        if min_bedrooms:
            parts.append(f"{int(min_bedrooms)}-bedrooms")
        if min_price or max_price:
            lo = min_price or 0
            hi = max_price or 10000
            parts.append(f"{lo}-to-{hi}")
        url = "/".join(parts) + "/"

        try:
            resp = requests.get(url, headers={"User-Agent": self.UA}, timeout=15)
            if resp.status_code != 200:
                print(f"[Apartments] {resp.status_code} on {url}")
                return []
        except requests.RequestException as e:
            print(f"[Apartments] request failed: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        listings: List[Listing] = []

        for card in soup.select("article.placard, li.mortar-wrapper")[:limit]:
            link_el = card.select_one("a.property-link") or card.select_one("a[href*='/']")
            if not link_el:
                continue
            href = link_el.get("href", "")
            title_el = card.select_one(".property-title") or card.select_one(".property-name")
            price_el = card.select_one(".property-pricing") or card.select_one(".price-range")
            beds_el = card.select_one(".property-beds") or card.select_one(".bed-range")
            addr_el = card.select_one(".property-address")
            img_el = card.select_one("img")

            title = (title_el.get_text(strip=True) if title_el else "").strip()
            price_txt = price_el.get_text(" ", strip=True) if price_el else ""
            beds_txt = beds_el.get_text(" ", strip=True) if beds_el else ""
            addr = addr_el.get_text(" ", strip=True) if addr_el else None
            img = img_el.get("src") if img_el else None

            if not title and addr:
                title = addr

            listings.append(
                Listing(
                    source=self.name,
                    title=title or "Apartments.com listing",
                    url=href,
                    price=self._extract_price(price_txt),
                    location=addr,
                    bedrooms=self._extract_bedrooms(beds_txt),
                    posted_at=None,
                    image=img,
                    description=price_txt or None,
                )
            )
        return listings

    @staticmethod
    def _extract_price(text: str) -> Optional[int]:
        m = re.search(r"\$([\d,]+)", text or "")
        if not m:
            return None
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _extract_bedrooms(text: str) -> Optional[float]:
        if not text:
            return None
        if re.search(r"studio", text, re.I):
            return 0
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None
