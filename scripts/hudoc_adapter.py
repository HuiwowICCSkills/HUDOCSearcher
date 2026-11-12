#!/usr/bin/env python3
"""European Court of Human Rights HUDOC adapter for HUDOCSearcher."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup
from skillkit import HTTP, RetrievalError, clean, result, snippet
from hudoc_headless import fetch_html, fetch_json

PROG = "hudoc_search.py"
DESCRIPTION = "Search the European Court of Human Rights HUDOC database."
CACHE_DEFAULT = ".hudoc-cache"
FETCH_TIMEOUT_DEFAULT = 300

API_URL = "https://hudoc.echr.coe.int/app/query/results"
ROOT_URL = "https://hudoc.echr.coe.int/eng"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/155.0.0.0 Safari/537.36"
)
SELECT_FIELDS = "itemid,docname,appno,doctype,judgementdate,respondent"


def _headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Referer": ROOT_URL,
        "X-Requested-With": "XMLHttpRequest",
    }


def make_http(args: argparse.Namespace) -> HTTP:
    return HTTP(
        args.cache,
        offline=args.offline,
        ttl=args.cache_ttl,
        timeout=args.timeout,
        user_agent=UA,
    )


def add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=10, help="1..50 (default 10)")
    parser.add_argument("--offset", type=int, default=0, help=">= 0 (default 0)")
    parser.add_argument(
        "--document-collection",
        action="append",
        default=[],
        help=(
            "HUDOC document collection, repeatable: GRANDCHAMBER, CHAMBER, "
            "COMMITTEE, JUDGMENTS, DECISIONS, COMMUNICATEDCASES, "
            "ADVISORYOPINIONS, REPORTS, RESOLUTIONS"
        ),
    )
    parser.add_argument("--respondent", help="Respondent State ISO3 code, e.g. TUR")
    parser.add_argument("--article", help="Convention article, e.g. 3 or 6-1")
    parser.add_argument("--importance", help="HUDOC importance level, e.g. 1, 2, 3 or KEY")
    parser.add_argument("--violation", help="Article number for a violation finding, e.g. 6")
    parser.add_argument("--nonviolation", help="Article number for a non-violation finding")
    parser.add_argument("--docname", help="Words in the document title")
    parser.add_argument("--appno", help="Exact application number, e.g. 34356/06")
    parser.add_argument("--doctype", help="HUDOC document type code, e.g. HEJUD or HEDEC")
    parser.add_argument("--date-from", dest="date_from", help="Judgment date lower bound YYYY-MM-DD")
    parser.add_argument("--date-to", dest="date_to", help="Judgment date upper bound YYYY-MM-DD")
    parser.add_argument("--sort", default="", help="HUDOC sort expression (default: relevance)")


def add_fetch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text-out", help="Write extracted page text here")
    parser.add_argument("--max-mb", type=int, default=50, help="Maximum response size in MiB")


def _escape(value: str) -> str:
    return str(value).replace('"', '\\"')


def _clause(field: str, value: str) -> str:
    return f'{field}:"{_escape(value)}"'


def build_query(text: str, args: argparse.Namespace | None = None) -> str:
    """Build a HUDOC query from free text plus the site's advanced fields.

    Field names were verified against HUDOC's own advanced-search controls
    (2026-11-12).  Values are quoted as phrases; multi-value document
    collections are OR-ed, and every other condition is AND-ed.
    """
    parts: list[str] = ["contentsitename:ECHR"]
    if text and text.strip():
        parts.append('"' + _escape(text.strip()) + '"')
    if args is not None:
        if getattr(args, "document_collection", None):
            collections = [
                _clause("documentcollectionid2", value)
                for value in args.document_collection
                if value
            ]
            if collections:
                parts.append("(" + " OR ".join(collections) + ")")
        for field, attr in (
            ("respondent", "respondent"),
            ("article", "article"),
            ("importance", "importance"),
            ("violation", "violation"),
            ("nonviolation", "nonviolation"),
            ("docname", "docname"),
            ("appno", "appno"),
            ("doctype", "doctype"),
        ):
            value = getattr(args, attr, None)
            if value:
                parts.append(_clause(field, value))
        date_from = getattr(args, "date_from", None)
        date_to = getattr(args, "date_to", None)
        if date_from or date_to:
            parts.append(
                "judgementdate:["
                + (date_from or "*")
                + " TO "
                + (date_to or "*")
                + "]"
            )
    return " AND ".join(parts)


def _rows_from_payload(data: dict[str, Any], meta: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    docs = data.get("results")
    if isinstance(docs, dict):
        docs = docs.get("docs")
    if not isinstance(docs, list):
        raise RetrievalError("HUDOC response schema not recognized; cannot infer zero results")
    rows: list[dict[str, Any]] = []
    for doc in docs:
        columns = doc.get("columns", doc)
        if isinstance(columns, list):
            columns = {item.get("name"): item.get("value") for item in columns}
        itemid = doc.get("itemid") or columns.get("itemid")
        if not itemid or not columns.get("docname"):
            raise RetrievalError("HUDOC record lacks itemid/docname")
        rows.append(
            result(
                columns.get("docname"),
                "https://hudoc.echr.coe.int/eng?i=" + quote(str(itemid)),
                "hudoc-api",
                "",
                fields=columns,
                item_id=str(itemid),
                appno=columns.get("appno"),
                document_type=columns.get("doctype"),
                date=columns.get("judgementdate"),
                respondent=columns.get("respondent"),
                access="search metadata; document text must be fetched separately",
                content_scope="HUDOC search metadata, not the judgment text",
            )
        )
    total = data.get("resultcount")
    return rows, int(total) if isinstance(total, int) else None


def search(query: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    if not 1 <= args.limit <= 50:
        raise ValueError("limit must be 1..50")
    if args.offset < 0:
        raise ValueError("offset must be >= 0")
    built = build_query(query, args)
    if not query.strip() and built == "contentsitename:ECHR":
        raise ValueError("A non-empty query or at least one advanced filter is required")
    params = {
        "query": built,
        "select": SELECT_FIELDS,
        "sort": getattr(args, "sort", ""),
        "start": args.offset,
        "length": args.limit,
    }
    fallback = False
    warnings: list[str] = []
    try:
        data, meta = http.json(API_URL, params, headers=_headers())
    except RetrievalError as exc:
        if args.offline:
            raise
        warnings.append("direct HUDOC API failed; using headless Chrome: " + str(exc))
        prepared = (
            API_URL
            + "?"
            + "&".join(
                [
                    "query=" + quote(built, safe=""),
                    "select=" + quote(SELECT_FIELDS, safe=","),
                    "sort=" + quote(getattr(args, "sort", ""), safe=""),
                    "start=" + str(args.offset),
                    "length=" + str(args.limit),
                ]
            )
        )
        body, meta = fetch_json(prepared, timeout=args.timeout)
        data = json.loads(body)
        fallback = True
    rows, total = _rows_from_payload(data, meta)
    return {
        "status": "ok" if rows or total == 0 else "no-results-in-queried-index",
        "query": query,
        "query_expression": built,
        "filters": {
            "document_collection": getattr(args, "document_collection", []),
            "respondent": getattr(args, "respondent", None),
            "article": getattr(args, "article", None),
            "importance": getattr(args, "importance", None),
            "violation": getattr(args, "violation", None),
            "nonviolation": getattr(args, "nonviolation", None),
            "docname": getattr(args, "docname", None),
            "appno": getattr(args, "appno", None),
            "doctype": getattr(args, "doctype", None),
            "date_from": getattr(args, "date_from", None),
            "date_to": getattr(args, "date_to", None),
        },
        "total": total,
        "results": rows,
        "pagination": {
            "offset": args.offset,
            "limit": args.limit,
            "next_offset": (
                args.offset + len(rows)
                if total is not None and rows and args.offset + len(rows) < total
                else None
            ),
        },
        "warnings": warnings,
        "transport": "headless-chrome-page-fetch" if fallback else "direct-http",
        "scope": (
            "HUDOC search metadata for the ECHR collection; advanced filters use "
            "the field syntax of the HUDOC search API"
        ),
        "evidence": http.evidence,
    }


def fetch(locator: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    parsed = urlparse(locator)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "hudoc.echr.coe.int":
        raise ValueError("fetch expects an https://hudoc.echr.coe.int/ URL")
    max_bytes = args.max_mb * 1024 * 1024
    body = b""
    meta: dict[str, Any] = {}
    try:
        body, meta = http.get(locator, headers={"User-Agent": UA})
    except RetrievalError as exc:
        if args.offline:
            raise
        html, meta = fetch_html(locator, timeout=args.timeout)
        body = html.encode("utf-8")
        meta["transport"] = "headless-chrome-rendered"
    if len(body) > max_bytes:
        raise RetrievalError(f"Response exceeds --max-mb ({args.max_mb} MiB)")
    soup = BeautifulSoup(body, "html.parser")
    title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
    if re.search(r"^(sign in|log in|access denied|just a moment)", title, re.I):
        raise RetrievalError("Login/access page, not document text")
    container = (
        soup.select_one("#content")
        or soup.select_one("main")
        or soup.select_one("article")
        or soup.body
        or soup
    )
    for node in container.select("script, style, nav, header, footer, input, select, button, textarea, noscript"):
        node.decompose()
    text = container.get_text("\n", strip=True)
    if len(text) < 100:
        raise RetrievalError("Insufficient HUDOC page text; page may be a shell or access page")
    links = []
    seen = set()
    for anchor in container.select("a[href]"):
        href = urljoin(meta.get("source_url", locator), anchor["href"])
        if href in seen:
            continue
        seen.add(href)
        links.append({"text": clean(anchor.get_text(" ", strip=True)), "url": href})
    if args.text_out:
        Path(args.text_out).write_text(text, encoding="utf-8")
    return {
        "status": "ok",
        "url": meta.get("source_url", locator),
        "title": title,
        "text": text,
        "text_characters": len(text),
        "document_links": links,
        "content_scope": "HUDOC rendered document page text; confirm the item ID and language",
        "text_out": str(Path(args.text_out).resolve()) if args.text_out else None,
        "sha256": meta.get("sha256"),
        "retrieved_at": meta.get("retrieved_at"),
        "transport": meta.get("transport", "direct-http"),
    }


def doctor(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        {"check": "python", "ok": True, "detail": "Python runtime available"},
        {"check": "requests", "ok": True, "detail": "requests importable"},
        {"check": "beautifulsoup4", "ok": True, "detail": "bs4 importable"},
    ]
    try:
        import DrissionPage  # noqa: F401

        checks.append({"check": "DrissionPage", "ok": True, "detail": "headless fallback importable"})
        headless_ok = True
    except Exception as exc:
        checks.append({"check": "DrissionPage", "ok": False, "detail": str(exc)})
        headless_ok = False
    if args.no_probe:
        return {"ok": headless_ok, "status": "ok (probes skipped)" if headless_ok else "error", "checks": checks}
    http = make_http(args)
    try:
        data, meta = http.json(
            API_URL,
            {
                "query": build_query("state immunity"),
                "select": "itemid,docname",
                "sort": "",
                "start": 0,
                "length": 1,
            },
            headers=_headers(),
        )
        checks.append(
            {
                "check": "HUDOC API",
                "ok": isinstance(data.get("results"), (list, dict)),
                "http_status": meta["http_status"],
                "bytes": meta["bytes"],
            }
        )
        ok = True
    except Exception as exc:
        checks.append(
            {
                "check": "HUDOC API",
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "headless_available": headless_ok,
            }
        )
        ok = headless_ok
    return {
        "ok": ok,
        "status": "ok" if ok else "error",
        "checks": checks,
        "catalog": {"select": SELECT_FIELDS, "root": ROOT_URL},
    }
