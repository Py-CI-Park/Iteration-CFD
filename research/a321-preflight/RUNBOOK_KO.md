# CPU 재실행 안내

작업 루트는 `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight`다. 모든 명령은 이 루트에서 실행한다. 연구용 Blender는 `D:\Chanil_Park\Project\Programming\Aircraft-Workbench\.workstation\tools\blender-5.2.2-portable\blender.exe`다.

**원본 대신 `artifacts/input/A321_G1B_FROZEN.blend`만 연다. 기존 trial 폴더를 덮어쓰지 말고 새 개정 폴더를 사용한다. 실행 전후 원본 SHA를 확인한다.** 아래 명령의 `B`는 Blender 절대경로, `R`은 `research/a321-preflight`의 절대경로로 대체한다. PowerShell에서는 `& $B ...`처럼 실행한다.

```powershell
$B = 'D:\Chanil_Park\Project\Programming\Aircraft-Workbench\.workstation\tools\blender-5.2.2-portable\blender.exe'
$R = 'D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight\research\a321-preflight'
& $B --background --factory-startup --disable-autoexec --threads 4 "$R\artifacts\input\A321_G1B_FROZEN.blend" --python-exit-code 7 --python "$R\inventory.py" -- "$R\evidence\native-inventory-rerun.json"

# 후속 시험은 trial-v040-rerun 같은 새 폴더를 사용한다.
& $B --background --factory-startup --disable-autoexec --threads 8 "$R\artifacts\input\A321_G1B_FROZEN.blend" --python-exit-code 7 --python "$R\prepare_surface.py" -- "$R\artifacts\trial-v040-rerun" 0.04

python -B "$R\verify_stl.py" "$R\artifacts\trial-v040-rerun\candidate.stl" "$R\evidence\stl-v040-rerun.json"

& $B --background --factory-startup --disable-autoexec --threads 4 "$R\artifacts\input\A321_G1B_FROZEN.blend" --python-exit-code 7 --python "$R\extract_wing.py" -- "$R\artifacts\wing-subsystem-rerun"
& $B --background --factory-startup --disable-autoexec --threads 4 "$R\artifacts\wing-subsystem-rerun\wing-fixed-box.blend" --python-exit-code 7 --python "$R\reopen_candidate.py" -- "$R\artifacts\wing-subsystem-rerun"
python -B "$R\verify_stl.py" "$R\artifacts\wing-subsystem-rerun\wing-fixed-box.stl" "$R\evidence\wing-rerun.json"

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -B -m pytest "$R\test_surface_metrics.py" "$R\test_custody.py" --noconftest -p no:cacheprovider -q
ruff check $R
python -B "$R\plot_sections.py" $R
python -B "$R\build_report.py"
```

Blender에 포함된 Python/numpy로 bpy 어댑터를 실행했다. 독립 리더는 시스템 Python 3.13/numpy/scipy, 도표는 matplotlib Agg CPU 백엔드다. 환경이 다르면 PEP 723 의존성을 `uv run`으로 준비한다. 테스트는 정확 사면체·구멍·뒤집힌 면·중복 면·비유한 좌표 거부 5개 기하 불변량을 검사한다. A321 전체 물리 검증 시험이 아니다. 비유한 좌표 시험은 최초 1 failed/4 passed를 확인한 뒤 최소 검사를 추가해 5 passed로 전환했다.

출력 보호 회귀 4개를 더해 최종 9개가 통과했다. 출력 경로는 evidence/artifacts 안의 새 경로만 허용하며 동결 input과 기존 파일을 거부한다. `make_manifest.py`, `build_report.py`, `plot_sections.py`는 각각 자신의 고정된 연구용 파생 기록만 갱신한다. 원본 모델 경로를 받지 않는다.

`browser-sources.mjs`는 Ego Lite task space를 만들고 NASA 6개 URL을 읽는다. `browser-nasa-followup.mjs`는 **당시 spaceId=7에 의존하는 실행 기록**이다. 재사용 시 새 작업의 반환 ID로 조정한다. `nasa-process.json`은 잘못된 URL의 404 영수증이므로 내용 근거에서 제외한다.

STL 재열기 비교는 삼각형·폐합·면적·체적·bounds와 SHA를 확인한다. 닫힌 표면 판정은 자기교차 검사를 대신하지 않는다. `source_exact_welded`의 정점 수와 STL 정점 수는 unused vertices 차이가 날 수 있어 정점 수만 동일성 기준으로 쓰지 않는다.

이번 연구는 단계 5에서 멈춘다. `ofgpu-probe`, `ofgpu-validate`, `ofgpu-lowmach`, `cargo test`의 GPU 테스트, CUDA context 생성, 체적 메셔, Blender 렌더는 실행하지 않는다.
