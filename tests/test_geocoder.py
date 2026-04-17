import unittest
from unittest.mock import MagicMock, patch

import app as app_module
from scrapers.geocoder import Geocoder


class GeocoderUnit(unittest.TestCase):
    def test_returns_none_for_empty_query(self):
        g = Geocoder()
        self.assertIsNone(g.lookup(""))
        self.assertIsNone(g.lookup("   "))

    def test_caches_results(self):
        g = Geocoder()
        with patch.object(g, "_fetch", return_value=(30.27, -97.74)) as fetch:
            self.assertEqual(g.lookup("Downtown", city_hint="Austin"), (30.27, -97.74))
            self.assertEqual(g.lookup("Downtown", city_hint="Austin"), (30.27, -97.74))
            self.assertEqual(fetch.call_count, 1)

    def test_appends_city_hint_only_when_missing(self):
        g = Geocoder()
        with patch.object(g, "_fetch", return_value=(0.0, 0.0)) as fetch:
            g.lookup("East Side", city_hint="Austin")
            g.lookup("West Side, Austin", city_hint="Austin")
            self.assertEqual(fetch.call_args_list[0][0][0], "East Side, Austin")
            self.assertEqual(fetch.call_args_list[1][0][0], "West Side, Austin")

    def test_fetch_handles_empty_response(self):
        g = Geocoder()
        # Set last_call to "now" so the rate-limit wait is ~0 instead of huge.
        import time as _t
        g._last_call = _t.time()
        fake = MagicMock(status_code=200)
        fake.json.return_value = []
        with patch("scrapers.geocoder.requests.get", return_value=fake):
            self.assertIsNone(g._fetch("nowhere"))


class GeocodeEndpoint(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_missing_q_returns_400(self):
        resp = self.client.get("/api/geocode")
        self.assertEqual(resp.status_code, 400)

    def test_returns_coords_when_found(self):
        with patch.object(app_module._geocoder, "lookup", return_value=(1.0, 2.0)):
            resp = self.client.get("/api/geocode?q=anywhere")
            data = resp.get_json()
            self.assertTrue(data["found"])
            self.assertEqual(data["lat"], 1.0)
            self.assertEqual(data["lng"], 2.0)

    def test_returns_not_found(self):
        with patch.object(app_module._geocoder, "lookup", return_value=None):
            resp = self.client.get("/api/geocode?q=nowhere")
            data = resp.get_json()
            self.assertFalse(data["found"])


if __name__ == "__main__":
    unittest.main()
