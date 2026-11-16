# R6-a / R6-b 후보 생성 보고 (sonnet-r6-gen, 2026-11-16)

## 결론

- **R6-a(02 규정 그대로의 사각형 분할, attempt02)와 R6-b(02c 기울어진 띠 분할, attempt02) 모두 fuselage는 G3 surfaceCheck와 G4 구간 편차에서 FAIL**, 나머지 3개 구성품(wing, horizontal, vertical)은 모든 게이트 PASS(단, G6 station-kink 비율은 wing·vertical에서 «정의 불가»)이다. M3 PASS 선언은 하지 않는다. 판정은 오케스트레이터 몫이다.
- surfaceCheck: R6-a fuselage 1568건, R6-b fuselage 104건(wing·horizontal·vertical은 둘 다 0건). 위치 분석은 **104건 중 96건이 정확히 y축에 평행한 모서리가 있는 꼭짓점**이다. 이 모서리는 R3 원장의 평평한 배(belly) 자르기(flat clip)와 노즈 캡 중심에서 생긴다. 점을 옮기지 않고 그 모서리를 반대 대각선으로 뒤집은 **복사본**에서는 104건이 8건으로 줄었다(attempt01은 64건이 1건으로).
- G4 편차: fuselage 26.83 mm(한도 25 mm). 최대점은 x = 0.33 m, z = 2.77 m(노즈 아래쪽, 원장 스테이션 2~3 구간)이다. 02b 조건 3에 따라 선형화하지 않고 G4 실패로 보고한다.
- 정션: wing, horizontal, vertical 모두 교선이 닫힌 고리로 나온다(wing·horizontal은 좌우 2개 고리, vertical은 열린 호 2개이지만 끝점이 정확히 만난다). 최소 표면 각 wing 45.0도(R6-b) / 46.2도(R6-a), horizontal 63.8도, vertical 22.5도.
- 시도 횟수: R6-a 2회(attempt01, attempt02), R6-b 2회. 모든 영수증을 남겼다. 최종 후보는 각 태그의 attempt02이다.
- 시험: `test_build_r6.py` 10 passed.

## 후보 파일

| 항목 | 경로 (`research/a321-quality/r6/` 기준) |
|---|---|
| R6-a 최종 | `candidates/r6-a/attempt02/` (STL 4개, `r6-a.blend`, `gate-table.json`, `receipt.json`, `feature-manifest.json`, `sc/`, `junctions/`, `gate/`, `a3-reference.json`) |
| R6-a 1차 | `candidates/r6-a/attempt01/` (영수증 포함, 실패 기록으로 보존) |
| R6-b 최종 | `candidates/r6-b/attempt02/` |
| R6-b 1차 | `candidates/r6-b/attempt01/` |
| 생성기 | `gen/build_r6.py`, `r6_grid.py`, `r6_tess.py`, `r6_sections.py`, `r6_lines.py`, `r6_splines.py`, `r6_kinks.py`, `blender_r6.py`, `run_pipeline.py`, `check_r6.py` |
| 보정 실험 | `gen/calibration/` (`surfacecheck_axis_parallel.py`, `calibration-log.json`, `ledger_flat_clips.py`, `flat-clips*.json`, `edge_orientation.py`, `flip_axis_parallel_experiment.py`, `flip-experiment-r6b-attempt0{1,2}.json`) |
| 그림 | `gen/figures/r6-a-attempt02/` (정사영 3면, 노즈·날개 뿌리·날개 끝·꼬리 와이어프레임). PNG는 git 무시 대상이다. 노출이 과해 흐리게 나왔다(R6-b 그림은 만들지 않았다) |

디스크: `candidates/`가 약 298 MB이다(STL, npz, blend). 커밋 여부는 오케스트레이터가 정한다. 커밋은 하지 않았다.

## 구성품별 게이트 표 (attempt02, 한도는 02a)

| 게이트 | 한도 | R6-a fuselage | R6-b fuselage | wing | horizontal | vertical |
|---|---|---|---|---|---|---|
| 삼각형 수 | - | 350,048 | 350,048 | 385,112 | 145,240 | 117,912 |
| G1 닫힘/경계/성분/오일러 | 0/0/1/2 | PASS | PASS | PASS | PASS | PASS |
| G2 방향·바깥 법선·부피 | 일관, 바깥 | PASS | PASS | PASS | PASS | PASS |
| G3 locator / PyMeshLab | 0 / 0 | 0 / 0 PASS | 0 / 0 PASS | 0 / 0 | 0 / 0 | 0 / 0 |
| **G3 surfaceCheck** | 0 | **1568 FAIL** | **104 FAIL** | 0 | 0 | 0 |
| G4 원장 점 거리 | 1e-5 m | 0 | 0 | 0 | 0 | 0 |
| G4 경계 상자 | 1e-5 m | 0 | 0 | 0 | 0 | 0 |
| **G4 구간 편차** | 25 mm / 10 mm | **26.83 mm FAIL** | **26.83 mm FAIL** | 0.83 mm | 0.80 mm | 1.19 mm |
| G4 부피 상대차 | 1 % | 0.035 % | 0.031 % | 0.003 % | 0.008 % | 0.007 % |
| G5 Q_OF 최소 / p1 | 0.001 / 0.01 | 0.0058 / 0.061 | 0.0058 / 0.060 | 0.024 / 0.114 | 0.054 / 0.140 | 0.0047 / 0.0197 |
| G5 최소각 최소 / p5 | 1.0 / 5.0도 | 1.79 / 9.11 | 1.79 / 9.07 | 2.10 / 6.55 | 2.40 / 6.07 | 1.19 / 5.38 |
| G5 종횡비 최대 / p99 | 100 / 30 | 32.1 / 14.2 | 32.1 / 14.2 | 27.7 / 13.0 | 24.3 / 10.7 | 50.2 / 16.7 |
| G5 인접 면적비 최대 / p99 | 30 / 10 | 12.9 / 3.97 | 12.9 / 3.98 | 22.0 / 2.30 | 17.4 / 2.66 | 25.4 / 2.61 |
| G5 인접 변 길이비 p99 | 3 | 1.62 | 1.65 | 1.10 | 1.17 | 1.33 |
| G5 꼭짓점 차수 최대 | 8 | 8 | 8 | 8 | 8 | 7 |
| G6 비특징 이면각 최대 / p99 | 30 / 10도 | 19.2 / 4.76 | 19.2 / 6.29 | 7.34 / 6.40 | 9.31 / 8.05 | 12.4 / 7.52 |
| G6 스테이션 kink 비율 | 1.5 | 0.35 | 0.43 | 정의 불가 | 1.28 | 정의 불가 |
| G7 새 프로세스 .blend = STL | 동일 | PASS | PASS | PASS | PASS | PASS |

주의:

- **G6 kink 비율 «정의 불가»**: 분모(스테이션이 아닌 곳의 링 방향 평균 회전)가 float32 하한 0.01도 아래(wing 0.0088도, vertical 0.0016도)라서 지표 정의상 비율이 없다. 분자(특징선 제외한 스테이션 모서리 평균)도 wing 0.0087도, vertical 0.0014도로 같은 잡음 수준이다. PASS나 FAIL로 세지 않고 «UNDEF»로 남겼다. 02a 주석 «비율이 정의되지 않으면 A 분포를 쓴다»에 따른 값은 `gate-table.json`의 `kink_detail`에 있다.
- kink 비율 평가에서 **선언한 특징선(캡 경계, 닫힘 띠 경계, kink 행)의 모서리는 A에서 뺐다**. 1차 평가기는 캡 경계를 빼지 않아 wing 등에서 값이 부풀었다. 평가기를 고친 것이지 한도를 건드린 것이 아니다.
- G4 구간 편차 방식: 양방향 20,000점 표본 최대값이다(하우스도르프 거리의 하한).

## fuselage가 FAIL인 이유

### 1. G3 surfaceCheck (R6-a 1568건, R6-b 104건)

보정 실험 결과(`gen/calibration/calibration-log.json`, 원통 R=2 m, float32 STL, OpenFOAM v1912):

| 경우 | surfaceCheck 건수 |
|---|---|
| 정확히 격자 정렬된 원통 32x100 | 2497 |
| 128x300 | 11410 |
| z축으로 0.37 rad 회전 | 98 |
| xyz 회전 | 26 |
| 링마다 반 칸 엇갈림 | 0 |
| 점마다 y 또는 z 방향 잡음(1e-5, 1e-3) | 0 |
| 점마다 x 방향 잡음만 | 2346 ~ 2487 |
| 기울어진 띠 32x100 | 0 |

결론: **트리거는 좌표축에 정확히 평행한 모서리**(float32에서 나머지 두 성분이 정확히 0)이다. 곡률, 삼각형 모양, 평평함 자체가 아니다. 이 모서리가 있는 꼭짓점 주변에서 surfaceCheck가 «자기 교차»를 보고한다. locator와 PyMeshLab은 0이다.

- R6-a: 링과 링 사이 연결선이 축에 평행한 곳이 많아 1568건이다.
- R6-b(02c 기울어진 띠): 그런 띠 25개(attempt01은 22개)만 기울여 링 간 모서리는 사라졌다. 남은 104건의 분석(`candidates/r6-b/attempt02/sc/fuselage-edge-orientation.json`):
  - 104건 중 96건은 가장 가까운 꼭짓점에 **y축에 평행한 모서리**가 있다(나머지 8건은 해당 모서리가 없어 원인 미확인).
  - 위치는 x 4 ~ 7 m 구간에 94건(배 평평한 구간), 노즈 캡 중심(x = 0) 3건 등이다.
  - 메시 전체에서 y 평행 모서리 500개, z 평행 4개, x 평행 0개.
  - 이 모서리들은 **링 안의 모서리**이다. 원장에서 이웃한 두 점의 x와 z가 정확히 같아서(평평한 배 자르기) 링 모서리 자체가 y에 평행하다. 띠를 기울여도 링 모서리는 남는다.
- 진단 실험(복사본, 점 이동 없음): y 평행 모서리 504개 중 500개를 반대 대각선으로 뒤집으면 surfaceCheck가 **104건에서 8건**(attempt01은 64건에서 1건)으로 준다(`gen/calibration/flip-experiment-r6b-attempt0{1,2}.json`). 후보 파일은 건드리지 않았다. 남은 8건과 뒤집지 못한 4개는 노즈 캡 중심 부근으로 추정되나 확인하지 않았다.

따라서 02c의 «링 간 모서리를 기울이기»만으로는 부족하고, 링 모서리(평평한 구간)를 비껴가는 연결 규칙(간선 뒤집기)이 있어야 surfaceCheck 0에 닿을 가능성이 높다. 이는 계약 변경이므로 구현하지 않았다.

### 2. G4 구간 편차 26.83 mm (한도 25 mm)

- 최대점: x = 0.33 m, y = -0.06 m, z = 2.77 m(노즈 아래쪽), `gate/fuselage-deviation-locator.json`.
- 이 위치는 02b가 예상한 구간 1~2, 179~180이 아니라 **원장 스테이션 2~3 구간**(x 0.25 ~ 0.50 m)이다. 스플라인이 선형 보간인 R3 STL보다 바깥쪽(곡률 반경 쪽)으로 부풀어서 생기는 차이이다. 양방향 표본 최대값이며 하우스도르프 거리의 하한이다.
- 선형화하지 않았다(02b 조건 3). 나머지 구간 최대: x 21~21.5 m에서 17 mm, x 23.5 m에서 16.5 mm(배 앞쪽 전이 구간).

## 1차(attempt01)에서 고친 것

| 증상(attempt01) | 원인 | attempt02 조치(계약 방법 안) |
|---|---|---|
| wing/horizontal/vertical 인접 면적비 185 / 115 / 76 | 날개 끝·뿌리 캡의 LE 쪽 가는 삼각형과 캡 경계에 붙은 12 mm 두께 띠 | 끝 행 간격을 캡 삼각형 크기에 맞춰 풀고(`--end-match`, `--end-bias 1.5`), 캡 안쪽 행 수를 3배로(`--cap-density 3`) |
| fuselage 이면각 30.28도 | 원장의 배 단차(x 23.4 -> 23.6 m에서 z 2.37 -> 2.12 m)를 행 간격이 못 따라감 | 크기장에 «격자선 회전각 행당 20도 이하» 기준 추가(`--long-turn 20`, 삼각형 24.7만 -> 35.0만) |
| wing/vertical kink 비율 «정의 불가/부풀림» | 평가기가 캡 경계 모서리를 빼지 않음 | 특징선 마스크로 A에서 제외 |
| vertical 정션 «열린 호 2개» | sbf가 y = 0 대칭면에서 호를 이어 붙이지 않음 | 끝점끼리 간격 0(1 마이크로미터 이내)이라 사실상 닫힌 고리로 판정 |

모든 한도는 그대로 두었다.

## 정션 (A1/A2)

| 구성 | 고리 수 | 닫힘 | 최소 표면 각 (R6-a / R6-b) |
|---|---|---|---|
| wing | 2(좌우) | 닫힘 | 46.2도 / 45.0도 |
| horizontal | 2(좌우) | 닫힘 | 63.8도 / 63.8도 |
| vertical | 호 2개, 끝점 4개가 두 쌍으로 만남(간격 0) | 사실상 1개 고리 | 22.5도 / 22.5도 |

vertical 교선 호의 z 범위는 5.79 ~ 6.13 m로 뿌리 면(z = 5.5)보다 위라서 뿌리 캡은 fuselage 안에 있다.

## 기준 치수(A3, 인쇄값 ±0.1 m)

전부 허용 안: 전장 44.51 m(차이 -1.7e-6), 날개 반 스팬 16.29 m(9e-7), 수평꼬리 스팬 12.45 m(-2e-7), 수직꼬리 끝이 x = 30에서 동체 윗선 위로 5.8703 m(+0.27 mm), 동체 폭 3.95 m, 동체 높이 4.1824 m(+42 mm, 인쇄값 4.14). 날개 끝 샤클릿(총 폭 35.80 m)은 계약 범위 밖이라 모델링하지 않았다.

디스플레이 합집합(manifold3d, 게이트 아님): R6-a attempt02의 4개를 합치면 닫힌 단일 성분 955,586 삼각형, surfaceCheck 388건이다(`candidates/r6-a/attempt02/display-union-check.json`, STL은 확인 후 삭제).

## 부수 발견: R3 fuselage 윗면·배가 정확히 평평한가

`gen/calibration/flat-clips.json`(z 같음 허용 1e-9 m):

- **윗면(crown)**: 182개 스테이션 중 1개(x = 1.24 m, 스테이션 6)만 3점 이상이 같은 z(4.4414 m)이다. y 길이 0.124 m.
- **배(belly)**: 8개 스테이션이 평평하다. 스테이션 18(x = 4.23 m, z = 2.0237 m, y 길이 0.622 m)와 스테이션 19~25(x 4.48 ~ 5.97 m, z = 2.0112 m, y 길이 0.635 ~ 0.663 m).
- 즉 «정확히 평평함»은 배 앞쪽 x 4.2 ~ 6.0 m의 약 0.62 ~ 0.66 m 폭 구간과 노즈 근처 한 스테이션에만 있다. 나머지 스테이션은 평평하지 않다(허용 1e-6, 1e-4 결과도 같은 폴더).
- surfaceCheck 잔여 기록이 x 4 ~ 6 m 구간에 몰리는 이유가 이 평평한 구간이다.

## planform kink 기록

`feature-manifest.json`의 `kinks_detected`:

- wing: 5개(TE 스테이션 58, 62, 136, 140에서 7.8 ~ 8.3도, 중앙 y = 0에서 LE 55.2도). 중앙 값은 좌우 미러 접합점에서 생기는 부호 반전이다.
- horizontal: 1개(y = 0, LE 66.3도, TE 26.7도). 미러 접합점이다.
- vertical: 11개(LE 기울기 변화 -10.6 ~ +25.8도). 스테이션 8->9 부호 반전(+7.3, -7.4도)과 11, 12, 19, 20은 부호가 뒤섞여 **다각형 잡음**일 가능성이 높다. 스테이션 71 ~ 74(+3.7, +6.4, +12.5, +11.6도)는 같은 방향으로 연속해서 꺾여 실제 끝단 굽힘(LE 모서리 둥글림)으로 보인다. 어느 쪽이든 02 규칙대로 2.0도 기준으로 모두 선언했고 해당 스테이션에서 스플라인을 끊었다. 잡음 여부는 판정하지 않았다(미확인).

## 명령과 실측 시간 (attempt02, R6-a)

| 단계 | 명령 | 시간 |
|---|---|---|
| 전체 | `python gen/run_pipeline.py --tag r6-a --attempt attempt02 --tess quad --skip-render --build-args "--end-match --cap-density 3.0 --end-bias 1.5 --long-turn 20"` (R6-b는 `--tess lean`, 태그 `r6-b`) | 약 5 ~ 6분 |
| 생성 | `build_r6.py --aspect-fuselage 3.0 --aspect-wing 1.8 --aspect-vertical 1.0 ...` | 47.9 s |
| Blender 생성·내보내기 / 새 프로세스 확인(G7) | `blender.exe -b --factory-startup --disable-autoexec --python blender_r6.py ... --build / --verify` | 8.8 s / 3.3 s |
| 게이트 4개 병렬(locator, PyMeshLab, 지표) | `uv run checks/r6_gate.py ...` | 103.8 s |
| surfaceCheck fuselage / wing / horizontal / vertical | WSL `run_surfacecheck_gen.sh`(복사본, 새 디렉터리) | 10.9 / 4.8 / 2.1 / 1.8 s |
| surfaceBooleanFeatures + 분석(wing, horizontal, vertical) | WSL `run_junction_gen.sh` + `junction_analysis.py` | 7.6+17.3 / 5.0+16.2 / 4.7+13.4 s |
| 평가 | `uv run gen/check_r6.py` | 18.6 s |
| 보조 | `a3_reference.py`, `locate_deviation.py`(약 28 s), `display_union.py`(약 12 s), `edge_orientation.py`, `flip_axis_parallel_experiment.py`(약 15 s), 렌더(약 10 s) | 위 시간 내 |
| 시험 | `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q test_build_r6.py` | 0.4 s, 10 passed |

입력 SHA256(원장, R3 STL 4개, 계약 02, 02a, 02b, 02c)은 모든 파이프라인 전후 같다(`receipt.json`의 `inputs_unchanged: true`). 작업 브랜치 `feat/a321-r6-blender`, HEAD `57ab99f1`이고 이 작업에서 커밋·브랜치 전환·reset은 하지 않았다. 새 파일은 `candidates/`, `gen/` 아래에만 있다(`git status`에 `?? candidates/`, `?? gen/`).

## 하지 않은 것, 불확실한 것

- M3 PASS를 선언하지 않았다.
- R6-b 그림은 만들지 않았다. R6-a 그림은 노출이 과해 흐리다(와이어프레임 확인에는 충분).
- surfaceCheck 잔여 8건(뒤집기 실험 후)과 R6-b 104건 중 8건(y 평행 모서리가 없는 기록)의 원인은 확인하지 못했다.
- 간선 뒤집기 후보(R6-c)와 fuselage 노즈 편차를 줄이는 방법(예: 노즈 구간 보간 변경)은 계약 변경이라 만들지 않았다.
- vertical 11개 kink의 잡음 여부는 판정하지 않았다.
- 두 번째 attempt에서 `--end-bias 1.5`, `--cap-density 3`, `--long-turn 20`은 시험 빌드를 몇 번 돌려 고른 값이다(`end_bias`는 vertical 최소각 1.0도와 면적비 30 사이를 맞추는 값). 한도에는 영향이 없으나 값 자체는 경험적이다. 면적비 여유는 wing 22, horizontal 17, vertical 25(한도 30)이다.
- `gen/attempts/`(약 5 MB)에는 surfaceCheck·sbf 복사 작업 디렉터리가 남아 있다(개발용 변형 `sc-V1/V2/V3` 포함).
