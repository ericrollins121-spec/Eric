import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import Listing


class ZumperScraper:
    """
    Scrapes public search pages from zumper.com.

    Zumper renders a list of results server-side on `/for-rent/<city>-<state>`
    URLs. We hit the generic `<city>-apartments` slug which works for most
    major US cities without needing a state suffix.
    """

    name = "Zumper"
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
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
        url = f"https://www.zumper.com/apartments-for-rent/{slug}"
        params = {}
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price
        if min_bedrooms:
            params["min_bedrooms"] = min_bedrooms

        try:
            resp = requests.get(
                url, params=params, headers={"User-Agent": self.UA}, timeout=15
            )
            if resp.status_code != 200:
                print(f"[Zumper] {resp.status_code} on {resp.url}")
                return []
        except requests.RequestException as e:
            print(f"[Zumper] request failed: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        listings: List[Listing] = []

        cards = soup.select("a[href*='/listings/']") or soup.select(
            "div[data-testid='listing-card']"
        )
        for card in cards[:limit]:
            href = card.get("href") or ""
            if href.startswith("/"):
                href = "https://www.zumper.com" + href

            title = self._pick_text(card, ["h3", "h2", "[data-testid='listing-title']"])
            price_txt = self._pick_text(card, ["[data-testid='price']", ".price"])
            beds_txt = self._pick_text(card, ["[data-testid='bed']", ".beds"])
            loc = self._pick_text(card, ["[data-testid='address']", "address"])
            img_el = card.select_one("img")
            img = img_el.get("src") if img_el else None

            if not (price_txt or title):
                continue

            listings.append(
                Listing(
                    source=self.name,
                    title=title or loc or "Zumper listing",
                    url=href,
                    price=self._extract_price(price_txt),
                    location=loc,
                    bedrooms=self._extract_bedrooms(beds_txt),
                    posted_at=None,
                    image=img,
                    description=price_txt or None,
                )
            )
        return listings

    @staticmethod
    def _pick_text(card, selectors: List[str]) -> str:
        for sel in selectors:
            el = card.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if t:
                    return t
        return ""

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
