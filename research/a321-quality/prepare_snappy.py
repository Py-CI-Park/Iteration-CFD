#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2"]
# ///
# How to run: install uv, then uv run prepare_snappy.py; writes fresh CPU-only meshing inputs.
"""Create an external-tool hex-dominant control alongside the prism/tet research route."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Final

from custody import write_input_manifest

ROOT: Final = Path(__file__).resolve().parent


def foam(name: str, body: str) -> str:
    """Emit an ASCII dictionary from independently specified public input keywords."""
    return (
        f"FoamFile\n{{ version 2.0; format ascii; class dictionary; object {name}; }}\n"
        + body
        + "\n"
    )


def main() -> None:
    """Preserve the input bytes and create no initial fields or solver launch commands."""
    source = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
    ):
        raise RuntimeError("R3_SHA_MISMATCH")
    root = ROOT / "artifacts/snappy-01"
    (root / "constant/triSurface").mkdir(parents=True, exist_ok=False)
    (root / "system").mkdir()
    shutil.copyfile(source, root / "constant/triSurface/aircraft.stl")
    control = "application snappyHexMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1; writeControl timeStep; writeInterval 1; purgeWrite 0; writeFormat ascii; writePrecision 17; writeCompression off; timeFormat general; timePrecision 6; runTimeModifiable false;"
    (root / "system/controlDict").write_text(
        foam("controlDict", control), encoding="utf8", newline="\n"
    )
    vertices = "((-45 -65 -45) (135 -65 -45) (135 65 -45) (-45 65 -45) (-45 -65 55) (135 -65 55) (135 65 55) (-45 65 55))"
    boundary = "inlet {type patch; faces ((0 4 7 3));} outlet {type patch; faces ((1 2 6 5));} yMin {type patch; faces ((0 1 5 4));} yMax {type patch; faces ((3 7 6 2));} zMin {type patch; faces ((0 3 2 1));} zMax {type patch; faces ((4 5 6 7));}"
    block = f"convertToMeters 1; vertices {vertices}; blocks (hex (0 1 2 3 4 5 6 7) (60 44 34) simpleGrading (1 1 1)); edges (); boundary ({boundary}); mergePatchPairs ();"
    (root / "system/blockMeshDict").write_text(
        foam("blockMeshDict", block), encoding="utf8", newline="\n"
    )
    features = "aircraft.stl {extractionMethod extractFromSurface; extractFromSurfaceCoeffs { includedAngle 150; } writeObj no;}"
    (root / "system/surfaceFeatureExtractDict").write_text(
        foam("surfaceFeatureExtractDict", features), encoding="utf8", newline="\n"
    )
    text = """castellatedMesh true; snap true; addLayers true;
geometry { aircraft.stl {type triSurfaceMesh; name aircraft;} }
castellatedMeshControls {
 maxLocalCells 3000000; maxGlobalCells 6000000; minRefinementCells 0;
 maxLoadUnbalance 0.1; nCellsBetweenLevels 3;
 features ({file "aircraft.eMesh"; level 5;});
 refinementSurfaces {aircraft {level (4 5); patchInfo {type wall;} }}
 resolveFeatureAngle 30; refinementRegions {};
 locationInMesh (-40.1 0.1 0.1); allowFreeStandingZoneFaces true;
}
snapControls { nSmoothPatch 5; tolerance 2; nSolveIter 50; nRelaxIter 8;
 nFeatureSnapIter 15; implicitFeatureSnap false; explicitFeatureSnap true; multiRegionFeatureSnap false; }
addLayersControls {
 relativeSizes false; layers {"aircraft.*" {nSurfaceLayers 8;}}
 expansionRatio 1.2; firstLayerThickness 0.001; minThickness 0.004;
 nGrow 0; featureAngle 130; slipFeatureAngle 30; nRelaxIter 8;
 nSmoothSurfaceNormals 3; nSmoothNormals 5; nSmoothThickness 10;
 maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3;
 minMedialAxisAngle 90; nBufferCellsNoExtrude 1; nLayerIter 50; nRelaxedIter 50;
}
meshQualityControls {
 maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4;
 maxConcave 80; minVol 1e-14; minTetQuality 1e-15; minArea -1;
 minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.02;
 minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4; errorReduction 0.75;
 relaxed {maxNonOrtho 65;}
}
writeFlags (layerSets layerFields); mergeTolerance 1e-9;
"""
    (root / "system/snappyHexMeshDict").write_text(
        foam("snappyHexMeshDict", text), encoding="utf8", newline="\n"
    )
    (root / "system/fvSchemes").write_text(
        foam(
            "fvSchemes",
            "ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}",
        ),
        encoding="utf8",
        newline="\n",
    )
    (root / "system/fvSolution").write_text(
        foam("fvSolution", "solvers {}"), encoding="utf8", newline="\n"
    )
    (root / "system/decomposeParDict").write_text(
        foam(
            "decomposeParDict",
            "numberOfSubdomains 8; method hierarchical; hierarchicalCoeffs {n (2 2 2); delta 0.001; order xyz;}",
        ),
        encoding="utf8",
        newline="\n",
    )
    write_input_manifest(root)
    print(root)


if __name__ == "__main__":
    main()
