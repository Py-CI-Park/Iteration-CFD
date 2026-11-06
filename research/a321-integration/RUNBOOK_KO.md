# 실행·재개 안내

연구 루트: `D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration`.

1. `start-studio.ps1`은 연구 workspace를 web5183/API8807로 띄운다. demo/mock이므로 유료 LLM·실제 solver는 사용하지 않는다. 원 main의 npm 의존성 junction을 사용하는 로컬 설치이며 새 clone에서는 `gui`에서 의존성 설치 필요. 이미 포트가 사용 중이면 다른 프로세스를 죽이지 말고 실행 소유자를 확인한다.
2. Ego Lite에서 탐색기 `research/a321-shell/models/A321_AIRFRAME_SHELL_R2.stl` → R2, `research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl` → R3. geometry 탭은 실제 STL 경로다. geometry import 중 용접/삼각형 제외 경고를 확인한다.
3. `inspect_span.py`와 `visual_compare.py`는 CPU 진단 그림을 만든다. `reconstruct_r3.py`는 기존 output이 없을 때만 R2 링에서 R3를 만든다. 원본·R2를 수정하지 않는다.
4. Blender는 `.workstation/tools/blender-5.2.2-portable/blender.exe --background --factory-startup --disable-autoexec --threads 4 --python <blender_r3.py>`로 작성했다. 검토는 새 모델을 직접 열고, readback은 `reopen_r3.py`를 사용한다. 원본 경로로 저장하지 않는다.
5. `uv run layer_mesh.py`는 현재 hybrid-r5 생성 알고리즘이다. 매우 얇은 층을 만들므로 **해석용 승인 알고리즘이 아니며 연구 재현용**이다. output이 이미 있으면 실패한다. 역사 r1~r4 실패는 attempt ledger와 log로 확인한다.
6. `convert_fast.py` → polyMesh 5파일, `audit_polymesh.py` → streaming exact point readback·face-based cell/비직교/폐합, `quality_detail.py`, `layer_jacobian.py` → 층 포착·프리즘 Jacobian 실패. 기존 polyMesh를 덮어쓰지 않는다. 저장 파일을 지우지 말고 새 개정 폴더를 사용한다.
7. polyMesh 위치는 `artifacts/hybrid-r5/case/constant/polyMesh`. Studio dataset reader는 case 경로를 API로 열 수 있다. system/controlDict·물성·필드 등 실행 가능한 case 구성은 아직 없음. 따라서 UI 탐색기가 case 태그를 자동 부여하지 않을 수 있다.
8. `gpu_diagnostic.py`는 환경 `CUDA_VISIBLE_DEVICES=GPU-2147afeb-b9fc-c7f5-398b-d5d00a3a5a90`가 정확할 때만 제한 메모리 진단. 이번 사용자 GPU 테스트 승인 범위이며 본 항공기 solver는 실행하지 않는다. 최대 scratch1GiB, 검증64MiB, 메모리 해제. OOM/장치명 불일치/잔여여유<3GiB는 거부.

테스트:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
uv run --with numpy --with scipy --with trimesh --with manifold3d --with pytest python -B -m pytest research/a321-integration/test_span_repair.py research/a321-integration/test_conversion.py research/a321-integration/test_layers.py research/a321-shell/test_profiles.py research/a321-shell/test_topology.py research/a321-preflight/test_surface_metrics.py research/a321-preflight/test_custody.py --noconftest -p no:cacheprovider -q
ruff check research/a321-integration
```

artifact 의존 테스트는 현재 보존된 hybrid가 있어야 한다. 새 clone에는 대형 격자를 올리지 않았으므로 재생성 또는 SHA 검증한 artifact 복원이 필요하다. 순수 analytic 테스트와 artifact 테스트를 구분해 수행 결과에 기록한다. 전체 복원이 없는 clone에서 형상 모델 검토만 하려면 tracked `models/*.blend/.stl`을 연다.

출력은 고정 연구 폴더 안으로만 쓴다. `package_research.py`가 source SHA·model 왕복·모든 local artifact 크기/SHA를 기록한다. 로그에는 실패 시점 코드와 현재 수정 코드가 다를 수 있다. 덮어쓰지 않은 실패본과 현재 default r5를 혼동하지 않는다. commit/push는 사용자 연구 브랜치만, main 병합/태그/Release는 수행하지 않는다.
