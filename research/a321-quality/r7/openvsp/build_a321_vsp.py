# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Build the independent OpenVSP 3.56.0 A321 model (fuselage, wing, horizontal, vertical) and export CompGeom STL.

OpenVSP is NOSA 1.3 and is used here as a separate program through its Python API (venv interpreter).
No GUI executable and no VSPAERO is started. Run (from the repository root, venv interpreter, isolated mode):
  .worktmp/venvs/openvsp313/Scripts/python.exe -I research/a321-quality/r7/openvsp/build_a321_vsp.py --mode union --out-json X
  .worktmp/venvs/openvsp313/Scripts/python.exe -I research/a321-quality/r7/openvsp/build_a321_vsp.py --mode components --out-json X
Union mode: wing and horizontal are two-sided (XZ symmetry, no root cap), one CompGeom trimmed union is exported.
Components mode: every component alone, wing and horizontal as +y halves with a flat root cap, one CompGeom each."""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a321_params as P  # noqa: E402
import openvsp as vsp  # noqa: E402
import r3_sections as r3  # noqa: E402
import stl_tools  # noqa: E402

WORKTMP = HERE.parents[3] / ".worktmp" / "r7-openvsp"
AF_DIR = HERE / "af"
SET_EXPORT = vsp.SET_FIRST_USER + 6


def set_xsec(xs: str, k: int, name: str, value: float) -> None:
    vsp.SetParmVal(vsp.GetXSecParm(vsp.GetXSec(xs, k), name), float(value))


def write_airfoil(frame: dict, path: Path, label: str) -> None:
    """Selig-order .af file in chord lengths: upper TE -> LE -> lower TE."""
    up, lo = r3.side_order(frame["local"])
    pts = np.vstack([up[::-1], lo[1:]])
    path.write_text(label + "\n" + "".join(f"{x:.9f} {z:.9f}\n" for x, z in pts), encoding="ascii")


def build_lifting(name: str, part, rotate_vertical: bool, two_sided: bool, root_cap: bool, record: list) -> str:
    """One OpenVSP WING geometry whose sections are a greedy subset of the R3 stations."""
    frames = r3.frames_for(part)
    picks = r3.greedy_picks(frames, P.SECTION_TOL_M[0])
    n = len(picks)
    geom = vsp.AddGeom("WING")
    vsp.SetGeomName(geom, name)
    xs = vsp.GetXSecSurf(geom, 0)
    while vsp.GetNumXSec(xs) < n:
        vsp.InsertXSec(geom, vsp.GetNumXSec(xs) - 1, vsp.XS_FILE_AIRFOIL)
    AF_DIR.mkdir(exist_ok=True)
    for k, idx in enumerate(picks):
        af = AF_DIR / f"{name}_{k:02d}.af"
        write_airfoil(frames[idx], af, f"{name} R3 station {frames[idx]['station']:.6f}")
        vsp.ChangeXSecShape(xs, k, vsp.XS_FILE_AIRFOIL)
        vsp.ReadFileAirfoil(vsp.GetXSec(xs, k), str(af))
    # section planes stay perpendicular to the station axis, as in R3
    vsp.SetParmVal(geom, "RotateAirfoilMatchDideralFlag", "WingGeom", 0.0)
    vsp.SetParmVal(geom, "CorrectAirfoilthicknessFlag", "WingGeom", float(P.CORRECT_THICKNESS[0]))
    for k in range(1, n):
        vsp.SetDriverGroup(geom, k, vsp.SPAN_WSECT_DRIVER, vsp.ROOTC_WSECT_DRIVER, vsp.TIPC_WSECT_DRIVER)
    vsp.Update()
    st = [frames[i]["station"] for i in picks]
    lex = [float(frames[i]["le"][0]) for i in picks]
    lez = [0.0 if rotate_vertical else float(frames[i]["le"][1]) for i in picks]
    ch = [float(frames[i]["chord"]) for i in picks]
    for k in range(1, n):
        dx, dy, dz = lex[k] - lex[k - 1], st[k] - st[k - 1], lez[k] - lez[k - 1]
        span = math.hypot(dy, dz)
        values = {"Sweep_Location": 0.0, "Twist_Location": 0.0, "Twist": 0.0, "Dihedral": math.degrees(math.atan2(dz, dy)),
                  "Sweep": math.degrees(math.atan2(dx, span)), "Span": span, "Tip_Chord": ch[k]}
        if k == 1:
            values["Root_Chord"] = ch[0]
        for key, val in values.items():
            set_xsec(xs, k, key, val)
        for key in ("InLEStrength", "InTEStrength", "OutLEStrength", "OutTEStrength"):
            set_xsec(xs, k, key, 0.0)
    for key in ("InLEStrength", "InTEStrength", "OutLEStrength", "OutTEStrength"):
        set_xsec(xs, 0, key, 0.0)
    if rotate_vertical:
        vsp.SetParmVal(geom, "X_Rel_Location", "XForm", lex[0])
        vsp.SetParmVal(geom, "Z_Rel_Location", "XForm", st[0])
        vsp.SetParmVal(geom, "X_Rel_Rotation", "XForm", 90.0)
    else:
        vsp.SetParmVal(geom, "X_Rel_Location", "XForm", lex[0])
        vsp.SetParmVal(geom, "Z_Rel_Location", "XForm", lez[0])
    vsp.SetParmVal(geom, "Sym_Planar_Flag", "Sym", float(vsp.SYM_XZ) if two_sided else 0.0)
    vsp.SetParmVal(geom, "CapUMinOption", "EndCap", float(vsp.FLAT_END_CAP) if root_cap else float(vsp.NO_END_CAP))
    vsp.SetParmVal(geom, "CapUMaxOption", "EndCap", float(vsp.FLAT_END_CAP))
    tess = {"U": P.scaled(P.TESS[name]["U"]), "W": P.scaled(P.TESS[name]["W"])}
    vsp.SetParmVal(geom, "Tess_U", "Shape", float(tess["U"]))
    vsp.SetParmVal(geom, "Tess_W", "Shape", float(tess["W"]))
    vsp.Update()
    record.append({"name": name, "geom": geom, "n_sections": n, "r3_station_values": st, "le_x": lex, "le_z_or_y": lez, "chord": ch,
                   "two_sided": two_sided, "root_cap": root_cap, "tess": tess, "section_tol_m": P.SECTION_TOL_M[0],
                   "source": "R3_SECTIONS (research/a321-integration/evidence/reconstruction-r3.json via r6_ledger.load_parts)"})
    return geom


def build_fuselage(record: list) -> str:
    stations = P.fuselage_stations()
    geom = vsp.AddGeom("FUSELAGE")
    vsp.SetGeomName(geom, "fuselage")
    vsp.SetParmVal(geom, "Length", "Design", P.LENGTH[0])
    xs = vsp.GetXSecSurf(geom, 0)
    while vsp.GetNumXSec(xs) < len(stations):
        vsp.InsertXSec(geom, vsp.GetNumXSec(xs) - 2, vsp.XS_ELLIPSE)
    for k, st in enumerate(stations):
        kind = vsp.XS_POINT if st["kind"] == "point" else vsp.XS_ELLIPSE
        vsp.ChangeXSecShape(xs, k, kind)
    for k in range(len(stations) - 1, -1, -1):  # tail to nose keeps the x order valid while editing
        st = stations[k]
        set_xsec(xs, k, "XLocPercent", st["x"] / P.LENGTH[0])
        set_xsec(xs, k, "ZLocPercent", st["zc"] / P.LENGTH[0])
        if st["kind"] == "ellipse":
            set_xsec(xs, k, "Ellipse_Width", st["width"])
            set_xsec(xs, k, "Ellipse_Height", st["height"])
        set_xsec(xs, k, "SectTess_U", st["sect_tess_u"])
    vsp.Update()
    for k in range(1, len(stations) - 1):
        vsp.SetXSecContinuity(vsp.GetXSec(xs, k), 1)
    tess = {"U": P.scaled(P.TESS["fuselage"]["U"]), "W": P.scaled(P.TESS["fuselage"]["W"])}
    vsp.SetParmVal(geom, "Tess_U", "Shape", float(tess["U"]))
    vsp.SetParmVal(geom, "Tess_W", "Shape", float(tess["W"]))
    vsp.Update()
    record.append({"name": "fuselage", "geom": geom, "stations": stations, "tess": tess, "continuity": 1})
    return geom


def comp_geom(set_index: int, half: bool, txt_path: Path) -> tuple[str, float]:
    vsp.SetComputationFileName(vsp.COMP_GEOM_TXT_TYPE, str(txt_path))
    t0 = time.perf_counter()
    mesh_id = vsp.ComputeCompGeom(set_index, half, vsp.COMP_GEOM_TXT_TYPE)
    return mesh_id, time.perf_counter() - t0


def export_mesh(mesh_id: str, stl_path: Path) -> dict:
    """Export one mesh geometry as ASCII STL, convert to binary, drop the ASCII copy, return facts."""
    vsp.SetSetFlag(mesh_id, SET_EXPORT, True)
    ascii_path = stl_path.with_suffix(".ascii.stl")
    if ascii_path.exists():
        ascii_path.unlink()
    vsp.ExportFile(str(ascii_path), SET_EXPORT, vsp.EXPORT_STL)
    vsp.SetSetFlag(mesh_id, SET_EXPORT, False)
    tri = stl_tools.read_ascii_stl(ascii_path)
    if stl_path.exists():
        stl_path.unlink()
    stl_tools.write_binary_stl(stl_path, tri, f"openvsp3.56.0 compgeom {stl_path.stem}")
    ascii_path.unlink()
    return {"stl": str(stl_path), "triangles": int(len(tri)), "sha256": stl_tools.sha256_file(stl_path)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("union", "components"), required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--tess-scale", type=float, default=1.0, help="multiplies every tessellation count (default 1 = the production model)")
    ap.add_argument("--correct-thickness", type=int, choices=(0, 1), default=0, help="WingGeom CorrectAirfoilthicknessFlag (OpenVSP default 1; 0 used, see a321_params.CORRECT_THICKNESS)")
    ap.add_argument("--tag", default="", help="suffix for output names (sensitivity variants); empty for the production model")
    ap.add_argument("--half", action="store_true", help="union mode: also export the half (y >= 0) CompGeom mesh")
    args = ap.parse_args()
    P.TESS_SCALE[0] = args.tess_scale
    P.CORRECT_THICKNESS[0] = args.correct_thickness
    tag = args.tag
    WORKTMP.mkdir(parents=True, exist_ok=True)
    parts = r3.r6_ledger.load_parts()
    vsp.VSPRenew()
    print("OpenVSP", vsp.GetVSPVersion())
    record: list = []
    union = args.mode == "union"
    geoms = {"fuselage": build_fuselage(record),
             "wing": build_lifting("wing", parts["wing"], False, union, not union, record),
             "horizontal": build_lifting("horizontal", parts["horizontal"], False, union, not union, record),
             "vertical": build_lifting("vertical", parts["vertical"], True, False, True, record)}
    vsp_path = HERE / f"a321_openvsp_{args.mode}{tag}.vsp3"
    vsp.WriteVSPFile(str(vsp_path), vsp.SET_ALL)
    out: dict = {"mode": args.mode, "vsp3": str(vsp_path), "version": vsp.GetVSPVersion(), "geometry_records": record, "exports": {}}
    if union:
        mesh, secs = comp_geom(vsp.SET_ALL, False, WORKTMP / f"union{tag}_compgeom.txt")
        out["exports"]["union"] = {"compgeom_wall_s": secs, **export_mesh(mesh, WORKTMP / f"openvsp_union{tag}.stl")}
        vsp.DeleteGeom(mesh)
        if args.half:
            mesh, secs = comp_geom(vsp.SET_ALL, True, WORKTMP / f"union_half{tag}_compgeom.txt")
            out["exports"]["union_half"] = {"compgeom_wall_s": secs, **export_mesh(mesh, WORKTMP / f"openvsp_union_half{tag}.stl")}
            vsp.DeleteGeom(mesh)
    else:
        for i, (name, geom) in enumerate(geoms.items()):
            s = vsp.SET_FIRST_USER + i
            for other in geoms.values():
                vsp.SetSetFlag(other, s, other == geom)
            mesh, secs = comp_geom(s, False, WORKTMP / f"{name}{tag}_compgeom.txt")
            out["exports"][name] = {"compgeom_wall_s": secs, **export_mesh(mesh, WORKTMP / f"openvsp_{name}{tag}.stl")}
            vsp.DeleteGeom(mesh)
    args.out_json.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "stl"} for k, v in out["exports"].items()}, indent=1))


if __name__ == "__main__":
    main()
