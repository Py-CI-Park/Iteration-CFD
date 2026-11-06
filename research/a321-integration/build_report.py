#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown"]
# ///
# How to run: uv run build_report.py
"""Build fixed Korean integration report without external assets."""

from pathlib import Path

import markdown


def main() -> None:
    """Render report HTML from canonical study Markdown."""
    root = Path(__file__).resolve().parent
    body = markdown.markdown(
        (root / "README_KO.md").read_text(encoding="utf8"),
        extensions=["tables", "fenced_code"],
    )
    css = "body{max-width:1160px;margin:36px auto;padding:0 24px;font:17px/1.8 system-ui,sans-serif;background:#f6f9fc;color:#17283f}h1,h2{line-height:1.35}h2{padding-top:25px;border-bottom:2px solid #c7d5e4}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid #c5d0df;padding:9px}th{background:#e4edf6}img{max-width:100%}code{overflow-wrap:anywhere}pre{overflow:auto}a{color:#075eb4}"
    links = '<p><a href="http://127.0.0.1:5183/">실행 중인 Studio</a> · <a href="models/A321_AIRFRAME_SHELL_R3.blend">R3 Blender</a> · <a href="models/A321_AIRFRAME_SHELL_R3.stl">R3 STL</a></p>'
    (root / "report.html").write_text(
        f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>A321 Studio·경계층·GPU 진단</title><style>{css}</style><body>{links}{body}</body></html>',
        encoding="utf8",
    )


if __name__ == "__main__":
    main()
