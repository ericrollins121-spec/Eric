import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import app as app_module
from scrapers.base import Listing


def _fake_search(**_):
    return [
        Listing(
            source="Fake",
            title="Nice 2br loft",
            url="https://example.com/1",
            price=1500,
            location="Downtown",
            bedrooms=2,
            posted_at="Mon, 14 Apr 2026 10:00:00 GMT",
            image=None,
            description="loft with view",
        )
    ]


class AppEndpoints(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        # Force every scraper to our fake so tests are hermetic.
        self._patches = [
            patch.object(s, "search", side_effect=_fake_search)
            for s in app_module.SCRAPERS
        ]
        for p in self._patches:
            p.start()
        app_module._cache._store.clear()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_index_renders(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Rental Search", resp.data)

    def test_search_json_shape(self):
        resp = self.client.get("/api/search?city=austin&sort=price_desc")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["city"], "austin")
        self.assertEqual(data["sort"], "price_desc")
        self.assertIn("results", data)
        self.assertIn("sources", data)
        self.assertIn("deduped", data)
        self.assertGreaterEqual(data["count"], 1)

    def test_search_invalid_sort_falls_back(self):
        resp = self.client.get("/api/search?sort=nonsense")
        self.assertEqual(resp.get_json()["sort"], "price_asc")

    def test_search_dedupes_identical_listings(self):
        # All fake scrapers return the same URL; dedupe should collapse.
        resp = self.client.get("/api/search?city=austin&max_price=9999")
        data = resp.get_json()
        self.assertEqual(data["count"], 1)
        self.assertGreaterEqual(data["deduped"], 1)

    def test_rss_feed_parses(self):
        resp = self.client.get("/feed.rss?city=austin")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rss", resp.headers["Content-Type"])
        root = ET.fromstring(resp.data)
        self.assertEqual(root.tag, "rss")
        items = root.findall(".//item")
        self.assertGreaterEqual(len(items), 1)
        self.assertIn("example.com", items[0].find("link").text)


if __name__ == "__main__":
    unittest.main()
