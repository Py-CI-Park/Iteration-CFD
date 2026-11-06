#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["markdown"]
# ///
# How to run: uv run build_report.py; static local research report.
"""Render the overview and the preserved detailed study without external scripts."""

from __future__ import annotations

from pathlib import Path

import markdown


def render(root: Path) -> str:
    """Render the overview and unchanged detailed study in one navigable document."""
    overview = (root / "PROGRESS_KO.md").read_text(encoding="utf8")
    archive = (root / "README_KO.md").read_text(encoding="utf8")
    extensions = ["tables", "fenced_code", "attr_list"]
    body = markdown.markdown(overview, extensions=extensions)
    detail = markdown.markdown("#" + archive, extensions=extensions)
    return (
        '<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>A321 공력 해석 준비 · R3 · GPU 보류</title>"
        '<link rel="stylesheet" href="report.css"></head><body>'
        '<nav aria-label="보고서 목차"><a href="#progress">진행률</a>'
        '<a href="#gallery">Studio 화면</a><a href="#next">남은 단계</a>'
        '<a href="#history">이전 연구</a><a href="#upstream">상위 업데이트</a>'
        '<a href="#detail">상세 원문</a></nav>'
        f'<main>{body}<section class="archive" aria-labelledby="detail">'
        f"{detail}</section></main></body></html>\n"
    )


def main() -> None:
    """Generate the static report next to its source Markdown and evidence."""
    root = Path(__file__).resolve().parent
    (root / "report.html").write_text(render(root), encoding="utf8", newline="\n")
    print(root / "report.html")


if __name__ == "__main__":
    main()
