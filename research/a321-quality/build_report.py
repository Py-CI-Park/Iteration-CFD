#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["markdown"]
# ///
# How to run: uv run build_report.py; static local research report.
"""Render the current Korean findings without external scripts or generated flow imagery."""

from __future__ import annotations

from pathlib import Path

import markdown


def main() -> None:
    """Generate a readable report using only measured local evidence."""
    root = Path(__file__).resolve().parent
    body = markdown.markdown(
        (root / "README_KO.md").read_text(encoding="utf8"),
        extensions=["tables", "fenced_code"],
    )
    style = "body{font:17px/1.7 system-ui,sans-serif;max-width:1150px;margin:45px auto;padding:0 24px;background:#111923;color:#dce6f2}h1,h2{color:#9de1ec}h2{margin-top:45px}a{color:#80c7ff}table{width:100%;border-collapse:collapse;font-size:14px}th,td{border:1px solid #3a4a60;padding:8px;text-align:left}pre{overflow:auto;background:#202d3e;padding:16px}img{max-width:100%;background:white}code{overflow-wrap:anywhere}strong{color:#ffc979}"
    (root / "report.html").write_text(
        f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A321 계산 격자 — 수치 PASS · GPU HOLD</title><style>{style}</style><body>{body}</body></html>',
        encoding="utf8",
    )
    print(root / "report.html")


if __name__ == "__main__":
    main()
