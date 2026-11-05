#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown"]
# ///
# How to run: uv run build_report.py; fixed local HTML target only.
"""Create a Korean report without runtime package/CDN dependencies."""

from pathlib import Path

import markdown


def main() -> None:
    """Build readable HTML with links to generated derivative models and evidence."""
    root = Path(__file__).resolve().parent
    body = markdown.markdown(
        (root / "README_KO.md").read_text(encoding="utf8"),
        extensions=["tables", "fenced_code"],
    )
    css = "body{font:17px/1.8 system-ui,sans-serif;max-width:1160px;margin:36px auto;padding:0 22px;color:#14233b;background:#f7fafc}h1,h2{line-height:1.4}h2{border-bottom:2px solid #cbd5e1;padding-top:26px}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid #bcc9d8;padding:9px;text-align:left}th{background:#e4edf5}img{max-width:100%}code{overflow-wrap:anywhere}a{color:#0757b3}pre{overflow:auto}"
    links = '<p><a href="models/A321_AIRFRAME_SHELL_R2.blend">Blender 모델</a> · <a href="models/A321_AIRFRAME_SHELL_R2.stl">STL</a> · <a href="evidence/shell-audit-r2.json">형상 검사</a> · <a href="evidence/cpu-mesh-readback.json">CPU 격자 검사</a></p>'
    (root / "report.html").write_text(
        f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>A321 공력 전용 외피 R2</title><style>{css}</style><body>{links}{body}</body></html>',
        encoding="utf8",
    )


if __name__ == "__main__":
    main()
