#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown"]
# ///
# How to run: uv run build_report.py; local research report, no network resources.
"""Render the Korean evidence ledger as a local, browser-readable report."""

from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
body = markdown.markdown(
    (ROOT / "README_KO.md").read_text(encoding="utf8"),
    extensions=["tables", "fenced_code"],
)
style = "body{font:17px/1.7 system-ui,sans-serif;max-width:1150px;margin:45px auto;padding:0 25px;color:#dce6f2;background:#111923}h1,h2{color:#9de1ec}h2{margin-top:50px}a{color:#80c7ff}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #3a4a60;padding:8px;text-align:left}pre{overflow:auto;padding:18px;background:#202d3e}img{max-width:100%;background:white}code{overflow-wrap:anywhere}strong{color:#ffc979}"
(ROOT / "report.html").write_text(
    f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A321 R3 경계층 연구 — FIX_FIRST</title><style>{style}</style><body>{body}</body></html>',
    encoding="utf8",
)
print(ROOT / "report.html")
