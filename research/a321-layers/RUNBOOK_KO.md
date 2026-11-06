# 실행·증거 재현 절차

작업 checkout: `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight`.
브랜치: `codex/a321-aero-shell-20261105`.
현재 유효 후보: `research/a321-layers/artifacts/constrained-exact-02`.

## 보관과 입력

- 기존 R3 모델은 `research/a321-integration/models`에 버전 관리되어 있다. 원본 SHA는 README에 고정했다.
- 새 거대 `layers.npz`, `hybrid.npz`, `face-data.npz`, polyMesh와 실패 TetGen 원시 출력은 **이 컴퓨터의 artifacts에 보존되며 Git에서 제외**된다. 원격 브랜치에는 생성 코드·측정 JSON·해시·단면 그림·브라우저 증거·절차를 남긴다. 새 clone만으로 125만 셀 파일이 자동으로 생기지는 않는다.
- 기존 artifacts를 삭제하거나 덮어쓰지 않는다. 생성기는 고정 후보 이름이 이미 존재하면 실패한다. 반복 실험은 새 후보 이름과 별도 evidence 이름으로 진행한다. 새 clone에서 재현하면 Git에 있는 과거 evidence JSON과 새 측정 JSON 사이의 diff를 검토해야 한다. 생성 시각·소요 시간·환경에 따른 해시까지 항상 동일하다는 보장은 하지 않는다.
- [환경 원장](evidence/environment.json)은 실제 uv 스크립트 캐시의 패키지 metadata 목록이다. 의존성 헤더 수정 전후 환경도 포함하며 모든 과거 프로세스의 실행 시각을 복원한 자료는 아니다. 장기 재현에는 이 버전 목록으로 별도 환경을 고정한다.

## 새 clone에서 현재 유효 후보를 만드는 순서 — CPU만

Windows PowerShell, Python/uv 설치를 전제로 checkout 루트에서 실행한다. 아래 순서는 이미 생성된 로컬 artifacts에서는 다시 생성하지 말고 검사 단계만 실행한다. `build_layers.py`는 artifacts 상위 폴더도 생성한다.

```powershell
git status --short
git branch --show-current
uv run research/a321-layers/build_layers.py
uv run research/a321-layers/exterior_tets.py
uv run research/a321-layers/convert_oriented.py
uv run research/a321-layers/convert_oriented.py --verify-only
uv run research/a321-layers/audit_saved.py
uv run research/a321-layers/audit_incidence.py
uv run research/a321-layers/plot_section.py
```

각 명령의 종료 코드를 확인한다. build는 실패 시 `rejected-layers.npz`만 진단용으로 남기며 accepted `layers.npz`를 만들지 않는다. 다음 단계도 유한·양수 Jacobian을 다시 검사한다. exterior의 mesher/interface 거부는 실패 영수증을 남기고 종료 코드 2다. 이미 생성된 mesh는 덮어쓰지 않는다. `PASS_SCOPED_CPU_GATE`가 생기더라도 solver 자체 검사·전역 충돌·유효 경계층·물리적 validation이 끝났다는 뜻은 아니다.

실험용 `uv run research/a321-layers/exterior_tets.py --quality`는 **제외된 quality-exterior-03**을 재현한다. 현재는 정확 좌표 보존 검사에 실패한다. 실패 뒤 `convert_oriented.py --quality`, `audit_saved.py --quality`, `audit_incidence.py --quality`를 이어 실행해서는 안 된다. 각각 같은 quality-exterior-03 경로를 사용하며 누락된 입력을 자동으로 유효 후보로 대체하지 않는다.

`remesh_surface.py`는 별도의 isotropic-01 표면 근사 실험이다. 현재 후보의 벽면으로 사용하지 않는다. 첫 실험 constrained-exact-01은 제한된 Jacobian 표본 방식이었고, 재현 대상은 해석적 최소값을 사용하는 exact-02다.

## 회귀 검증

```powershell
uv run --with numpy --with scipy --with trimesh --with meshpy --with pytest python -m pytest research/a321-layers -q
uvx ruff check research/a321-layers
uvx ruff format --check research/a321-layers
```

테스트는 평균 법선의 함정, 프리즘 내부 극솟값, NaN/0/음수 거부, 잘못된 접합면·같은 winding 거부, 실제 warped-prism 폐합 회귀, 정점 순서 변경과 좌표 보존, 기존 artifact 덮어쓰기 금지 및 mesher 실패 종료 코드를 다룬다. 테스트 통과는 현재 실패한 mesh quality를 합격으로 바꾸지 않는다.

## Ego Lite Studio

서버 시작은 기존 [start-studio.ps1](../a321-integration/start-studio.ps1)을 따른다. main checkout의 기존 package/lock 변경은 건드리지 않는다. Studio는 이 연구 checkout을 workspace로 사용해야 한다.

1. Ego Lite에서 `http://127.0.0.1:5183/`를 연다.
2. 탐색기에서 `research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl`과 새 후보의 `outer.stl`을 연다.
3. mesh-only case 안에 `system/README_MESH_ONLY.txt`가 있어야 기존 UI가 case로 분류한다. 재현 시 그 디렉터리에 "Mesh only; FIX_FIRST; no solver settings" 설명 파일만 만든다. controlDict나 가짜 결과를 만들지 않는다.
4. 부모 폴더를 우클릭하여 새로 고침한 후 `case`를 우클릭 → **3D 뷰어로 열기**를 누른다. 1,251,054 cells 및 비정렬 mesh 경고를 확인한다. 기본 표면 화면은 외부 영역 박스를 보여 준다.
5. 수치 결과 필드와 시간이 비어 있는 상태가 정상이다. geometry 탭의 표시 삼각형 수는 원본 STL 수와 다를 수 있다. 오른쪽 AI와 GPU 데모 수치를 검증 자료로 쓰지 않는다.

`ego-01.mjs`~`ego-*.mjs`는 이번 세션의 조작 원장이다. 종료된 TaskSpace 6을 이후 자동 재사용하는 설치 스크립트가 아니다. 새 사용자 작업에는 새 TaskSpace를 만들고 현재 snapshot에서 selector를 확인한다.

## 중단 조건과 다음 실험

항공기 GPU solver는 현 상태에서 실행하지 않는다. 비직교 ≤70°, 상대 폐합 ≤1e-10 및 나머지 물리/기하 검사를 모두 충족한 뒤 실제 solver mesh acceptance를 수행한다. 새 표면 후보를 허용오차 없이 원 R3와 동일하다고 부르지 않는다. 다음 연구는 feature 보존 표면 분할과 경계층 패치 설계, 외부 사면체 grading을 함께 다룬다.
