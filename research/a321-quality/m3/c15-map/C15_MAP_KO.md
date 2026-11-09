# R5-C C15 위치 지도 — M3-a 진단

**결론: surfaceCheck v1912의 15레코드를 모두 좌표·국소 STL 삼각형으로 지도화했다. 독립 비인접 삼각형 검사는 0쌍/0클러스터다. 두 검사 결과의 차이는 미해결이며 M3 FAIL·C 미채택을 유지한다.** 15레코드는 14개의 서로 다른 출력 좌표이고, 1·2번 좌표는 완전히 같은 OBJ 텍스트다. 15개의 고유 결함 또는 확정 교차쌍을 찾았다고 주장하지 않는다.

권위 있는 위치 목록은 [첫 OBJ](surfacecheck-nMM86x/selfInterPoints.obj)다. 새 로컬 복사본을 검사한 [contained 재검사](surfacecheck-qNy1jX/result.log)도 15, `End`, FATAL 없음이며 두 OBJ의 SHA가 동일하다. 두 surfaceCheck 실행 모두 exit 0이지만 형상 합격은 아니다.

| 구분 | 결과 | 근거 |
|---|---|---|
| 입력 C | 305,764 facets; 원 binary STL 순서 0-based index 유지 | [independent-scan.json](independent-scan.json) |
| source STL 전·후 SHA256 | `5466466cfdb9361aea0f20fe5daabbab3bea7835df90887652310ffad7f6cd7b` 동일 | [최초](input-before.json), [첫 재검사](surfacecheck-nMM86x/before.sha256), [후](surfacecheck-nMM86x/after.sha256), [최종 보존 확인](custody-contained-check.log) |
| 독립 broad/narrow phase | rtree AABB 전체 스캔, 비인접 후보 801,534쌍 검사; 발견 0쌍/0클러스터 | [원시 진행 로그](independent-scan.log), JSON의 실제 `narrow_phase_pairs`를 기준으로 확인 |
| 권위 있는 위치 | 15 OBJ vertex rows /14 unique printed coordinates | [c15-locations.json](c15-locations.json) |
| 부품 | 15레코드 모두 fuselage bounds에만 해당 | M1 원장과 원 `reconstruction-r3.json` station/bbox 대조 |
| 인접 정밀 검사 | 후보별 exact Fraction 교차가 공유 정점/변을 넘는 경우 0 | JSON의 `rational_beyond_shared_topology`, `exact_contact_vertices_m` |
| 테스트 | 최초 3 failed(`NotImplementedError`) → 필수3 passed → 확장5 passed | [RED](pytest-red.log), [3 GREEN](pytest-green.log), [확장](pytest-expanded.log), [최종](final-pytest.log) |
| 별도 QA | 5 passed, 순열 216 assertions 통과 | [QA](review-qa.md), [순열 로그](qa-permutations.log) |

## 15레코드 표

모든 행의 부품은 **fuselage**다. 주익·수평/수직미익, LE/TE/tip, wing-body/tail-body junction에 해당한다는 증거는 없다. 좌우 부품 구분은 해당 없음. X는 길이, Y는 횡방향, Z는 수직이며 단위 m이다. M1 원장이 참조하는 source station/bbox 파일 SHA `405aec921c5f492a6841c89102cb0215141a920906baed94298c5c2d3fef15cb`를 현재 파일에서 확인했다.

아래 ID는 **100µm 국소 반경 내 후보 facet**이다. surfaceCheck OBJ는 edge/facet ID를 쓰지 않으므로 실제 checker 교차쌍의 신원은 **UNKNOWN**이다. 두 facet뿐인 A군은 그 인접쌍을 제시할 수 있고, fan/seam은 JSON에 모든 인접 후보쌍을 보존한다. 이를 확인된 비인접 교차쌍으로 승격하지 않았다. 각 pair의 공유 정점 수·정확 접촉 좌표·법선각, 각 facet의 좌표3개·변3개·면적·품질2종은 JSON에 있다.

| # | world (X,Y,Z) m | 국소 STL facet IDs | feature | 최소 Qeq | 변 길이 min–max m | 후보 법선각 min–max ° | 원인 가설 |
|---:|---|---|---|---:|---:|---:|---|
| 1 | (4.22802, 0.206553, 2.02366) | 5388,68601,68606,68608,68611,68618 | section ring seam (추론) | 0.0019818 | 0.0024895–0.62232 | 1.2074E-06–10.456 | C: station/shoulder 정점 fan 접촉 가설 |
| 2 | (4.22802, 0.206553, 2.02366) | 5388,68601,68606,68608,68611,68618 | section ring seam (추론) | 0.0019818 | 0.0024895–0.62232 | 1.2074E-06–10.456 | C: station/shoulder 정점 fan 접촉 가설 |
| 3 | (6.42599, -0.0294316, 1.95089) | 13055,13056 | other / 패치 대각선 | 0.85371 | 0.10073–0.15617 | 0.0099179–0.0099179 | A: 공유 대각선 판정 민감성 가설 |
| 4 | (10.1419, -0.0411171, 1.95124) | 16648,16649 | other / 패치 대각선 | 0.85371 | 0.10073–0.15618 | 0.0098012–0.0098012 | A: 공유 대각선 판정 민감성 가설 |
| 5 | (6.49484, -0.0205902, 6.08937) | 30694,30696 | other / 패치 대각선 | 0.85233 | 0.10162–0.15723 | 0.024342–0.024342 | A: 공유 대각선 판정 민감성 가설 |
| 6 | (6.70952, 1.11022E-16, 6.09) | 30735,30736,30738,94331,94332,94333 | section ring seam (추론) | 0.16556 | 0.0099459–0.15771 | 0–3.5486 | B: 동체 상부 미러 seam 접촉 가설 |
| 7 | (9.95065, -0.0903181, 6.0872) | 32650,32652 | other / 패치 대각선 | 0.16528 | 0.0099459–0.10375 | 0–0 | A: 공유 대각선 판정 민감성 가설 |
| 8 | (10.58, -0.00972425, 6.08971) | 32785,32788 | other / 패치 대각선 | 0.85496 | 0.10163–0.15676 | 0.036508–0.036508 | A: 공유 대각선 판정 민감성 가설 |
| 9 | (1.24673, -0.0620968, 4.44314) | 9908,9911,9912,9915,9916,9919 | section ring seam (추론) | 0.084713 | 0.0030444–0.062309 | 0.22685–4.3848 | C: station/shoulder 정점 fan 접촉 가설 |
| 10 | (18.4059, 0.101541, 1.95308) | 106768,106770,106774,106894,106895,106899,106900 | section ring seam (추론) | 0.04238 | 0.0024872–1.4953 | 0–2.9153 | C: station/shoulder 정점 fan 접촉 가설 |
| 11 | (27.5689, -0.0227856, 1.95069) | 142732,142733 | other / 패치 대각선 | 0.848 | 0.099416–0.15602 | 0.0058564–0.0058564 | A: 공유 대각선 판정 민감성 가설 |
| 12 | (27.6206, -0.0126672, 6.08961) | 161893,161894 | other / 패치 대각선 | 0.85634 | 0.1027–0.15745 | 0.03555–0.03555 | A: 공유 대각선 판정 민감성 가설 |
| 13 | (27.3473, 1.11022E-16, 6.09) | 161815,161835,161836,161837,240462,240467,240473 | section ring seam (추론) | 0.084101 | 0.0049725–0.98987 | 8.5377E-07–3.4752 | B: 동체 상부 미러 seam 접촉 가설 |
| 14 | (27.4766, 1.249E-16, 6.09) | 161839,161882,161883,240475,240476,240494 | section ring seam (추론) | 0.85254 | 0.10163–0.15815 | 0.023427–3.559 | B: 동체 상부 미러 seam 접촉 가설 |
| 15 | (27.5995, 0.0356957, 1.95108) | 219692,219693 | other / 패치 대각선 | 0.17158 | 0.0099468–0.099912 | 8.5377E-07–8.5377E-07 | A: 공유 대각선 판정 민감성 가설 |

Qeq=`4√3 A / Σe²`, Qradius=`2r/R=16A²/(pabc)`이다. `radius_ratio_quality`를 OpenFOAM의 출력 품질과 동일한 구현이라고 주장하지 않는다. 법선각은 `acos(n1·n2)`이며 0°는 같은 방향의 공면이다. 공유 변이 없는 정점 접촉쌍은 통상적인 edge dihedral이 아니므로 후보 facet 법선 사이 각도로 해석한다. 극소각은 double precision 반올림에 민감하다.

기존 전역 최소 품질 `9.70744e-13`(triangle5617)은 surfaceCheck가 보고한 별도 값이다. C15 인근의 품질로 바꿔 쓰지 않았다. C15 대부분의 정상 크기 facet에서 접촉 경고가 발생하므로, 전역 극소품질 하나만으로 15개의 원인을 확정할 수 없다.

## 원인군과 R6 권고 — 가설, 생성하지 않음

| 군 | 레코드 수 | 대상 | 관찰과 가설 | R6에서 변경·검증할 항목 |
|---|---:|---|---|---|
| A: shared diagonal | 8 | 3,4,5,7,8,11,12,15 | 각 위치에 공유 변을 갖는 두 facet. 법선각 약0–0.03651°, exact arithmetic은 공유 변 밖 교차 없음. near-coplanar edge/face 수치 판정 민감성 가설 | station 사이 패치 triangulation을 명시하고 diagonal 선택·곡률 적응 분할을 재설계. 동일 shape에서 대각선만 달리한 대조 후보로 원인 분리. checker 무시·tolerance 확대 금지 |
| B: mirror centerline seam | 3 | 6,13,14 | Y≈0인 동체 상부 접합, 여러 facet이 공유하는 seam. exact audit에서 공유 topology 외 겹침 없음 | 반쪽 Boolean 후 단순 접합 대신 centerline 연속 패치/단일 topology 구성, seam 근처 tangent·normal 및 두께를 사전 계약으로 고정하고 재검사 |
| C: station/shoulder vertex fan | 4 (3개 출력좌표) | 1,2,9,10 | ring/shoulder 근방 정점 fan. 1/2 중복, 국소 저품질 및 긴 변 포함. 공유 정점 edge/face 판정 민감성 가설 | 2%/98% shoulder에 몰린 strip·긴 fan을 국소 재패치, 작은 변·긴 변/가느다란 면 발생을 제어하는 tessellation 설계. 원 station·bbox·체적 제약은 유지 |

인접 후보의 exact Fraction 검사로 해당 후보가 공유 topology 밖으로 겹치지 않는다는 것은 확인했다. 그러나 surfaceCheck 내부 hit identity와 tolerance를 확보하지 않았으므로 **false positive 확정**, **15개 원인 확정**, **C 안전**으로 결론 내리지 않는다. R6에 앞서 원인을 바꾸었을 때 경고가 사라지는 대조 실험과 independent checker 상호 대조가 필요하다. 생성기를 실행해 원인을 toggle한 실험은 이번 범위가 아니다.

R6는 별도 사전 contract로 feature/patch·LE/TE/tip·junction·대칭·곡률·두께·tessellation을 규정해야 한다. 현재 C15는 fuselage 증거만 제공하며 주익/미익 feature 설계 완료의 증거가 아니다. 원 M1 station/bbox 오차 1e-5m, 상대체적1%, 기존 교차 gate를 완화하지 않는다. C cleanup의 6µm 계약을 실패 후 바꾸거나 기존 C를 재명명·채택하지 않는다.

## 방법과 불일치의 경계

1. 바이너리 STL facet 순서를 직접 읽고 float32 좌표를 float64로 올렸다. welding, reordering, repair는 하지 않았다.
2. 3D rtree AABB broad phase 후 정확히 같은 정점/변을 공유하는 pair를 제외했다. plane cut/line interval overlap, coplanar convex clipping을 narrow phase로 사용했다. `EPS=1e-12m`는 첫 독립 스캔 전에 고정했고 15에 맞춰 변경하지 않았다. 이는 부동소수점 기하 predicate이며 전체 스캔이 exact rational proof인 것은 아니다.
3. 교차쌍을 공유 facet 연결성으로 clustering하도록 구현했지만 pair0이므로 cluster0이다. 거리 기준을 바꿔 15를 만들지 않았다.
4. OBJ는6 significant digits이므로 X≈27m의 roundoff가 약50µm일 수 있다. 위치 매칭 반경100µm는 text rounding 대응이며, 교차 허용오차/합격 기준이 아니다. 반경 AABB 후 실제 closest-point 거리로 facet 후보를 거른다. 각 위치의 최근접 원 station index/ΔX도 JSON에 기록했다.
5. 인접 후보는 STL float를 손실 없이 `Fraction`으로 바꿔 plane orientation/segment intersection/copolanar clipping을 검사했다. 이 국소 감사는 전역 비인접 검사와 다른 범위다. 원본 triangle order에 대한 식별자이며 generator component/feature face tag는 없다.

도구 버전은 JSON에 기록했다(NumPy2.5.4, SciPy1.18.1, rtree1.4.1 등). OpenFOAM1912 patch200626, label32/scalar64다. [지도 SVG](c15-map.svg), [PNG](c15-map.png)는 실제 STL 투영을 표시하고, 겹치는 표식을 위쪽 label로 연결했다. 1/2는 같은 좌표에 함께 표기했다.

## 실행 범위 예외·보존

**첫 성공 surfaceCheck 실행은 원본 경로를 직접 지정해 새 diagnostic `.vtp`를 원본 STL 옆에 출력했다.** [당시 로그](surfacecheck-nMM86x/result.log)의 `Wrote triangle-quality`를 보존했다. 이 파일이 새로 생성된 것임을 확인하고 [triangle-quality.vtp](surfacecheck-nMM86x/triangle-quality.vtp)로 작업 출력 안에 옮겼다. 기존 STL·receipt·log는 수정/이름변경/삭제하지 않았다. 그래도 일시적으로 “새 산출물도 전부 map 아래” 제약을 위반했으므로 완전한 scope 준수라고 주장하지 않는다.

현재 [재실행 스크립트](run_surfacecheck.sh)는 `mktemp` attempt 안에 same-SHA `input.stl`을 복사한 뒤 검사한다. [실제 contained 실행](surfacecheck-contained.log)은4.70s checker/8.3329368s wrapper, 동일15/End/noFATAL, 원본 전후해시 동일이며 모든 새 산출물이 attempt 안에 있다. 첫 실행의 위반 이력을 소급 제거하지 않는다.

첫 quoting 오류는 mktemp 전에 실패했다. PS5.1 Tee-Object parameter-set 오류와 초반 UTF8/UTF16 혼합 RED 로그도 보존했다. 실패한 hygiene wrapper가 stderr를 저장하지 못한 기록이 있으며 [native 재확인 로그](hygiene-native.log)로6개 generic-exception finding을 복구했고 typed DiagnosticError로 수정 후 [5파일 위반0](hygiene-final.log)을 확인했다. 원시 실패 로그를 합격 로그로 덮지 않았다.

CONTRIBUTING의 source header를 모든 새 소스에 넣었다. 기존 `rust/PROVENANCE.md` 수정은 사용자 hard constraint에 어긋나므로 새 [PROVENANCE.md](PROVENANCE.md)에 원장과 통합 필요사항을 기록했다. 기존 status 문서/JSON도 수정하지 않았다.

## 명령과 실제 벽시계 시간

핵심 command 원문·UTC 시작·wrapper wall seconds는 각 `.log`의 COMMAND/START_UTC/WALL_SECONDS 필드에 있다. checker의 `/usr/bin/time`과 uv 환경 준비가 포함된 wrapper 시간을 구분한다. 단순 read-only 초기 문서 탐색은 도구 transcript에 남아 있으나 모두 별도 raw log로 캡처되지는 않았다. 따라서 모든 탐색 명령의 로컬 원시 로그가 완전하다는 주장은 하지 않는다.

| 실제 실행 | wall seconds | 근거 |
|---|---:|---|
| source 경로 surfaceCheck -checkSelfIntersection -outputThreshold 100 -writeSets vtk | checker3.38 / wrapper5.7116081 | surfacecheck-run.log / nMM86x/result.log |
| local copy surfaceCheck 같은 flags | checker4.70 / wrapper8.3329368 | surfacecheck-contained.log / qNy1jX/result.log |
| uv --with numpy/scipy/trimesh/rtree python -B locate_intersections.py INPUT --output independent-scan.json | script139.2867657 / wrapper287.7019649 | independent-scan.json/.log |
| local inspection 첫 실행 / neutral metric 최종 실행 | wrapper52.0650265 /35.2640922 | local-inspection.log / local-inspection-neutral.log |
| 지도 첫 assembly / exact / 최종 | wrapper146.9303761 /72.1356021 /69.6599349 | assemble-map.log / assemble-map-exact.log / assemble-map-final.log |
| pytest 필수3 RED / GREEN / 확장5 | wrapper119.2717894 /18.8291919 /56.020406 | pytest-red/green/expanded.log |
| pytest 별도 QA5 / 순열216 / 최종5 | wrapper60.6685054 /27.3970712 /15.8280395 | qa-review-tests.log / qa-permutations.log / final-pytest.log |
| ruff repo rules 검사 | wrapper4.8856653, all checks passed | final-code-checks.log |
| strict skill hygiene5파일 | wrapper1.8657636, no violations | hygiene-final.log |

재현 명령은 해당 output이 존재하면 덮어쓰지 않고 거부된다. 새 output/attempt를 사용해야 한다. `python -B`, pytest `-p no:cacheprovider`로 기존 checkout에 cache 파일을 만들지 않았다. 현재 모든 로그는50MB 미만이고, logger는45MiB 초과에서 출력을 제한한 뒤 bounded tail을 보존한다. source 모델 복사본/VTP는 로그가 아니다.

- [assemble-map.log](assemble-map.log), wall `146.9303761`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with matplotlib --with pydantic python -B research/a321-quality/m3/c15-map/assemble_map.py
```
- [assemble-map-exact.log](assemble-map-exact.log), wall `72.1356021`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with matplotlib --with pydantic python -B research/a321-quality/m3/c15-map/assemble_map.py
```
- [assemble-map-final.log](assemble-map-final.log), wall `69.6599349`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with matplotlib --with pydantic python -B research/a321-quality/m3/c15-map/assemble_map.py
```
- [custody-contained-check.log](custody-contained-check.log), wall `3.4986096`s
```text
$taskBefore=Get-Content research/a321-quality/m3/c15-map/surfacecheck-nMM86x/selfInterPoints.obj -Raw; $taskAfter=Get-Content research/a321-quality/m3/c15-map/surfacecheck-qNy1jX/selfInterPoints.obj -Raw; if($taskBefore -cne $taskAfter){throw "OBJ differs"}; Get-FileHash research/a321-quality/m3/c15-map/surfacecheck-nMM86x/selfInterPoints.obj,research/a321-quality/m3/c15-map/surfacecheck-qNy1jX/selfInterPoints.obj -Algorithm SHA256 | ConvertTo-Json; Get-FileHash research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl,research/a321-quality/models/A321_AIRFRAME_REBUILD_R5_C.stl -Algorithm SHA256 | ConvertTo-Json; git diff --name-only; git status --short --branch
```
- [final-code-checks.log](final-code-checks.log), wall `4.8856653`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with ruff ruff check research/a321-quality/m3/c15-map --output-format concise
```
- [final-pytest.log](final-pytest.log), wall `15.8280395`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with pytest python -B -m pytest -p no:cacheprovider research/a321-quality/m3/c15-map/test_locate_intersections.py -q
```
- [final-ruff.log](final-ruff.log), wall `3.2754228`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with ruff ruff check research/a321-quality/m3/c15-map --output-format concise
```
- [hygiene-direct.log](hygiene-direct.log), wall `5.5693282`s
```text
& C:/Python/64/Python31313/python.exe -B C:/Users/parkc/.codex/skills/programming/scripts/python/check-no-excuse-rules.py research/a321-quality/m3/c15-map/locate_intersections.py research/a321-quality/m3/c15-map/inspect_locations.py research/a321-quality/m3/c15-map/assemble_map.py research/a321-quality/m3/c15-map/exact_contacts.py research/a321-quality/m3/c15-map/test_locate_intersections.py
```
- [hygiene-final.log](hygiene-final.log), wall `1.8657636`s
```text
& C:/Python/64/Python31313/python.exe -B C:/Users/parkc/.codex/skills/programming/scripts/python/check-no-excuse-rules.py research/a321-quality/m3/c15-map/locate_intersections.py research/a321-quality/m3/c15-map/inspect_locations.py research/a321-quality/m3/c15-map/assemble_map.py research/a321-quality/m3/c15-map/exact_contacts.py research/a321-quality/m3/c15-map/test_locate_intersections.py
```
- [independent-locator-checks.log](independent-locator-checks.log), wall `31.1193224`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with pytest --with ruff python -B C:/Users/parkc/.codex/skills/programming/scripts/python/check-no-excuse-rules.py research/a321-quality/m3/c15-map/locate_intersections.py research/a321-quality/m3/c15-map/inspect_locations.py research/a321-quality/m3/c15-map/test_locate_intersections.py
```
- [independent-scan.log](independent-scan.log), wall `287.7019649`s
```text
uv run --with numpy --with scipy --with trimesh --with rtree python -B research/a321-quality/m3/c15-map/locate_intersections.py research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl --output research/a321-quality/m3/c15-map/independent-scan.json
```
- [input-final.log](input-final.log), wall `3.5671369`s
```text
Get-FileHash research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl,research/a321-quality/models/A321_AIRFRAME_REBUILD_R5_C.stl -Algorithm SHA256 | ConvertTo-Json; git diff --exit-code; git branch --show-current; git ls-files --others --exclude-standard | Where-Object { $_ -notlike "research/a321-quality/m3/c15-map/*" }
```
- [local-inspection.log](local-inspection.log), wall `52.0650265`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree python -B research/a321-quality/m3/c15-map/inspect_locations.py research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl research/a321-quality/m3/c15-map/surfacecheck-nMM86x/selfInterPoints.obj research/a321-quality/m3/c15-map/local-inspection.json
```
- [local-inspection-neutral.log](local-inspection-neutral.log), wall `35.2640922`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree python -B research/a321-quality/m3/c15-map/inspect_locations.py research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl research/a321-quality/m3/c15-map/surfacecheck-nMM86x/selfInterPoints.obj research/a321-quality/m3/c15-map/local-inspection.json
```
- [pytest-expanded.log](pytest-expanded.log), wall `56.020406`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with pytest python -B -m pytest -p no:cacheprovider research/a321-quality/m3/c15-map/test_locate_intersections.py -q
```
- [pytest-green.log](pytest-green.log), wall `18.8291919`s
```text
uv run --with numpy --with scipy --with trimesh --with rtree --with pytest python -B -m pytest -p no:cacheprovider research/a321-quality/m3/c15-map/test_locate_intersections.py -q
```
- [pytest-red.log](pytest-red.log), wall `119.2717894`s
```text
uv run --with numpy --with scipy --with trimesh --with rtree --with pytest python -B -m pytest -p no:cacheprovider research/a321-quality/m3/c15-map/test_locate_intersections.py -q
```
- [python-checks.log](python-checks.log), wall `35.1632971`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with ruff python -B C:/Users/parkc/.codex/skills/programming/scripts/python/check-no-excuse-rules.py research/a321-quality/m3/c15-map/locate_intersections.py research/a321-quality/m3/c15-map/inspect_locations.py research/a321-quality/m3/c15-map/test_locate_intersections.py
```
- [python-loc-count.log](python-loc-count.log), wall `1.1322179`s
```text
Get-ChildItem research/a321-quality/m3/c15-map/*.py | ForEach-Object { $taskLoc=(Get-Content $_.FullName | Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" }).Count; "$($_.Name) $taskLoc pure LOC" }
```
- [qa-permutations.log](qa-permutations.log), wall `27.3970712`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with pytest python -B -c 'import sys
from itertools import permutations
import numpy as np
sys.path.insert(0, ''research/a321-quality/m3/c15-map'')
from locate_intersections import intersection_points
from exact_contacts import audit_contact
a = np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]])
cases = [(''crossing'', np.array([[.5,.5,-1.],[.5,.5,1.],[1.,1.,0.]]), True), (''coplanar_overlap'', np.array([[.25,.25,0.],[1.,.25,0.],[.25,1.,0.]]), True), (''parallel_disjoint'', a + [0.,0.,1.], False)]
checks = 0
for name, b, expected in cases:
    for p in permutations(range(3)):
        for q in permutations(range(3)):
            aa, bb = a[list(p)], b[list(q)]
            assert bool(len(intersection_points(aa,bb))) == expected, (name,p,q)
            assert audit_contact(aa,bb)[0] == expected, (name,p,q)
            checks += 2
print(f''PASS: {checks} checks; 3 cases x 36 vertex permutation pairs x 2 algorithms'')'
```
- [qa-review-tests.log](qa-review-tests.log), wall `60.6685054`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree --with pytest python -B -m pytest -p no:cacheprovider research/a321-quality/m3/c15-map/test_locate_intersections.py -q
```
- [report-check.log](report-check.log), wall `1.2848755`s
```text
$taskReport=Get-Content research/a321-quality/m3/c15-map/C15_MAP_KO.md -Raw -Encoding utf8; if($taskReport.Contains("__ROWS__") -or $taskReport.Contains("__COMMANDS__")){throw "Unexpanded report"}; $taskData=Get-Content research/a321-quality/m3/c15-map/c15-locations.json -Raw -Encoding utf8 | ConvertFrom-Json; $taskScan=Get-Content research/a321-quality/m3/c15-map/independent-scan.json -Raw -Encoding utf8 | ConvertFrom-Json; "Records=$($taskData.locations.Count), distinct=$($taskData.unique_printed_coordinates), narrow=$($taskScan.narrow_phase_pairs)"; Get-ChildItem research/a321-quality/m3/c15-map -Recurse -Filter *.log | Sort-Object Length -Descending | Select-Object -First 3 Name,Length | Format-Table; Get-Content research/a321-quality/m3/c15-map/C15_MAP_KO.md -Encoding utf8 -TotalCount 50
```
- [ruff-fix-new-files.log](ruff-fix-new-files.log), wall `10.4941596`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with ruff ruff check research/a321-quality/m3/c15-map --fix --output-format concise
```
- [source-station-read.log](source-station-read.log), wall `1.3423569`s
```text
$taskSource=Get-Content research/a321-integration/evidence/reconstruction-r3.json -Raw | ConvertFrom-Json; $taskSource.parts | Select-Object name,axis,bounds_m | ConvertTo-Json -Depth 4; $taskSource.parts[0].stations_m | Where-Object { ($_ -ge 1 -and $_ -le 1.5) -or ($_ -ge 18 -and $_ -le 18.7) -or ($_ -ge 27 -and $_ -le 28) }
```
- [surfacecheck-contained.log](surfacecheck-contained.log), wall `8.3329368`s
```text
wsl bash research/a321-quality/m3/c15-map/run_surfacecheck.sh
```
- [surfacecheck-run.log](surfacecheck-run.log), wall `5.7116081`s
```text
wsl bash research/a321-quality/m3/c15-map/run_surfacecheck.sh
```
- [uv-diagnostic.log](uv-diagnostic.log), wall `33.429695`s
```text
& C:/Users/parkc/.local/bin/uv.exe run --with numpy --with scipy --with trimesh --with rtree python -B -c "import sys; print(sys.executable, flush=True); import numpy; print(numpy.__version__, flush=True); import scipy; print(scipy.__version__, flush=True); import rtree; print(rtree.__version__, flush=True)"
```
- [write-report.log](write-report.log), wall `1.1797854`s
```text
& research/a321-quality/m3/c15-map/write_report.ps1
```
- [write-report-utf8.log](write-report-utf8.log), wall `2.2354612`s
```text
& research/a321-quality/m3/c15-map/write_report.ps1
```

## 하지 않은 일·남은 불확실성

- R6 형상 생성/repair, Blender, mesher, CFD solver, GPU를 실행하지 않았다. `ofgpu-lowmach`도 호출하지 않았다.
- C를 채택하거나 M3 PASS/engineering acceptance를 선언하지 않았다. EXECUTION_STATUS_KO.md/execution-status.json/기존 모델·receipt·원시로그를 편집하지 않았다.
- 권위 있는15 hit의 edge/facet ID, checker 내부 tolerance, 원인 toggle 대조 실험은 확보하지 않았다. 실제 교차 pair는 UNKNOWN이며 인접 후보 pair의 국소 근거만 제공한다.
- 원 generator의 feature tag·OEM 형상/공력 검증·주익/미익 전체 설계 검증은 하지 않았다. 기하군 A8/B3/C4는 잠정 진단 분류다.
- 전역 FP scan 및 국소 exact audit의 범위 밖인 전체 인접 pair 감사, 대칭·곡률·두께 재설계/품질 최적화는 미실행이다.

5개 review lane 중 코드·focused QA·현재 스크립트 안전·계약일관성에는 차단 결함이 없었으나, goal reviewer는 첫 diagnostic out-of-directory write를 FAIL로 기록했다. 이 위반을 contained 재실행으로 소급 PASS 처리하지 않는다. 리뷰·green tests는 M3 인수와 별개다.
