import re
from typing import Iterable, List

from .base import Listing


def _norm_location(loc: str) -> str:
    if not loc:
        return ""
    s = loc.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def dedupe(listings: Iterable[Listing]) -> List[Listing]:
    """
    Merge near-duplicates that appear on multiple sources.

    A listing is considered a duplicate of another when they share the same
    price, bedroom count, and a normalized location string. The first one
    wins; later duplicates are dropped. We also dedupe exact URLs.
    """
    seen_urls = set()
    seen_keys = set()
    out: List[Listing] = []

    for l in listings:
        if l.url and l.url in seen_urls:
            continue
        key = None
        if l.price is not None and l.location:
            key = (l.price, l.bedrooms, _norm_location(l.location))
            if key in seen_keys:
                continue

        if l.url:
            seen_urls.add(l.url)
        if key:
            seen_keys.add(key)
        out.append(l)
    return out
