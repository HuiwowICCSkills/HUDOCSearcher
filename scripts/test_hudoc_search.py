"""Offline tests for HUDOCSearcher."""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import hudoc_adapter as adapter  # noqa: E402


class FakeHttp:
    def __init__(self, data):
        self.data = data
        self.evidence = []

    def json(self, url, params=None, headers=None):
        return self.data, {
            "source_url": url, "http_status": 200, "content_type": "application/json",
            "bytes": 100, "retrieved_at": "2026-11-09T00:00:00Z", "sha256": "0" * 64,
        }


def args(**kwargs):
    base = dict(limit=1, offset=0, cache=".cache", offline=False, cache_ttl=0, timeout=30)
    base.update(kwargs)
    return argparse.Namespace(**base)


class HudocTests(unittest.TestCase):
    def test_search_parses_columns(self):
        payload = {
            "resultcount": 1,
            "results": [{"columns": {
                "itemid": "001-140005",
                "docname": "CASE OF JONES v. THE UNITED KINGDOM",
                "appno": "34356/06",
                "doctype": "HEJUD",
                "judgementdate": "14/01/2014",
                "respondent": "GBR",
            }}],
        }
        out = adapter.search("state immunity", args(), FakeHttp(payload))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["results"][0]["item_id"], "001-140005")
        self.assertIn("001-140005", out["results"][0]["url"])


if __name__ == "__main__":
    unittest.main()
