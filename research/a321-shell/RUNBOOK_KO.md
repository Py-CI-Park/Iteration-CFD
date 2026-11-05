# 재현 및 다음 단계

작업 폴더: `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight`.

```powershell
$B='D:\Chanil_Park\Project\Programming\Aircraft-Workbench\.workstation\tools\blender-5.2.2-portable\blender.exe'
$R='D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight\research\a321-shell'
# 새 checkout에서는 read-only native SHA가 같은지 먼저 확인하고, 입력 경로를 지정한다.
& $B --background --factory-startup --disable-autoexec --threads 6 'D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight\research\a321-preflight\artifacts\input\A321_G1B_FROZEN.blend' --python-exit-code 7 --python "$R\export_reference.py"
uv run "$R\reconstruct.py"
& $B --background --factory-startup --disable-autoexec --threads 4 --python "$R\blender_shell.py"
& $B --background --factory-startup --disable-autoexec --threads 4 "$R\artifacts\shell-r2\A321_AIRFRAME_SHELL_R2.blend" --python-exit-code 7 --python "$R\reopen_shell.py"
uv run "$R\audit_shell.py"
python -B "$R\visualize_shell.py"
python -B "$R\plan_case.py"
```

새 clone에는 원본을 올리지 않았으므로 모델만 검토할 때는 `models/*.blend/.stl`을 바로 연다. 재구성에는 SHA가 같은 로컬 원본 또는 동결 사본이 필요하다. 출력 trial 폴더가 있으면 생성기는 거부한다. R1은 실패/비교 이력이고 현재 재실행 코드는 R2를 만든다.

CPU 격자: `uv run meshpy_trial.py`는 수 분 이상 걸릴 수 있다. **`pq1.4a100YQ` 옵션과 실제 129,532개 기체 표면 삼각형은 바꾸지 않았다.** VTK 출력은 `mesh_readback.py`가 담당한다. `cpu_mesh.py`의 Gmsh 시도는 실패 경로 재현용이며 반복 분할 위험이 있어 자동 실행 체인에 넣지 않는다. 실패 로그는 artifact manifest에서 추적한다.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
uv run --with numpy --with scipy --with trimesh --with manifold3d --with pytest python -B -m pytest "$R\test_profiles.py" "$R\test_topology.py" --noconftest -p no:cacheprovider -q
ruff check $R
```

Blender GUI는 `& $B --disable-autoexec "$R\models\A321_AIRFRAME_SHELL_R2.blend"`로 연다. 실행 파일이 PATH에 없어도 절대경로로 가능하다. Ego Lite에서는 로컬 HTML 보고서를 열고 자료·그림을 검토한다. native 작성은 Blender CLI가 수행한다.

GPU 진입 전 필수 잔여: 독립 자기교차/holdout 단면, boundary-layer meshing, sliver·비직교·폐합 검사, ofgpu mesh gate, solver runtime 준비. 이 관문을 통과하기 전에는 생성된 CPU 격자로 CFD 결과를 만들지 않는다.
