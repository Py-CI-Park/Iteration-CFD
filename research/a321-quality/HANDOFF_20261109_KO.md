# A321 공력 연구 중단 복구·전체 핸드오프

**작성일 2026-11-09(KST). 결론: 작업은 보존·재개 가능하며, 현재 형상 인수 M3는 FAIL이고 항공기 GPU 해석은 미실행이다.** 이 문서는 사용량 만료로 중단된 실행을 다른 Codex 세션·checkout·컴퓨터에서 이어가기 위한 인계 기준이다. 새 실험을 실행한 보고서가 아니다.

## 1. 가장 먼저 알아야 할 상태

```text
STATUS DASHBOARD
================================================================
기준 브랜치   codex/a321-aero-shell-20261105
중단 전 HEAD  e3b809de24f0a40ee689831406a9a5931fd49b21
현재 보존     위 HEAD 이후 미커밋 연구 코드·모델·로그·문서까지 수록
목표          단순화 A321 계열 airframe, 30 m/s·기준 받음각 0°
실제 외형     R3/R4 보존 + R5-A/C 실패 초안 생성
현재 gate     M3 FAIL: C 독립 자기교차 15 locations
새 R5 격자    NOT GENERATED
항공기 유동   NOT RUN
항공기 GPU    HOLD
기존 준비     [###-----] 3/8 기존 체크포인트
================================================================
```

3/8은 이전 계획에 정의된 무가중 체크포인트 개수다. 공학적 완성도·공력 정확도·GPU 성공 확률 37.5%를 뜻하지 않는다. R5가 만들어졌어도 형상·경계층·격자·엔진 인수가 남아 있어 이 수치를 임의로 올리지 않았다.

**바로 다음은 C의 15개 자기교차 위치를 식별하고, 실제 feature/접합 설계를 보완해 새로운 후보를 검증하는 일이다.** C를 계산용으로 채택하거나 GPU를 시작하는 단계가 아니다. 핸드오프 요청 이후에는 mesher·Blender·GPU 실험을 새로 실행하지 않고, 완료된 파일을 읽어 상태와 보관을 정리했다.

## 2. 저장소·브랜치·통합 경계

| 구분 | 위치·기준 |
|---|---|
| 실제 연구 checkout | `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight` |
| 프로젝트 main checkout | `D:\Chanil_Park\Project\Programming\Iteration-CFD` |
| 원래 참고 모델 프로젝트 | `D:\Chanil_Park\Project\Programming\Aircraft-Workbench` |
| Codex 대화 cwd | `C:\Users\parkc\Documents\Codex\2026-11-04\ego-lite-mcp-ego-lite-d` — 연구 Git 루트가 아님 |
| 원격 origin | [Py-CI-Park/Iteration-CFD](https://github.com/Py-CI-Park/Iteration-CFD) |
| 연구 브랜치 | `codex/a321-aero-shell-20261105` |
| 실행 출발점 | `e3b809de24f0a40ee689831406a9a5931fd49b21` |
| 직전 실험 commit | `9b132e6377d9fbff8490d3a47c770b0fb37ffa6f` |
| 이번 읽기 시 local main / origin/main | `8099602643f5ed30716805f2fa6ecd7ddd1e4643`; 원격 최신성을 새 fetch로 판정한 결과는 아님 |
| Git 관계 | 위 local main은 시작 연구 HEAD의 ancestor로 확인 |
| 변경 범위 | 연구 코드/증거/모델/상태/핸드오프·provenance. 솔버 수치 코어 변경 없음 |

main checkout의 사용자 파일을 바꾸거나 main에 자동 merge하지 않는다. 이 커밋은 **WIP 연구 스냅샷**이며 제품 release·최종 형상/격자 합격 커밋이 아니다. `e3b809d`로 reset하면 새 연구를 잃으므로, 기준점은 비교에만 사용한다.

## 3. 누적 사용자 의도·승인

원래 목표는 Aircraft-Workbench의 A321 Blender 모델을 참고해 **항공기 공력 해석을 한 번 직접 경험**하는 것이다. Ego Lite·컴퓨터 유즈·Chrome·CLI를 활용하고, 모델부터 격자·실행 환경·첫 시험·문서·Git까지 에이전트가 직접 진행하도록 요청했다.

- R3 원본과 이전 실패 결과를 보존한다. 공력용 새 겉껍데기와 Blender 외형 재생성은 허용됐다.
- 매끄러운 표시만 바꾸지 말고 홈/단면/접합과 실제 기하를 확인한다.
- 저속 외부유동 **30 m/s·기준 받음각 0°**를 첫 목표로 사용자가 선택했다.
- 기존 비직교·폐합·양수 체적·확장 품질·경계층 조건을 낮춰 합격시키지 않는다.
- GPU 메모리 테스트는 승인됐지만 **품질 통과 전 항공기 GPU 해석 금지**는 계속 유효하다.
- AI API 직접 호출/등록 가능성 조사와 코드 수정 검토는 허용됐으며, 필수 의존성은 아니다.
- Ego Lite 기존 space10이 사라진 뒤 **새 연구 공간 생성 승인**을 받아 space15를 만들었다.
- 상세 한국어 Markdown·HTML·실제 화면 증거·한글 커밋/연구 브랜치 push와 지속적 진행 보고를 원한다.
- 이번 최신 요청은 연구 확대 실행이 아니라 **중단 지점까지 빠짐없이 파악·검토·핸드오프 작성 후 커밋**이다.

[대화 요구·의사결정 연속성](HANDOFF_CONTEXT_KO.md)에 요청 흐름과 오해 방지 항목을 별도로 수록했다. 이것은 전달된 대화와 저장 증거의 정리이며, 과거 모든 assistant 답변의 원문 transcript라고 주장하지 않는다.

## 4. 누적 연구 연혁

전체 commit 목록과 파일 목록은 [이력](evidence/handoff-git-history.txt), [연구 파일 색인](evidence/handoff-research-file-index.txt)을 따른다. 아래 표는 흐름을 이해하기 위한 핵심 이력이다.

| commit | 누적 작업과 해석 |
|---|---|
| c3b4a9b | 원 A321 표면 CPU 사전검사·첫 연구 로드맵 |
| 6d4bfed | R2 공력 shell·CPU 격자 준비 |
| ab176ae | Studio 로딩·wing notch 수정·R3·hybrid polyMesh·SUPER 제한적 메모리 진단 |
| c5295b0 | R3 보존·뒤집힘 없는 8층 Jacobian/접합 연구. 비직교·폐합 미해결 |
| f8b186b | hex/poly 대안으로 명시 기본 CPU gate 통과. 확장·경계층·GPU는 미합격 |
| cfd592b / 5ec807f | 실행 입력 dictionary 바이트/EOF 보존 |
| a39d590 | 당시 upstream main 병합. 현재 upstream 최신 반영을 뜻하지 않음 |
| 1e08cbd | 모델/격자 실제 화면과 GPU 전 준비표를 통합 보고서에 추가 |
| 3a67a10 | 실패 위치 지도·국소 격자·GPU 메모리/API 조사 |
| 376e9f2 / b2de364 | 30m/s 근벽 조건·실제 층 지도 복구, 기존 HTML PC/모바일 검증 |
| 9b132e6 | R4 국소 외형과 08~11 CPU 비교; 원본 보존·GPU HOLD |
| e3b809d | Blender 외형부터 첫 공력 시험까지 M0~M9 전체 실행 계획 |
| 이번 핸드오프 | e3 이후 미커밋 M1/M4 준비, R5-A/B/C, 안전 보강·증거·중단 상태를 동결 |

원본 증거 폴더를 상위 최신 상태 문서로 덮지 않는다. 예전 문서의 “이번에는 R5 미생성”은 당시 계획 시점으로는 맞는 기록이며, 현재 상태는 [EXECUTION_STATUS_KO.md](EXECUTION_STATUS_KO.md)와 [execution-status.json](execution-status.json)이 담당한다.

## 5. 지금까지 측정된 격자 결과

### 기존 경계층·사면체 경로

R3를 고정하고 8층 프리즘의 Jacobian 실패를 174→68→21→6→0으로 줄인 실험이 있다. 그러나 극소층 약32nm, 최대 비직교 약89.9927°, 상대 폐합 약4.0103e-10 문제를 남겨 최종 경계층/CFD 채택은 하지 않았다. TetGen 외부 좌표 정확 보존 실패와 등방성 표면 최대 표본 이탈74.3185mm도 제외 기록으로 남았다.

[경계층 연구](../a321-layers/README_KO.md), [진단](DIAGNOSIS_KO.md), [이전 실행 절차](RUNBOOK_KO.md)를 읽는다. 뒤집힘 없음과 물리적으로 유효한 경계층·좋은 외부 셀은 서로 다른 조건이다.

### hex/poly 대안과 후속 비교

snappy-03은 462,113셀, 최대 독립 비직교66.203955°≤70°, 최대 상대 폐합8.259123e-15≤1e-10, 비양수 체적0, 기본 checkMesh Mesh OK를 통과했다. **확장 검사3종 FAIL**, 전 표면 경계층 미완성·형상 적합성 미수용이므로 제한적 CPU 수치 후보다.

| 실제 비교 | 06 | 10(R4+weight) | 11(buffer3) |
|---|---:|---:|---:|
| 작은 determinant 셀 | 2,964 | 2,901 | 85 |
| 오목 셀 | 44,911 | 44,883 | 35,393 |
| 낮은 보간 가중치 면 | 176 | 0 | 0 |
| 층 생성 면적 | 92.76% | 91.33% | 94.07% |
| 평균 실제 층 수 | 3.14 | 3.14 | 1.93 |
| 완전8층 면 | 2,897 | 2,908 | 0 |
| 확장 실패 종류 | 3 | 2 | 2 |

11의 숫자 개선은 층 깊이 손실을 동반해 채택하지 않았다. 09의 R4-only 대조도 실패3종을 해결하지 못했다. R4의 원 station 최대 이동 약0.250164mm는 국소 변경이며 전체 익면을 새로 설계한 결과가 아니다. 위 비교는 기존 [surface-comparison.json](evidence/surface-comparison.json)·[계획](REBUILD_ROADMAP_KO.md)의 기록을 인계한 것으로 이번에 격자를 재생성한 것이 아니다.

비직교·폐합의 정의는 그대로 유지한다. 상대 폐합은 `|ΣSf| / V^(2/3)`이며 다른 도구의 다른 분모로 바꾸지 않는다. 확장 determinant/concavity/interpolation weight 및 겹침·층 포착을 기본 Mesh OK로 대체하지 않는다.

## 6. e3 이후 실제 작업: M1 → R5-A → B 거부 → C 실패

### M1 고정 입력·계약

- [원장](evidence/r5-m1-source-ledger.json): 동체182개 station×128점, 주익100×128점, 수평67×96점, 수직76×96점.
- [생성 전 동결](evidence/r5-m1-freeze.json): R3 STL/단면원장·R4 STL/native·형상 계약 해시 고정.
- [계약01](plans/r5-geometry-contract-01.json): 원 station·bbox 최대1e-5m, station 사이 표본 이탈 동체25mm/주익·미익10mm, R3 대비 상대체적 변화≤1%.
- 이 값은 파생 형상에 대한 연구 제한이지 OEM 공학 허용오차가 아니다.
- [방법 보충01](plans/r5-method-supplement-01.json)은 **A 실행 후·B 전** 작성했다. A 방법 전체를 실행 전 고정했다고 소급 주장하지 않는다.
- 의도한 planform kink·LE/TE·chordwise 곡률·wing-body 전이의 완전한 feature별 설계는 아직 부분이다.

### R5-A

실제 생성 761,090삼각형. 원 section ring을 유지하고 길이/span 대응점 PCHIP와 2%/98% shoulder 제어점을 사용했다. bbox 변화0, R3 대비 상대체적 변화8.932705597627663e-8, 원 단면 최대 약1.92µm 오차. native 저장·새 Blender 재읽기·STL/NPZ 대응과 내부 topology는 통과했다.

**독립 surfaceCheck 자기교차4,184위치 FAIL.** 최소 triangle quality1.19287e-11, 저품질 극소면 잔여. 내부 closed/manifold와 독립 교차 통과는 다르다. analytic 길이/span 궤적 C1이 실제 다각형 단면·삼각형 STL·Boolean seam 전체 C1인 것은 아니다. 신규 fillet·전체 chordwise CAD 재구성·OEM 정확성 주장은 없다.

### R3/R4 대조 검사

같은 외부 CLI에서 R3 72위치, R4 86위치가 보고됐다. [대조 영수증](evidence/r5-controls-surfaceCheck-receipt.json), [요약](evidence/r5-controls-surfaceCheck-summary.json), 원시 로그를 보존했다. 원본 전후 SHA 동일. A4184를 모두 새 보간만의 결함이라고 확정하거나 위치 수를 심각도 순위로 쓰지 않는다.

### R5-B

고정1µm cleanup 후보는 manifold3d 실제 최소 허용오차5.306005277816439µm가 선언 상한보다 커 **생성 전에 거부**됐다. worker 초기 시도와 부모 별도 시도 모두 실패 영수증을 보존했다. B 모델은 생성되지 않았다.

[worker 거부](rebuild/evidence/rebuild-r5-b-attempt-01-failure.json), [부모 거부](evidence/r5-cleanup-b-failure.json). 현재 `cleanup_b.py`의 오래된 코드 freeze는 후속 보강 코드와 달라 재실행 거부가 정상이다.

### R5-C: 중단 직전 완료된 결과

새 [C 계약](plans/r5-cleanup-c-contract.json)을 실행 전에 만들고 요청6µm를 별도로 선언했다. B 기준을 수정해 B를 합격시킨 것이 아니다. 기존 M1 bbox/체적 조건과 독립 교차 gate는 그대로다.

| 항목 | 실제 결과 |
|---|---|
| kernel 실제 허용오차 | 5.306005277816439µm |
| 삼각형 | A761,090 → C305,764 |
| bbox 변화 | 0m |
| R3 상대체적 변화 | 3.2680332447930774e-8 |
| A→C / C→A 표본 최대 | 5.046749µm / 5.189853µm, 각2,000표본 |
| 내부 topology·원본 불변 | PASS |
| 독립 검사 | **self-intersecting at15locations / End 완료** |
| 최소 triangle quality | 9.70744e-13 |
| native | Blender5.2.2 LTS, 152,884정점·305,764삼각형 |
| native/STL 좌표·삼각형 | 정확 일치 PASS |
| M3 / 새 R5 체적 격자 | FAIL / 미실행 |

C 원시 export 파일명이 `rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl`인 것은 복사된 이름이다. **directory·계약·receipt·SHA로 C를 식별**한다. 별도 `models/A321_AIRFRAME_REBUILD_R5_C.stl`은 같은 SHA의 presentation 사본이다. 원 export를 이름만 바꾸거나 영수증을 소급 수정하지 않는다.

`r5_c_surface_check.sh` 첫 실행은 잘못된 A basename 때문에 입력 부재로 거부됐다. 수정된 `r5_c_surface_check02.sh`가 실제 검사했다. noclobber 로그를 유지하므로 같은 스크립트를 기존 결과 위에 재실행하면 거부가 정상이다. exit0만으로 합격을 판정하지 않는다.

C 생성 영수증의 `PENDING_INDEPENDENT_CLI`·`NOT_YET_SAVED`는 생성 당시 상태다. 실제 후속 로그·native 영수증을 읽은 [핸드오프 판정](evidence/r5-c-independent-handoff.json)이 최종 M3 FAIL과 Blender 완료를 연결한다. 생성 영수증 자체는 불변이다.

## 7. 미완료·결함·검토 상태

| 우선순위 | 항목 | 다음 조치·수용 조건 |
|---|---|---|
| P0 gate | C 자기교차15위치 | 실제 좌표/triangle/부품/feature를 새 로그로 지도화. 원인 분리 후 새 후보에서0교차 검사 |
| P1 형상 | 극소/긴 삼각형·원 다각형 단면·Boolean 접합 | 적응형 tessellation·패치·LE/TE/tip/전이 설계. 새 geometry contract로 사전 고정 |
| P1 계약 | 전체 feature 설계 부분 | 유지할 kink·rounding 허용·두께·단면·대칭·곡률 지표 고정 |
| P1 메타데이터 | C native scope가 “local wing interior seam rounding only”·mesh명 R4 | 실제 C 범위와 불일치. **별도 이름의 새 presentation/native**에서 설명만 정정하고 기하 동일성·새SHA·fresh readback |
| P1 시각 검증 | R5-A/C Studio 화면 미완료 | space15 생존 확인 후 원본/새모델·전체/주익/접합부 flat/smooth/wireframe 비교·실제 screenshot |
| P1 재현 | A 생성 당시 코드와 사후 안전 보강 코드가 다름 | post-generation snapshot을 실행 전 freeze로 주장하지 않음. 보존 모델의 정확 재개와 재생성을 구분 |
| P1 코드 검토 | 최종5분야 review 미종결 | Goodall 보강 영수증만으로 모든 reviewer PASS 선언 금지. 부모 B/C helpers·adapter 별도 재검토 |
| P1 엔진 | native CPU-only 인수 경로 없음 | Gpu::new 이전 host-only 검사 설계·회귀. -iters0 우회 금지 |
| P2 코드 정리 | 부모 B/C runner 중복·C에 남은 B 출력/거리 label·R4 error 문자열 | frozen executed-code는 보존하고 다음 버전 모듈화·정확 명명. 현재 스냅샷을 release 코드로 취급하지 않음 |
| P2 문서/화면 | 새 HTML은 정적 문서; 최종 Ego 화면 QA 미완료 | static 링크/JSON/hash 검사와 실제 브라우저 확인을 구분 |

기존 검토 작업자 세션은 사용량 중단 후 조회에서 모두 `not_found`였다. 이어지는 세션은 이전 agent ID를 가동 중인 작업자로 가정하지 않는다. 원시 기록에 없는 최종 승인·실행 시간·후속 성공을 만들어내지 않는다.

## 8. 테스트·안전 보강 증거

[안전 보강 closeout](rebuild/evidence/rebuild-safety-closeout.json)에는 당시 통합 Python22 PASS(278.95초), 별도 custody3 PASS(319.73초), 실제 Blender guard5 PASS가 기록됐다. 해당 범위는 cap·finite 검사, 같은 captured bytes 해시/parse, R4 동결 비교, native world transform/parent/modifier/SHA/배타 lock 거부다.

부모 tolerance guard는 미구현 상태2fail/1pass 후3pass로 기록됐다. 이 실행의 원시 pytest 로그는 별도 파일로 남아 있지 않아 대화 인계 결과로만 구분한다. worker 초반 모듈 부재 RED는 알고리즘 결함 재현과 다르다. 중복 실행된 custody3개를 더해 독립 테스트 총개수처럼 보고하지 않는다.

과거143PASS·480개 원장·HTML25이미지/82링크는 **9b132e6 시점**의 증거다. 이번에 재실행한 결과가 아니다. 이번 핸드오프는 해시·증거·문서 링크·Git 바이트 보존 검사이며 CFD/형상 새 실험이 아니다. 결과는 [핸드오프 검증](evidence/handoff-validation.json)에 둔다.

필요 시 새 세션에서 CPU 회귀를 다음처럼 재실행한다. 환경 생성이 오래 걸렸으므로 기존 uv 환경을 확인해 재사용할 수 있지만 경로가 다른 컴퓨터에서 존재한다고 가정하지 않는다.

```powershell
uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh --with rtree python -B -m pytest -p no:cacheprovider research/a321-quality/rebuild/test_rebuild.py research/a321-quality/rebuild/test_binding.py research/a321-quality/rebuild/test_topology.py research/a321-quality/rebuild/test_cleanup.py research/a321-quality/rebuild/test_hardened_curves.py research/a321-quality/rebuild/test_custody.py -q
uv run --with pytest --with numpy --with scipy --with trimesh --with manifold3d --with rtree python -B -m pytest -p no:cacheprovider research/a321-quality/test_r5_cleanup_guard.py -q
```

의존성 패키지의 정확 버전이 모두 잠겼다는 보장은 없다. C 실행은 manifold3d3.5.4로 기록됐고 생성 코드가 상수 경로·기존 artifact 존재를 검사한다. 기존 후보를 다시 실행해 덮어쓰지 않는다.

## 9. 전체 재개 로드맵과 GPU 해제 조건

```text
ROADMAP
[M0 원본/실패 보존] DONE
          |
[M1 feature 계약] PARTIAL <-----------------------+
          |                                       |
[M2 새 곡면/계산 표면] A/C DRAFT                  |
          |                                       |
[M3 독립 형상 검사] C FAIL15 ----- 원인/새후보 ----+
          |
         PASS
          v
[M4 물리·경계층 설계] → [M5 새 CPU mesh+확장/층 검사]
                                  | FAIL → 지도화·재생성
                                 PASS
                                  v
[M6 실제 엔진 host-only 인수·필드/patch 계약]
                                  |
[M7 sm_89 빌드·장치·기준문제·VRAM·중단조건]
                                  |
                             모든 gate PASS
                                  v
[M8 짧은 첫 항공기 GPU 시험] → [M9 수렴·민감도·검증]
```

| 단계 | 남은 구체 작업 | 완료 기준 |
|---|---|---|
| M1/M2/M3 | C 교차 지도, 실제 홈/굴곡과 flat shading 분리, 단면·접합·feature 재설계 | 정해진 편차·단면·대칭·폐합·다양체·법선·퇴화/교차·면 품질 검사. native/표면 대응. 설계 일부를 누락한 채 채택 금지 |
| M4 | rho/nu/T·고도 가정, 난류/벽처리, first height·총두께·층수·성장률·외부영역·힘축/기준 | 30m/s·0°와 일관된 runnable 물리 명세. 사전 추정 y+와 계산 후 y+ 구분 |
| M5 | feature-preserving 계산 표면+근벽층+외부 체적 공동 생성 | 비직교≤70°, 상대폐합≤1e-10, 양수체적/Jacobian·연결·접합·patch, 확장3종·충돌·유효층 포착. 층 손실로 수치 통과 대체 금지 |
| M6 | native reader/host-only 경로, 단위·경계·U/p/T·난류/물성 지원 | Python checker가 아닌 실제 선택 엔진 인수. lowmach GPU 선초기화 해결 필요 |
| M7 | CUDA 준비·sm_89·정확 binary·SUPER UUID·실제 메모리/기준 문제 | 올바른 장치·커널 호환·peak VRAM·중단조건·지원 물리 검증 |
| M8 | 짧은 항공기 시험 감시 | U/p 갱신·질량수지·잔차·힘·실제 y+·발산/NaN 없음. 시작 성공만으로 합격 아님 |
| M9 | 반복수렴·거친/중간/세밀 격자·영역민감도·공개 validation | 수치 불확실성과 단순화 한계를 명시. 실기 자료 없으면 OEM validation 미완료 |

병행 가능한 일은 문서·host-only 코드 설계·빌드 환경 점검이다. M3 전 R5 새 체적 격자/항공기 solver를 실행하지 않는다. 수치 코어·모델 상수·공개 validation 숫자 변경은 저장소의 별도 issue/maintainer 계약 대상이므로 이 연구에서 임의 변경하지 않는다.

M4 준비용 gross XY wing 면적126.47650505852299m², span32.58000183105469m, mean geometric chord3.8820287891441367m는 원 단면에서 산출했다. 동체 내부 root 포함, wetted area·MAC 아님. 최종 R5 CL/CD 기준으로 아직 채택하지 않았다.

## 10. GPU·엔진·AI API·Studio의 실제 범위

- 목표 GPU는 **RTX4080SUPER UUID GPU-2147afeb-b9fc-c7f5-398b-d5d00a3a5a90**. 과거 물리 장치 조회는 4080과 SUPER를 각각16376MiB로 보고했다. 장치 index는 재시작 뒤 달라지므로 재확인한다.
- 과거 제한적 메모리 진단은1GiB할당·64MiB왕복복사·해제 후free동일을 확인했다. 전체VRAM·산술kernel·장시간부하·실제항공기solver·최대셀수 보증이 아니다.
- 지난 읽기에서 Toolkit12.6, README 요구13.x, 기본 arch sm_120, 두 release경로 실행기 부재. SUPER용 sm_89/`OFGPU_CUDA_ARCH=89` 준비가 필요하다. 최신 설치 상태는 재개 시 다시 확인한다.
- lowmach는 `Gpu::new(0)` 후 case load를 하므로 **-iters0도 GPU초기화를 포함**한다. CPU 인수라고 실행하면 안 된다.
- 난류 전용 ofgpu-k-epsilon/k-omega/sa를 전체 항공기 U/p 해석기로 쓰지 않는다. U/p/T coupled 경로의 실제 지원·BC·난류·힘 기능을 확인한다.
- Studio의 RTX4090/24GB·AI 대화는 demo 표시다. 형상/격자 reader 성공과 solver 실행/물리 GPU 실측은 다르다.
- API 직접 연동 조사 승인은 있으나 이번 R5 연구에서 외부AI API를 호출하거나 키를 새 등록하지 않았다. “OpenCodex가 등록되어 실제 통신 가능”은 확인되지 않았다. 새 세션에서는 provider schema·endpoint·auth·모델·응답형식·서버로그로 확인하고 secret을 Git/HTML에 남기지 않는다.
- GPU 메모리 검사 증거는 [gpu-memory-20261107.json](evidence/gpu-memory-20261107.json), API/reader 증거는 [studio-api-20261107.json](evidence/studio-api-20261107.json)을 따른다.

## 11. Ego Lite 복구·시각 검증 순서

[공간 기록](evidence/execution-browser-space.json): task명 `A321 roadmap execution 20261108`, space15/p1, 당시 Studio `http://127.0.0.1:5185/`, backend8815/version2.0.0/demo, 보고서 server8776. 이는 당시 관찰이며 이번 핸드오프에서 서버/space 생존을 재검증하지 않았다.

1. 설치된 ego-browser skill을 다시 읽고 현재 inventory로 space15·p1과 URL을 확인한다.
2. 같은 space/page가 있으면 이어간다. 과거space10은 없어졌으므로 그 ID를 반복 호출하지 않는다. 새space 허용은 이미 받았고 필요 시 이를 근거로 사용하되 중복생성보다 현재 상태 확인이 먼저다.
3. [Studio 시작 절차](../a321-integration/start-studio.ps1)를 읽고 연구 checkout을 root로 서버를 연다. main의 package/서버를 바꾸지 않는다.
4. R3/R4/A/C를 각각 표시하고 전체·날개·접합부를 같은 view로 비교한다. geometry탭과 volume dataset API를 혼동하지 않는다.
5. GPU/solver 버튼은 누르지 않는다. 숨은 geometry-info를 현재 모델로 오인하지 말고 보이는 pane의 이름·triangle수·경로를 확인한다.
6. 스크린샷은 창 복원 후 실제 화면에서 캡처한다. 화면에 보이는 smooth shading과 좌표의 실제 개선을 나누어 설명한다.
7. 새 R5 screenshot·HTML PC/모바일·로컬 링크 확인 후 새 receipt·status를 남긴다. 확인하지 못하면 PENDING로 유지한다.
8. 최종 Studio·보고서 탭을 남기고 skill의 finish 절차를 완료한다. 현재 space15 finish/최종화면 검사는 미완료다.

`execution-gallery/01~04.mjs`는 실행 이력이다. 현재 PC에 고정된 절대경로·과거 space명을 포함하므로 새 환경에서 무조건 일괄실행하지 않는다.

## 12. 파일 구조와 보관 경계

```text
research/
+-- a321-preflight/     원 참고모델 감사·단면·초기 진단
+-- a321-shell/         R2 셸·재구성/Blender·라이선스·실행 절차
+-- a321-integration/   R3·Studio·hybrid polyMesh·GPU 제한진단
+-- a321-layers/        비뒤집힘 프리즘·사면체·인터페이스 연구
'-- a321-quality/
    +-- report.html / README_KO.md          기존 통합 실험(보존)
    +-- REBUILD_ROADMAP_KO.md / rebuild-roadmap.html  e3 계획(보존)
    +-- EXECUTION_STATUS_KO.md / execution-status.json / .html
    +-- HANDOFF_20261109_KO.md / handoff-20261109.html  이번 인계
    +-- HANDOFF_CONTEXT_KO.md               누적 요구·결정
    +-- M1_GEOMETRY_SPEC_KO.md / M4_PHYSICS_PREPARATION_KO.md
    +-- plans/                             버전별 계약·방법
    +-- models/                            R4·C presentation STL/native
    +-- evidence/                          원시 로그·숫자·해시·화면
    +-- rebuild/
    |   +-- *.py / surface_check.sh         A 생성·안전 guard·tests
    |   +-- evidence/                       A/B·Blender·보강 기록
    |   '-- artifacts/rebuild-r5-a,b,c/      이번 명시 보존 snapshot
    +-- execution-gallery/                 중단 브라우저 조작 기록
    '-- artifacts/snappy-01~11/...         대형 CPU mesh 로컬 보존
```

이번에는 **실패 R5-A STL/BLEND/NPZ, B 실행코드/입력원장, C raw STL/NPZ/실행코드/입력원장, C presentation STL/native**를 명시적으로 Git에 수록한다. 일반 artifacts ignore 규칙을 전체 해제하지 않는다. 실행 중간 cache·fixture·locks는 원격 복제 필수 자산과 구분한다. A/C 실패 모델도 입력·검사 재개를 위해 보존할 가치가 있으며 계산용 accepted 모델은 아니다.

기존 snappy/processor/대형 NPZ·mesh는 계속 로컬에 있고 이번에 원격 전체 업로드하지 않는다. 다른 컴퓨터에서 예전 격자를 그대로 열려면 **해당 artifacts를 별도 복사하고 기존 manifest로 검증**하거나, 보존된 입력·도구 버전·새 output 경로로 재생성해야 한다. 새clone에 원시 격자가 전부 있다고 가정하면 안 된다.

정확한 파일 SHA/크기/전달 범위는 [핵심 자산 manifest](evidence/handoff-critical-assets.json), [로컬 보존 폴더](evidence/handoff-local-artifact-inventory.json), [전체 연구 파일 색인](evidence/handoff-research-file-index.txt)을 따른다. manifest는 relative path로 제공하므로 checkout 루트가 달라도 검증할 수 있다. 원시 영수증 안의 당시 절대경로는 감사 이력으로 남긴다.

이식성 검사에서 기존 Git의 R3 단면 원장만 LF로 정규화되고 로컬 M1 동결본은 CRLF인 차이를 발견했다. 이번에는 **로컬 입력 바이트를 바꾸지 않고**, 해당 파일 하나의 Git 속성을 raw 보존으로 지정해 동결 SHA가 새 clone에서도 유지되도록 기록했다. STL/native나 JSON 데이터 값 변경이 아니다. 과거 commit을 재작성하지 않으며, 기준 Git blob과 새 보존 blob이 다른 이유·줄바꿈만의 차이 증명은 [입력 보존 보완](evidence/handoff-r3-ledger-byte-custody.json)에 둔다. rebuild의 원시 영수증·실행 snapshot도 같은 바이트 보존 규칙을 적용했다.

## 13. 기존 PC·새 clone·main에서 안전하게 재개

### A. 기존 연구 checkout

```powershell
Set-Location 'D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight'
git status --short --branch
git log -3 --oneline
git diff e3b809de24f0a40ee689831406a9a5931fd49b21..HEAD --stat
Get-Content research/a321-quality/EXECUTION_STATUS_KO.md
Get-Content research/a321-quality/evidence/r5-c-independent-handoff.json
```

핸드오프 커밋은 이 문서를 포함하는 commit으로 `git log -1`에서 식별한다. 문서 안에 자기 자신의 commit SHA를 넣으려고 amend를 반복하지 않는다. 로컬 dirty가 있으면 소유자와 내용을 확인하고 reset/clean으로 지우지 않는다.

### B. 다른 컴퓨터의 새 clone

```powershell
git clone --single-branch --branch codex/a321-aero-shell-20261105 https://github.com/Py-CI-Park/Iteration-CFD.git Iteration-CFD-a321-resume
Set-Location Iteration-CFD-a321-resume
git status --short --branch
Get-Content research/a321-quality/HANDOFF_20261109_KO.md
$assetManifest = Get-Content research/a321-quality/evidence/handoff-critical-assets.json -Raw | ConvertFrom-Json
$assetManifest.assets | ForEach-Object {
    $assetPath = Join-Path (Get-Location) $_.path
    if (!(Test-Path -LiteralPath $assetPath)) { throw "MISSING: $($_.path)" }
    if ((Get-FileHash -LiteralPath $assetPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $_.sha256) {
        throw "HASH_MISMATCH: $($_.path)"
    }
}
```

이 clone 명령은 연구 브랜치가 원격에 push된 뒤 가능하다. 원격 반영에 실패한 경우 로컬 커밋만으로는 다른 컴퓨터가 가져올 수 없으므로 Git bundle 또는 별도 전달이 필요하다. 이번 실제 commit/push 결과는 사용자 안내에서 구분한다.

### C. main에 있는 세션에서 재개

먼저 현재 폴더·branch·dirty·remote를 확인한다. 연구 브랜치가 다른 worktree에 checkout돼 있으면 해당 연구 checkout으로 이동하는 것이 우선이다. 새cleanclone에서 필요한 경우 다음처럼 별도 재개 branch를 쓴다.

```powershell
git fetch origin
git switch -c codex/a321-resume-20261109 origin/codex/a321-aero-shell-20261105
```

main 기반 통합이 꼭 필요하면 **별도 integration branch에서 연구 branch의 누적 이력을 merge하고 충돌/도구 변화/해시를 검토**한다. 핸드오프 commit 하나만 main에 cherry-pick하면 R3/R4/기존 연구 선행 파일이 누락될 수 있다. main에 자동 merge하거나 이 문서만 복사해 실행하지 않는다. 실제 새worktree가 필요할 때는 Codex의 create_worktree 절차를 따른다.

### D. 보존 C 독립 검사만 새로 할 경우

먼저 CLI help·version을 확인하고 새 attempt 폴더를 만든다. 기존02 로그를 덮지 않는다. WSL bash 예시이며 경로는 현재 checkout으로 바꾼다.

```bash
set -euo pipefail
task_root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight
attempt_dir="$(mktemp -d "$task_root/research/a321-quality/rebuild/evidence/resume-c-XXXXXX")"
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1
set -C
candidate="$task_root/research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl"
sha256sum "$candidate" > "$attempt_dir/before.sha256"
surfaceCheck -checkSelfIntersection -outputThreshold 0 "$candidate" > "$attempt_dir/result.log" 2>&1
sha256sum "$candidate" > "$attempt_dir/after.sha256"
cmp "$attempt_dir/before.sha256" "$attempt_dir/after.sha256"
tail -30 "$attempt_dir/result.log"
```

설치된 v1912 help에 없는 split/write flag를 추정해서 추가하지 않는다. 명시적 no-intersection 결과·End·fatal없음·모델해시를 모두 확인한다. 15개 위치 출력 지도화 방법은 새로 설계해야 하며 위 재검사는 지도 생성 명령이 아니다.

## 14. 문서·출처·라이선스 규칙

읽는 순서: 본 핸드오프 → 현재 상태 → 전체 계획 → M1/M4 → 후보별 원시 증거 → 기존 연구 보고서/실행절차 → 코드.

NASA 자료는 사용자가 지정했고 이전 연구에서 접근·기록했다. 이번에는 방법론 내용을 새로 검증하거나 페이지 최신성을 조사한 것이 아니다. 기존 [출처 원장](evidence/rebuild-roadmap-sources.json), [방법론 기록](evidence/rebuild-roadmap-nasa-method.json)에 연결한다.

- [NASA NPARC V&V tutorial](https://www.grc.nasa.gov/www/wind/valid/tutorial/tutorial.html)
- [CFD analysis process](https://www.grc.nasa.gov/www/wind/valid/tutorial/process.html)
- [Spatial/grid convergence](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html)
- [Blender surface documentation](https://docs.blender.org/manual/en/latest/modeling/surfaces/introduction.html)

형상 생성·표시, mesh verification, solver verification, 실험 validation을 분리한다. 연구 기준70°/1e-10을 NASA가 A321을 승인한 기준으로 표시하지 않는다. 엔진·파일런·장치 틈·OEM 익형을 생략한 연구 shell에서 얻는 향후 항력은 실기 A321 전체 항력으로 확대하지 않는다.

[CONTRIBUTING](../../CONTRIBUTING.md): 기준 완화 금지, 신규 소스 출처/헤더, 수치 코어 변경 별도 승인 계약, `git commit -s`. GPL 구현 소스를 읽거나 복사하지 않는다. OpenFOAM은 외부 CLI, Blender bpy 프로그램은 [기존 별도 outbound 정책](../a321-shell/LICENSE-NOTICE.md)에 따라 GPL-2.0-or-later로 구분한다. 이 분류가 solver 전체 라이선스를 바꾸지 않는다.

새 결과는 새후보·새영수증에 남기고 status Markdown/JSON/HTML을 함께 갱신한다. 실패를 지우지 않고, 이전 테스트·화면을 새실행으로 재사용하지 않으며, 사용자에게 현재 gate·다음조치·미실행 범위를 텍스트 대시보드로 보고한다.

## 15. 다음 세션에 그대로 전달할 지시문

> research/a321-quality/HANDOFF_20261109_KO.md와 EXECUTION_STATUS_KO.md를 읽고 codex/a321-aero-shell-20261105의 핸드오프 커밋에서 이어가세요. R3/R4·R5-A/C·기존 snappy01~11과 raw receipts를 보존하고 critical-assets manifest 해시를 먼저 검증하세요. 현재 C는 자기교차15위치로 M3 FAIL입니다. C 교차 위치 지도와 feature/접합부·극소 삼각형 원인 분리를 우선하고, 새계약/새후보에서 재검사하세요. C native의 R4 복사 메타데이터는 별도 파생본으로 정정하고 exact geometry를 확인하세요. Ego Lite space15를 inventory로 확인해 실제 모델·보고서 화면을 남기세요. M3 전 새 R5 체적 격자, 모든 선행 품질 통과 전 항공기 GPU solver를 실행하지 마세요. lowmach -iters0은 CPU-only가 아닙니다. 코드 최종검토 미종결을 유지하고 증거가 있는 범위만 PASS로 기록하세요. 단계마다 상태 Markdown/JSON/HTML과 한글 커밋·연구 브랜치 push를 남기세요.
