# 실행·검증·보관

브랜치 `codex/a321-aero-shell-20261105`, checkout `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight`.
시작 HEAD는 `c5295b03bb71d13a3435846df769fb942322043b`이다. 원본 모델과 이전 연구 디렉터리는 수정하지 않는다.

## 현재 로컬 결과 확인

선정한 제한적 CPU 수치 후보는 `research/a321-quality/artifacts/snappy-03`이다. 전체 engineering 상태는 `NOT_VALIDATED_GPU_HOLD`다.

- `constant/polyMesh`: 실제 직렬화된 격자.
- `calculation-wall-v5.stl`: 실제 CFD wall을 삼각 분할한 보기용/거리 측정용 파생 표면.
- `audited-geometry-v5.npz`: signed triangle 적분 기반 셀 중심·체적·비직교·폐합.
- `processor*/0/nSurfaceLayers`, `thickness`: mesher 진단 필드. 압력·속도 해석 결과가 아니다.
- `log.snappy`, `log.checkMesh-standard`, `log.checkMesh-extended`: 성공과 실패를 모두 유지한 원시 로그.

큰 mesh·processor 중간 데이터는 artifacts에서 로컬 보존하며 Git에 올리지 않는다. 원격에는 코드·숫자 영수증·전체 주요 로그·해시·도식·브라우저 증거를 올린다. 새 clone에는 대형 격자가 없으므로 아래 재현 단계가 필요하다.

## 새 checkout에서 재현 — CPU만

Windows Python 3.12 이상과 uv, WSL Ubuntu가 필요하다. 현재 사용한 외부 패키지는 Ubuntu `openfoam 1912.200626-2build3`다. 설치가 없으면 WSL에서 `sudo apt-get install --no-install-recommends openfoam`으로 설치할 수 있다. 설치 버전과 binary SHA는 `evidence/external-toolchain.log`에 남겼다. 이 작업에서 읽은 것은 외부 public API·사용자 문서·입력 사전이며 GPL 구현 소스는 아니다.

아래는 checkout 루트의 PowerShell에서 실행한다. 이미 결과가 있는 현재 폴더에서 생성 단계를 다시 실행하면 **기존 trial 거부**가 정상이다. 실패·부분 결과도 삭제하거나 덮어쓰지 말고 새 후보를 사용한다.

```powershell
uv run research/a321-quality/prepare_snappy.py
wsl -d Ubuntu -- bash /mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/run_snappy.sh
uv run research/a321-quality/prepare_snappy_balanced.py
wsl -d Ubuntu -- bash /mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/run_snappy_balanced.sh
uv run research/a321-quality/audit_poly.py --case D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight\research\a321-quality\artifacts\snappy-03 --run-id v5
uv run research/a321-quality/layer_fields.py
uv run research/a321-quality/plot_quality.py
uv run research/a321-quality/package_quality.py
```

두 번째 실험 `prepare_snappy_refined.py`/`run_snappy_refined.sh`는 제외된 snappy-02를 만든다. 기본 checkMesh의 `Mesh OK`와 명시적 70° 기준이 다를 수 있음을 재현하는 대조군이다. 이 후보를 최종 후보로 선택하지 않는다.

runner는 `GENERATION_AND_DIAGNOSTICS_COMPLETE_NOT_ACCEPTANCE`까지만 보고한다. 종료 코드 0, `Mesh OK`, 독립 수치 PASS를 서로 대신 사용하지 않는다. acceptance는 `package_quality.py`가 감사 후보명·원본 SHA·실제 polyMesh 다섯 파일 SHA를 일치시킨 다음 계산한다. 확장 검사의 실패와 engineering/GPU HOLD는 별도로 남긴다.

Ubuntu split binary package의 upstream bashrc는 누락된 `bin/foamEtcFile` 경로를 기대했다. 실행기는 `/usr/bin` 도구와 명시적 `FOAM_ETC`/`WM_PROJECT_DIR` 환경을 사용한다. 이 패키지의 scotch stub 대신 hierarchical 2×2×2 분할을 사용했다. 시스템 bashrc나 라이브러리를 수정하지 않았다.

## 데이터 custody

prepare는 새 폴더를 배타적으로 만들고 입력 manifest를 기록한다. 파생 prepare는 parent manifest를 검증한 뒤 의도한 설정만 바꾼다. runner는 원 R3 SHA와 입력 manifest, 기존 mesh·processor·로그 부재, 배타적 실행 lock을 검사한다. 중복 시작·부분 실행·기존 결과를 모두 거부하며 lock은 실패 시에도 보존한다. 실제 [guard 검증](evidence/guard-tests.json)은 동시 실행 0/2, 기존 결과 거부 2, 변경 입력 거부 1을 기록했다.

이번 01/02/03은 초기 연구 실행 후 검토에서 guard를 추가했다. 그 입력 manifest는 **legacy_post_run_snapshot=true**로 표기했으며 실행 전 freeze였다고 주장하지 않는다. 향후 새 prepare가 만드는 manifest는 실행 전 기록이다. 현재 후보의 mesh 해시와 원본 SHA는 최종 감사·다섯 검토에서 실제 비교했다.

auditor는 이 연구 artifacts의 직접 자식만 허용한다. `--run-id`는 영숫자·하이픈으로 제한하며 같은 run-id의 산출물/lock이 있으면 거부한다. 다른 경로·동일 이름 영수증 충돌·동시 쓰기로 기존 결과를 바꾸지 않는다. 읽기 전·출력 전 SHA가 달라지면 영수증을 내보내지 않는다. 계산법을 바꿔 다시 검사할 때는 `--run-id v6`처럼 새 이름을 쓰고 기존 증거를 보존한다. 패키저도 새 영수증 버전을 명시적으로 선택해야 한다.

## 테스트

```powershell
uv run --with numpy --with trimesh --with pydantic --with pytest python -m pytest research/a321-quality -q
uvx ruff check research/a321-quality
uvx ruff format --check research/a321-quality
```

회귀 범위: 오목 면 signed centroid, warped face의 삼각형별 체적·모멘트, 실제 3D warped face, hanging edge, 병합으로 숨겨지는 틈, 잘못된 좌표/정점/셀 ID와 누락 footer, stale audit, audit 경로 제한, NaN 거부, 기본 Mesh OK와 숫자 기준의 분리. 검사는 실제 사면체·전체 경계층·공력 validation의 대체물이 아니다.

## Ego Lite Studio

기존 `research/a321-integration/start-studio.ps1`을 따라 이 checkout의 Studio를 실행한다. main checkout의 기존 package 변경은 건드리지 않는다. Ego에서 `http://127.0.0.1:5183/`를 열고 탐색기에서 snappy-03 `calculation-wall-v5.stl`을 연다. snappy-03 폴더를 우클릭해 **3D 뷰어로 열기**를 선택하면 462,113셀 표시를 확인할 수 있다. 기본 표면은 외부 영역 박스다. 벽 자체는 별도 geometry 탭에 있다.

`ego-*.mjs`는 이번 TaskSpace 8의 조작 원장이다. 종료 후 TaskSpace를 자동 재사용하는 설치 스크립트가 아니다. 새 사용자 작업에는 새 space와 현재 snapshot을 사용한다. local reader의 `exact`는 모델 검증 판정이 아니며 UI의 GPU/AI 데모 수치는 계산 증거가 아니다.

확장 실패·형상 허용오차·무층 영역이 남으므로 항공기 GPU solver는 실행하지 않는다. 이후에도 이 영수증의 `NAMED_CPU_GATES_PASS`만으로 GPU HOLD를 해제하지 않는다.
