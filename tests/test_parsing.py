import unittest

from scrapers.apartments import ApartmentsScraper
from scrapers.base import Listing
from scrapers.craigslist import CraigslistScraper
from scrapers.dedupe import dedupe


class CraigslistParsing(unittest.TestCase):
    def test_price_extraction(self):
        self.assertEqual(CraigslistScraper._extract_price("$1,950 / 2br"), 1950)
        self.assertEqual(CraigslistScraper._extract_price("nothing", "price $800 here"), 800)
        self.assertIsNone(CraigslistScraper._extract_price("no price here"))

    def test_bedroom_extraction(self):
        self.assertEqual(CraigslistScraper._extract_bedrooms("$1500 / 2br - downtown"), 2.0)
        self.assertEqual(CraigslistScraper._extract_bedrooms("3 bedroom loft"), 3.0)
        self.assertIsNone(CraigslistScraper._extract_bedrooms("studio apartment"))

    def test_location_extraction(self):
        self.assertEqual(
            CraigslistScraper._extract_location("$1500 / 2br - (East Austin)"),
            "East Austin",
        )
        self.assertIsNone(CraigslistScraper._extract_location("$1500 / 2br"))

    def test_strip_meta(self):
        self.assertEqual(
            CraigslistScraper._strip_meta_from_title("$1500 / 2br - Sunny loft (Downtown)"),
            "Sunny loft",
        )


class ApartmentsParsing(unittest.TestCase):
    def test_price(self):
        self.assertEqual(ApartmentsScraper._extract_price("Starting at $1,299"), 1299)
        self.assertIsNone(ApartmentsScraper._extract_price(""))

    def test_bedrooms(self):
        self.assertEqual(ApartmentsScraper._extract_bedrooms("Studio"), 0)
        self.assertEqual(ApartmentsScraper._extract_bedrooms("1-3 Bed"), 1.0)
        self.assertIsNone(ApartmentsScraper._extract_bedrooms(""))


def _mk(source, url, price=None, location=None, bedrooms=None):
    return Listing(
        source=source,
        title=f"{source} listing",
        url=url,
        price=price,
        location=location,
        bedrooms=bedrooms,
        posted_at=None,
        image=None,
        description=None,
    )


class Dedupe(unittest.TestCase):
    def test_drops_exact_url(self):
        a = _mk("CL", "https://x/1", 1500, "Downtown", 2)
        b = _mk("Apt", "https://x/1", 1500, "Downtown", 2)
        self.assertEqual(len(dedupe([a, b])), 1)

    def test_drops_same_price_loc_beds(self):
        a = _mk("CL", "https://x/1", 1500, "East Austin", 2)
        b = _mk("Apt", "https://y/2", 1500, "east-austin", 2)
        self.assertEqual(len(dedupe([a, b])), 1)

    def test_keeps_distinct(self):
        a = _mk("CL", "https://x/1", 1500, "Downtown", 2)
        b = _mk("Apt", "https://y/2", 1800, "Downtown", 2)
        self.assertEqual(len(dedupe([a, b])), 2)

    def test_no_key_when_price_missing(self):
        a = _mk("CL", "https://x/1", None, "Downtown", 2)
        b = _mk("Apt", "https://y/2", None, "Downtown", 2)
        self.assertEqual(len(dedupe([a, b])), 2)


if __name__ == "__main__":
    unittest.main()
