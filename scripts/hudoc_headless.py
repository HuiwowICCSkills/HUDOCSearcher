#!/usr/bin/env python3
"""Minimal headless-Chrome bridge for HUDOC JSON and document pages."""

from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
import time
from pathlib import Path
from typing import Any

from skillkit import RetrievalError

HUDOC_ROOT = "https://hudoc.echr.coe.int/eng"


def find_chrome(explicit: str | None = None) -> str:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    for env in ("CHROME_PATH", "CHROME_BIN", "CF_BROWSER_PATH"):
        value = os.environ.get(env)
        if value:
            candidates.append(value)
    for root in (
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ):
        if root:
            candidates.extend(
                [
                    str(Path(root) / "Google/Chrome/Application/chrome.exe"),
                    str(Path(root) / "Microsoft/Edge/Application/msedge.exe"),
                ]
            )
    for command in ("chrome", "google-chrome", "chromium", "msedge", "microsoft-edge"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(resolved)
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RetrievalError(
        "Chrome/Chromium/Edge not found; set CHROME_PATH or install a browser"
    )


def _launch(chrome: str | None = None):
    try:
        from DrissionPage import Chromium, ChromiumOptions
    except ImportError as exc:
        raise RetrievalError(
            "DrissionPage is required for the HUDOC headless fallback; "
            "install requirements.txt"
        ) from exc
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    profile = tempfile.mkdtemp(prefix="hudoc-headless-")
    options = (
        ChromiumOptions(read_file=False)
        .set_local_port(port)
        .set_user_data_path(profile)
        .headless(True)
        .set_browser_path(find_chrome(chrome))
    )
    return Chromium(options)


def _wait_for_page(tab: Any, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            title = tab.title or ""
            text = tab.run_js("return document.body ? document.body.innerText.slice(0, 300) : ''") or ""
        except Exception:
            title, text = "", ""
        if "just a moment" not in title.lower() and "human verification" not in text.lower():
            if title or text:
                return
        time.sleep(1.0)


def fetch_json(api_url: str, timeout: int = 120, chrome: str | None = None) -> tuple[bytes, dict[str, Any]]:
    browser = _launch(chrome)
    try:
        tab = browser.latest_tab
        tab.get(HUDOC_ROOT)
        _wait_for_page(tab, min(20, timeout))
        script = (
            "return fetch(arguments[0], {headers: {"
            "'Accept': 'application/json, text/plain, */*', "
            "'X-Requested-With': 'XMLHttpRequest', "
            "'Referer': 'https://hudoc.echr.coe.int/eng'"
            "}}).then(async r => JSON.stringify({status: r.status, body: await r.text()}));"
        )
        raw = tab.run_js(script, api_url)
        if not raw:
            raise RetrievalError("HUDOC headless fetch returned no response")
        payload = json.loads(raw)
        status = int(payload.get("status", 0))
        body = str(payload.get("body", "")).encode("utf-8")
        if status != 200:
            raise RetrievalError(f"HUDOC headless API returned HTTP {status}")
        return body, {
            "source_url": api_url,
            "http_status": status,
            "content_type": "application/json",
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "transport": "headless-chrome-page-fetch",
            "browser_user_agent": tab.run_js("return navigator.userAgent"),
        }
    finally:
        try:
            browser.quit()
        except Exception:
            pass


def fetch_html(url: str, timeout: int = 120, chrome: str | None = None) -> tuple[str, dict[str, Any]]:
    browser = _launch(chrome)
    try:
        tab = browser.latest_tab
        tab.get(url)
        _wait_for_page(tab, min(30, timeout))
        html = tab.html or ""
        title = tab.title or ""
        if not html or len(html) < 200:
            raise RetrievalError("HUDOC headless page returned insufficient HTML")
        return html, {
            "source_url": url,
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "transport": "headless-chrome-rendered",
            "title": title,
            "browser_user_agent": tab.run_js("return navigator.userAgent"),
        }
    finally:
        try:
            browser.quit()
        except Exception:
            pass
