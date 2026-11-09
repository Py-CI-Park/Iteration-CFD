#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: imported by assemble_map.py; local rational arithmetic audit.
from __future__ import annotations

from fractions import Fraction

import numpy as np
from numpy.typing import NDArray

Vector = tuple[Fraction, Fraction, Fraction]


def subtract(a: Vector, b: Vector) -> Vector:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vector, b: Vector) -> Fraction:
    return sum((a[i] * b[i] for i in range(3)), Fraction(0))


def cross(a: Vector, b: Vector) -> Vector:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def interpolate(a: Vector, b: Vector, t: Fraction) -> Vector:
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2]))


def contains(point: Vector, triangle: list[Vector], normal: Vector) -> bool:
    return all(dot(cross(subtract(triangle[(i + 1) % 3], triangle[i]), subtract(point, triangle[i])), normal) >= 0 for i in range(3))


def geometry(a: list[Vector], b: list[Vector]) -> list[Vector]:
    """Exact rational triangle intersection; inputs are exact binary STL floats."""
    na = cross(subtract(a[1], a[0]), subtract(a[2], a[0]))
    nb = cross(subtract(b[1], b[0]), subtract(b[2], b[0]))
    if na == (0, 0, 0) or nb == (0, 0, 0):
        return []
    if all(dot(subtract(p, b[0]), nb) == 0 for p in a):
        polygon = a[:]
        for i in range(3):
            edge = subtract(b[(i + 1) % 3], b[i])
            result = []
            for j in range(len(polygon)):
                p, q = polygon[j - 1], polygon[j]
                sp = dot(cross(edge, subtract(p, b[i])), nb)
                sq = dot(cross(edge, subtract(q, b[i])), nb)
                if (sp >= 0) != (sq >= 0):
                    result.append(interpolate(p, q, sp / (sp - sq)))
                if sq >= 0:
                    result.append(q)
            polygon = result
        return polygon
    points = []
    for first, second, normal in ((a, b, nb), (b, a, na)):
        for i in range(3):
            p, q = first[i], first[(i + 1) % 3]
            dp, dq = dot(subtract(p, second[0]), normal), dot(subtract(q, second[0]), normal)
            if dp == 0 and contains(p, second, normal):
                points.append(p)
            if dp * dq < 0:
                hit = interpolate(p, q, dp / (dp - dq))
                if contains(hit, second, normal):
                    points.append(hit)
    return points


def audit_contact(a: NDArray[np.float64], b: NDArray[np.float64]) -> tuple[bool, list[list[float]]]:
    """Return whether an intersection extends beyond its shared vertex/edge."""
    first = [(Fraction(float(p[0])), Fraction(float(p[1])), Fraction(float(p[2]))) for p in a]
    second = [(Fraction(float(p[0])), Fraction(float(p[1])), Fraction(float(p[2]))) for p in b]
    shared = list(set(first) & set(second))
    points = geometry(first, second)
    beyond = False
    for point in points:
        if point in shared:
            continue
        if len(shared) == 2:
            direction, offset = subtract(shared[1], shared[0]), subtract(point, shared[0])
            if cross(direction, offset) == (0, 0, 0) and 0 <= dot(direction, offset) <= dot(direction, direction):
                continue
        beyond = True
    unique = sorted(set(points))
    return beyond, [[float(value) for value in point] for point in unique]
