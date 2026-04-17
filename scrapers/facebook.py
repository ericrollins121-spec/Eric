from typing import List, Optional

from .base import Listing


class FacebookMarketplaceScraper:
    """
    Facebook Marketplace listings are behind a login wall and scraping them
    without authorization violates Meta's Terms of Service. This class is
    intentionally a documented stub.

    To actually pull results here, plug one of these into `search()`:

      1. A logged-in session cookie (`c_user` + `xs`) from your own account
         and a GraphQL request to the internal Marketplace endpoint. This is
         brittle and against ToS; use at your own risk.

      2. A third-party aggregator with a licensed API (e.g. a rental data
         provider) that re-exposes Marketplace inventory.

      3. Meta's official Graph API — note this does NOT currently expose
         Marketplace rental listings.

    Until a legitimate source is wired in we return an empty list plus a
    one-time notice so the UI stays honest about coverage.
    """

    name = "Facebook Marketplace"

    def search(
        self,
        city: str = "austin",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Listing]:
        print(
            "[FacebookMarketplace] skipped: requires authenticated session; "
            "scraping violates Meta ToS. See scrapers/facebook.py for how to "
            "plug in a legitimate data source."
        )
        return []
