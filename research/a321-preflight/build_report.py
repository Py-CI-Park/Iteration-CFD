#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown"]
# ///
# ─── How to run ───
# uv run build_report.py
# Original deterministic local report build; no renderer or GPU.
"""Generate the study HTML from the canonical Korean Markdown report."""
from pathlib import Path

import markdown


def main() -> None:
    """Rebuild only the fixed report.html beside this source file."""
    root = Path(__file__).resolve().parent
    body = markdown.markdown(
        (root / "RESEARCH_KO.md").read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code"],
    )
    css = """body{max-width:1120px;margin:40px auto;padding:0 24px;font:17px/1.8 system-ui,sans-serif;color:#172033;background:#f8fafc}
    h1,h2,h3{line-height:1.35}h2{border-bottom:2px solid #cbd5e1;padding-top:28px}
    table{border-collapse:collapse;width:100%;font-size:15px}td,th{border:1px solid #cbd5e1;padding:10px;text-align:left}
    th,pre{background:#e2e8f0}pre{padding:18px;overflow:auto}a{color:#0757b3}code{overflow-wrap:anywhere}img{max-width:100%}"""
    html = f"""<!doctype html><html lang="ko"><meta charset="utf-8">
    <title>A321 공력 연구 CPU 준비 결과</title><style>{css}</style><body>{body}
    <h2>실제 단면 비교</h2><img src="evidence/sections.svg" alt="실제 단면 비교"></body></html>"""
    (root / "report.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
