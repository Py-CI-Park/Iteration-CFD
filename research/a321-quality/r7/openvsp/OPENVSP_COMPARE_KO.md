# R7 독립 OpenVSP A321 형상 경로 대조 (sonnet-r7-openvsp)

작성: worker sonnet-r7-openvsp (Claude Sonnet, 일반 속도), 2026-11-16. 형상만 다뤘다. VSPAERO, GUI, 메셔, 솔버, GPU는 쓰지 않았다. 커밋하지 않았다. 이 문서는 연구용 대조이며 OEM 공학 검증 주장이 아니다.

## 결론

OpenVSP는 부품을 레고처럼 정확히 끼워 닫힌 합집합을 2초에 만들지만, 이음새에 접착제 자국(슬리버 삼각형)이 남고 곧은 동체 몸통에서 surfaceCheck가 기록을 낸다. 아래는 같은 말을 숫자로 쓴 것이다.

1. **닫힌 합집합을 바로 얻는다.** CompGeom 합집합 73,944 삼각형, 경계 변 0, 비다양체 변 0, 성분 1, 오일러 2, 감김 일치, 법선 바깥, 부피 514.37 m3(R3 합집합 504.86). 독립 locator 0쌍, PyMeshLab 0면. CompGeom 벽시계 2.1 s.
2. **합집합은 계약 게이트를 통과하지 못한다.** surfaceCheck 자기교차 **465곳(G3 실패)**, G5 품질 9개 행 중 8개 실패(Q_OF 최소 5.8e-6, 최소 각 0.0016도, 종횡비 최대 35,790, 인접 면적비 최대 2,531), 정점 차수 최대 64(동체 끝 극점, 한계 8)도 실패. 나쁜 삼각형(Q<0.01) 414개 중 290개가 접합선 5 cm 안에 있다. 접합 슬리버는 CompGeom 절단에서 생기며, 시험한 조절 수단(테셀레이션 배율)으로는 없어지지 않는다(CompGeom의 다른 옵션은 시험하지 않았다).
3. **surfaceCheck 기록은 전부 곧은 몸통에 있고 접합 부품 표면에서 멀다.** 동체 단독 858곳, 합집합 465곳이 모두 x 7.2–29.8 m의 일정 단면 구간이다. 합집합 465점은 날개·수평미익·수직미익 표면에서 모두 0.138 m 이상(중앙값 3.1 m) 떨어져 있다(날개 접합 x 17–23도 몸통 구간 안이라 거리로 따로 확인했다). 테셀레이션을 0.5배/1배/2배로 바꾸면 125/465/2,646곳으로 늘어난다. 독립 locator와 PyMeshLab은 모두 0이다. 계약 03 step_0 통(barrel) 게이트와 직접 관련된 관찰이다: 정확한 타원 원통(축 평행 링)은 OpenVSP 삼각분할에서도 surfaceCheck가 0이 아니었다. 원인(축 평행 변 가설)은 이 작업으로 증명하지 않았다. 규칙대로 G3 실패로 적고 거짓 양성이라고 부르지 않는다.
4. **날개·수평미익·수직미익은 같은 모델이다.** R3 단면 18/9/14개를 OpenVSP 파일 익형으로 넣었고, 부품 단독 조밀 양방향 편차는 R6-c 대비 날개 **1.73 mm**, 수평미익 **1.58 mm**, 수직미익 **4.57 mm**(한계 10 mm 이내). 부피는 R3와 0.04 % 이내다. 부품 단독 자기교차는 세 검사기 모두 0이다.
5. **동체는 인쇄 치수만으로 만들면 R3와 크게 다르다.** 길이 44.51, 폭 3.95, 높이 4.14는 정확히 재현하지만, 조밀 편차는 R3 대비 **최대 491.7 mm**(꼬리 아래쪽, x 36–44 m)이고 코(x<4 m)는 306 mm, 몸통 아래쪽 x 20–24 m 구간은 188 mm다. 코·꼬리는 내가 정한 타원체 규칙(CHOICE)의 결과이지 OpenVSP의 한계가 아니다. 몸통 아래 188 mm는 R3 쪽 국소 특징이다(원인 미확정, §4). 몸통(x 8–29 m)은 중앙값 1.1 mm, 최대 8–9 mm로 R3와 맞는다. R7 동체의 평가는 이 숫자를 쓰지 않는다.
6. **동체 단독 품질은 R3와 R6-c보다 낫다(극점 제외).** G5 Q_OF 최소 0.105, 최소 각 3.9도, 종횡비 최대 14.7, 인접 면적비 최대 2.6. 단 정점 차수가 64(코·꼬리 끝)라 G5 차수 행은 실패한다.
7. **대칭은 1e-6 m 이내가 아니다.** 합집합의 표면 거울 편차 최대 40 µm(480개 표본이 1e-6 초과), 정점 거울 최대 3.9 µm(정점의 99.78 %가 1e-6 이내; 최악 정점은 수직미익 끝 x 43.54, z 11.72이고 3.9 µm는 x≥32 m의 float32 STL 한 눈금 3.8 µm와 같다). 반쪽(half) CompGeom 메시는 면적×2가 전체와 5e-7 m2 이내로 같다.
8. **함정 하나를 찾아 고쳤다.** OpenVSP 기본값 `CorrectAirfoilthicknessFlag = 1`이면 뿌리 단면이 1/cos(상반각)만큼 두꺼워진다(날개 뿌리 +2.67 mm, 수평미익 +5.59 mm; `root-thickness-check.json`). 0으로 두면 R3 링과 두께 0.32 mm 이내, 시위 0.5 mm 이내로 맞는다(날개·수평·수직 각 3개 스테이션). 아래 모든 결과는 0 설정이다(첫 실행 결과는 폐기했다). 또 동체 XSec 연속성 C2는 단면 간격이 고르지 않으면 형상이 진동해(몸통 반폭 1.34–1.98 m로 출렁, x가 u에 대해 단조가 아님; `fuselage-continuity-check.json`) 쓸 수 없고 C1로 두었다(C0, C1은 1.975 m 일정).

## 1. 모델과 방법

| 부품 | OpenVSP 구성 | 출처 |
|---|---|---|
| 동체 | `FUSELAGE`, XSec 29개(끝 2개는 점), 타원 단면, 연속성 C1 | 인쇄 치수(길이·폭·높이) + R3 스테이션 extent(코 끝 z 3.458, 꼬리 끝 z 5.112, 몸통 x 7.2–29.8, 몸통 중심 z 4.02) + 내가 정한 규칙: 코 `(1-(1-ξ)^2)^(1/2)`, 꼬리 `(1-η^2)^(1/2)`, 중심선 포물선, 스테이션 간격 `(i/N)^1.6`로 등급 |
| 주익 | `WING`, 섹션 18개, 파일 익형 `.af`, 대칭(XZ), 뿌리 캡 없음(합집합) 또는 +y 반쪽에 평면 캡(부품) | R3 원장 링에서 코드 프레임 익형·앞전·시위를 뽑아 0.5 mm 이내로 재현하는 부분집합 |
| 수평미익 | `WING`, 섹션 9개, 같은 방식 | R3 원장 |
| 수직미익 | `WING` X 회전 90도, 섹션 14개, 뿌리 z=5.5 평면 캡 | R3 원장 |

- 모든 파라미터와 출처 꼬리표는 `a321_params.py`와 `build-union.json`에 있다. 섹션 평면은 R3처럼 스테이션 축에 수직으로 유지했다(`RotateAirfoilMatchDideralFlag=0`, `CorrectAirfoilthicknessFlag=0`). 섹션 앞전 위치는 읽어서 확인했고(초기 시험 18개 섹션 오차 4e-11 m), 스테이션 선택 기준은 0.5 mm다. 이 0.5 mm는 **선택 기준**이지 OpenVSP 곡면의 성질이 아니다. 실제 성질은 아래 조밀 편차다.
- **독립성.** R7 동체 측정과 출력은 읽지 않았다(`r7/measure/` 접근 없음). 작업 중 변경 파일을 찾는 `find`가 다른 worker의 `.worktmp/r7-trace/` 아래 파일 이름을 출력했다. 이름만 보았고 열지 않았다. 다만 동체 모양 규칙을 정하기 전에 R3 동체의 스테이션별 반폭·높이 요약 약 25행을 보았다. 따라서 동체는 R7로부터 독립이지 R3로부터 독립은 아니다. 규칙은 조정하지 않은 단순 형태(타원체)다.
- 합집합은 `ComputeCompGeom(SET_ALL)`의 트림된 메시, 부품은 부품마다 따로 CompGeom. STL은 OpenVSP가 ASCII로 쓰고 float32 이진으로 바꿔 게이트에 넣었다(`stl_tools.py`).

## 2. 게이트 결과

한계는 02a를 그대로 썼다. G6(특징선 제외 이면각, 스테이션 꺾임)은 OpenVSP 쪽에 선언된 특징선과 스테이션 장부가 없어 날개·꼬리·합집합에는 **판정하지 않았다**(원시 이면각은 `openvsp-compare.json`의 `smoothness_raw`; 날개 끝·뒷전이 날카로워 특징선 없는 최대 이면각은 165–171도). 특징선이 없는 동체만 의미가 있다: 전체 변 이면각 최대 **30.36도(한계 30도, 0.36도 초과로 실패; 30도 초과 변 10개)**, p99 **9.50도(한계 10도, 통과)**. 초과 변은 코·꼬리 끝 부채 근처로 보이나 위치는 확인하지 않았다. G4(R3 충실도)는 동체에 쓰지 않는다(계약 03). 부품 날개·수평미익은 +y 반쪽이며 평면 캡 삼각형이 품질 통계에 들어 있다. 판정은 한계 대비 통과/실패이며, R3 열과 R6-c 열은 같은 02a 지표의 측정값이다(R6-c 날개·수평미익 부피는 전폭이라 OpenVSP 반쪽의 2배).

**합집합 (OpenVSP CompGeom 대 R3 합집합)**

| 지표 | 한계 | OpenVSP | R3 합집합 | - | OpenVSP 판정 |
|---|---|---|---|---|---|
| G3 locator pairs | 0 | 0 | 0 | - | 통과 |
| G3 PyMeshLab selected faces | 0 | 0 | 6 | - | 통과 |
| G3 surfaceCheck locations | 0 | 465 | 72 | - | 실패 |
| G5 Q_OF min | >= 0.001 | 5.755e-06 | 1.589e-12 | - | 실패 |
| G5 Q_OF p1 | >= 0.01 | 0.01592 | 0.004912 | - | 통과 |
| G5 min angle min (deg) | >= 1.0 | 0.001601 | 0.002787 | - | 실패 |
| G5 min angle p5 (deg) | >= 5.0 | 3.884 | 3.307 | - | 실패 |
| G5 aspect max | <= 100.0 | 3.579e+04 | 2.866e+04 | - | 실패 |
| G5 aspect p99 | <= 30.0 | 32.32 | 88.87 | - | 실패 |
| G5 adjacent area ratio max | <= 30.0 | 2531 | 3.159e+04 | - | 실패 |
| G5 adjacent area ratio p99 | <= 10.0 | 13.87 | 13.77 | - | 실패 |
| G5 adjacent longest-edge ratio p99 | <= 3.0 | 4.124 | 2.891 | - | 실패 |
| G5 max vertex valence | <= 8 | 64 | - | - | 실패 |

**부품 동체. 열: OpenVSP, R3 부품, R6-c 부품**

| 지표 | 한계 | OpenVSP | R3 | R6-c | OpenVSP 판정 |
|---|---|---|---|---|---|
| G3 locator pairs | 0 | 0 | 0 | 0 | 통과 |
| G3 PyMeshLab selected faces | 0 | 0 | 6 | 0 | 통과 |
| G3 surfaceCheck locations | 0 | 858 | 255 | 48 | 실패 |
| G5 Q_OF min | >= 0.001 | 0.1049 | 0.0008016 | 0.001323 | 통과 |
| G5 Q_OF p1 | >= 0.01 | 0.1516 | 0.00803 | 0.05677 | 통과 |
| G5 min angle min (deg) | >= 1.0 | 3.927 | 0.03412 | 1.789 | 통과 |
| G5 min angle p5 (deg) | >= 5.0 | 14.16 | 5.428 | 9.038 | 통과 |
| G5 aspect max | <= 100.0 | 14.67 | 1679 | 32.05 | 통과 |
| G5 aspect p99 | <= 30.0 | 10.16 | 30.03 | 14.63 | 통과 |
| G5 adjacent area ratio max | <= 30.0 | 2.619 | 80.88 | 12.95 | 통과 |
| G5 adjacent area ratio p99 | <= 10.0 | 1.509 | 33.32 | 3.976 | 통과 |
| G5 adjacent longest-edge ratio p99 | <= 3.0 | 1.339 | 2.147 | 1.665 | 통과 |
| G5 max vertex valence | <= 8 | 64 | - | 8 | 실패 |

**부품 날개(+y 반쪽). 열: OpenVSP, R3 부품, R6-c 부품**

| 지표 | 한계 | OpenVSP | R3 | R6-c | OpenVSP 판정 |
|---|---|---|---|---|---|
| G3 locator pairs | 0 | 0 | 0 | 0 | 통과 |
| G3 PyMeshLab selected faces | 0 | 0 | 0 | 0 | 통과 |
| G3 surfaceCheck locations | 0 | 0 | 0 | 0 | 통과 |
| G5 Q_OF min | >= 0.001 | 0.02488 | 3.956e-06 | 0.001019 | 통과 |
| G5 Q_OF p1 | >= 0.01 | 0.05605 | 0.01031 | 0.1077 | 통과 |
| G5 min angle min (deg) | >= 1.0 | 1.489 | 0.008936 | 2.101 | 통과 |
| G5 min angle p5 (deg) | >= 5.0 | 4.089 | 2.85 | 6.541 | 실패 |
| G5 aspect max | <= 100.0 | 38.63 | 6420 | 28.82 | 통과 |
| G5 aspect p99 | <= 30.0 | 25.12 | 104.3 | 13.14 | 통과 |
| G5 adjacent area ratio max | <= 30.0 | 351.2 | 18.54 | 9.754 | 실패 |
| G5 adjacent area ratio p99 | <= 10.0 | 4 | 3.132 | 2.302 | 통과 |
| G5 adjacent longest-edge ratio p99 | <= 3.0 | 3.243 | 2.523 | 1.099 | 실패 |
| G5 max vertex valence | <= 8 | 8 | - | 8 | 통과 |

**부품 수평미익(+y 반쪽). 열: OpenVSP, R3 부품, R6-c 부품**

| 지표 | 한계 | OpenVSP | R3 | R6-c | OpenVSP 판정 |
|---|---|---|---|---|---|
| G3 locator pairs | 0 | 0 | 0 | 0 | 통과 |
| G3 PyMeshLab selected faces | 0 | 0 | 0 | 0 | 통과 |
| G3 surfaceCheck locations | 0 | 0 | 0 | 0 | 통과 |
| G5 Q_OF min | >= 0.001 | 0.03132 | 4.385e-06 | 0.001083 | 통과 |
| G5 Q_OF p1 | >= 0.01 | 0.04698 | 0.003303 | 0.09056 | 통과 |
| G5 min angle min (deg) | >= 1.0 | 1.411 | 0.01355 | 2.4 | 통과 |
| G5 min angle p5 (deg) | >= 5.0 | 3.385 | 3.996 | 6.05 | 실패 |
| G5 aspect max | <= 100.0 | 40.95 | 4237 | 28.25 | 통과 |
| G5 aspect p99 | <= 30.0 | 27.72 | 69.59 | 11.65 | 통과 |
| G5 adjacent area ratio max | <= 30.0 | 43.92 | 16.13 | 8.658 | 실패 |
| G5 adjacent area ratio p99 | <= 10.0 | 12.1 | 7.802 | 2.66 | 실패 |
| G5 adjacent longest-edge ratio p99 | <= 3.0 | 5.468 | 2.768 | 1.18 | 실패 |
| G5 max vertex valence | <= 8 | 8 | - | 8 | 통과 |

**부품 수직미익. 열: OpenVSP, R3 부품, R6-c 부품**

| 지표 | 한계 | OpenVSP | R3 | R6-c | OpenVSP 판정 |
|---|---|---|---|---|---|
| G3 locator pairs | 0 | 0 | 0 | 0 | 통과 |
| G3 PyMeshLab selected faces | 0 | 0 | 0 | 0 | 통과 |
| G3 surfaceCheck locations | 0 | 0 | 0 | 0 | 통과 |
| G5 Q_OF min | >= 0.001 | 0.009603 | 1.599e-06 | 0.001066 | 통과 |
| G5 Q_OF p1 | >= 0.01 | 0.01151 | 0.002745 | 0.01735 | 통과 |
| G5 min angle min (deg) | >= 1.0 | 0.6326 | 0.009664 | 1.186 | 실패 |
| G5 min angle p5 (deg) | >= 5.0 | 3.504 | 4.431 | 5.377 | 실패 |
| G5 aspect max | <= 100.0 | 90.97 | 5941 | 50.23 | 통과 |
| G5 aspect p99 | <= 30.0 | 38.56 | 63.77 | 16.74 | 실패 |
| G5 adjacent area ratio max | <= 30.0 | 49 | 27.74 | 18.4 | 실패 |
| G5 adjacent area ratio p99 | <= 10.0 | 19.75 | 2.531 | 2.606 | 실패 |
| G5 adjacent longest-edge ratio p99 | <= 3.0 | 4.756 | 1.986 | 1.384 | 실패 |
| G5 max vertex valence | <= 8 | 8 | - | 8 | 통과 |

G1(폐합)과 G2(방향)는 합집합과 4개 부품 모두 통과했다: 경계 변 0, 비다양체 변 0, 성분 1, 오일러 2, 감김 일치, 법선 바깥, 부피 양수. 부품 부피는 동체 476.35, 날개 반쪽 21.314, 수평미익 반쪽 2.923, 수직미익 5.184 m3다.

요약(실패 행 수, G3와 G5의 13행 중): 합집합 9, 동체 2(surfaceCheck, 차수), 날개 3, 수평미익 4, 수직미익 6. R6-c는 날개·수평미익·수직미익이 G5에서 전부 통과했다. OpenVSP 날개 계열은 Q_OF 최소가 더 좋지만(날개 0.0249 대 0.00102) 종횡비 최대, 최소 각 하위 5 %, 인접 면적비, 인접 변 길이비는 R6-c보다 나쁘다.

## 3. 치수

| 항목 | 인쇄값 | OpenVSP | R3 | R6-c |
|---|---|---|---|---|
| length_m | 44.51 | 44.51 | 44.51 | 44.51 |
| max_width_m | 3.95 | 3.95 | 3.95 | 3.95 |
| max_height_m | 4.14 | 4.14 | 4.14 | 4.14 |
| wing_half_span_m | 16.29 | 16.29 | 16.29 | 16.29 |
| horizontal_half_span_m | 6.225 | 6.225 | 6.225 | 6.225 |
| fin_tip_minus_fuselage_top_m | 5.87 | 5.87 | 5.87 | 5.87 |
| fin_tip_minus_fuselage_lowest_m | 10.01 | 10.01 | 10.01 | 10.01 |
| wing_root_chord_y2.2_m | 6.07 | 6.09915 | 6.09912 | 6.09912 |
| wing_tip_chord_m | 1.64 | 1.64079 | 1.64079 | 1.64079 |
| horizontal_root_chord_y1.475_m | 3.31 | 3.23645 | 3.23645 | 3.23645 |
| horizontal_tip_chord_m | 1.24 | 1.24046 | 1.24046 | 1.24046 |
| fuselage_bbox_z_extent_m_informational | - | 4.14294 | 4.18236 | 4.18236 |
| fuselage_bbox_zmax_m_informational | - | 6.09294 | 6.13236 | 6.13236 |
| 부피 fuselage m3 | - | 476.352 | 466.313 | 466.457 |
| 부피 wing m3 | - | 21.3136 | 21.3189 | 42.6392 |
| 부피 horizontal m3 | - | 2.92291 | 2.92341 | 5.84728 |
| 부피 vertical m3 | - | 5.18443 | 5.18622 | 5.18656 |
| 면적 fuselage m2 | - | 508.977 | 500.651 | 500.504 |
| 면적 wing m2 | - | 133.643 | 133.649 | 259.462 |
| 면적 horizontal m2 | - | 33.7 | 33.7021 | 65.4108 |
| 면적 vertical m2 | - | 54.8605 | 54.8678 | 54.8713 |

- 날개 끝 시위와 수평미익 끝 시위가 R3 열에서 1.641 / 1.240 m로 나오는 것은 `REFERENCE_KO.md`의 1.652 / 1.257 m와 측정 방법(여기서는 y=끝−1e-4 m의 x 슬라이스 폭, 거기서는 원장 링)이 다르기 때문이다.
- 날개 뿌리 시위(6.099 대 인쇄 6.07)와 수평미익 뿌리 시위(3.236 대 3.31)는 R3 원장 값이며 OpenVSP도 같다. 이 일치는 R3 단면을 썼기 때문이다(`REFERENCE_KO.md`와 같은 해석). 높이와 핀 행은 몸통 일정 구간 슬라이스로 쟀다. R3 열이 `REFERENCE_KO.md` 값(4.140, 5.870, 10.010)을 재현한다. 전체 bbox의 z 범위(OpenVSP 4.143, R3 4.182)는 꼬리 위 쪽이 올라온 값이라 참고용이다.
- 동체 부피는 OpenVSP 476.35 m3, R3 466.31, 차이 +2.2 %(타원체 코·꼬리와 완전 타원 단면의 결과).

## 4. 조밀 양방향 편차

모든 삼각형 7 무게중심 점, `trimesh` 정확한 가장 가까운 점(`dense_component_deviation.py` 방식). 날개와 수평미익은 OpenVSP 쪽에서 y=0 평면 캡 삼각형을 표본에서 뺐고, 기준 쪽은 y≥0 절반이다. 수직미익은 뿌리 캡(z=5.5)을 뺐다.

| 부품 | 기준 | 한계 mm | OpenVSP→기준 최대 mm | 기준→OpenVSP 최대 mm | p99 mm (양쪽 큰 값) | 최악 위치 |
|---|---|---|---|---|---|---|
| fuselage | r3_fuselage | 25 | 491.73 | 488.19 | 454.91 | [41.4408, -0.0626, 3.4087] / [41.2766, 0.074, 3.8757] |
| wing | r6c_wing | 10 | 1.61 | 1.73 | 0.94 | [16.0478, 0.0, 3.0547] / [16.0298, 0.0, 2.9807] |
| horizontal | r6c_horizontal | 10 | 1.50 | 1.58 | 1.05 | [38.3832, 0.0399, 4.6143] / [38.3547, 0.0, 4.6051] |
| vertical | r6c_vertical | 10 | 3.83 | 4.57 | 2.22 | [35.2966, 0.0194, 5.5368] / [35.2608, -0.0227, 5.5] |
| 합집합 | R3 합집합 | - | 491.73 | 488.19 | 391.80 | [41.4408, -0.0626, 3.4087] / [41.2766, 0.074, 3.8757] |

### 동체 편차의 x별 분포 (OpenVSP 동체 → R3 동체)

| x 구간 m | 최대 mm | 중앙값 mm | 최악 위치 |
|---|---|---|---|
| 0–4.0 | 306.0 | 90.14 | [1.049, -0.352, 4.619] |
| 4–8.0 | 124.6 | 20.08 | [4.382, -1.783, 4.215] |
| 8–12.0 | 8.9 | 1.10 | [10.449, 1.82, 4.825] |
| 12–16.0 | 8.3 | 1.07 | [12.709, 1.82, 4.825] |
| 16–20.0 | 8.3 | 1.12 | [16.381, -1.82, 4.825] |
| 20–24.0 | 188.2 | 1.31 | [21.749, -0.941, 2.2] |
| 24–28.0 | 7.5 | 1.13 | [27.607, 1.831, 4.794] |
| 28–32.0 | 25.3 | 1.59 | [31.946, 1.947, 3.941] |
| 32–36.0 | 238.6 | 40.34 | [35.974, 0.03, 2.354] |
| 36–40.0 | 482.0 | 166.94 | [39.957, 0.748, 3.233] |
| 40–44.0 | 491.7 | 255.60 | [41.441, -0.063, 3.409] |
| 44–44.5 | 118.4 | 65.48 | [44.025, 0.01, 4.524] |

- 몸통(x 8–29)은 중앙값 약 1 mm다(타원 대 R3 곡선과 면 분할 오차). 최대 8–9 mm는 |y|≈1.8 m, z≈4.8 m(몸통 옆 위)에 있다.
- x 20–24, 188 mm(최대): 몸통 아래 |y|≈0.9 m. `post-checks.json`의 아래쪽 윤곽 슬라이스에서 x=21.75, |y|=0.94는 R3 z 2.417, OpenVSP z 2.199로 R3가 **218 mm 높고**(|y|=0.5에서 141 mm, 1.5에서 68 mm, 중심선 y=0은 같음), x=15와 x=25에서는 두 곡면이 1.7 mm 이내로 같다. 즉 몸통 전체를 따라가는 평탄 클립이 아니라 x≈20–24 부근의 국소 오목이다(R3의 한 특징). **원인은 확정하지 못했다**(날개-동체 배면 처리 흔적일 수 있으나 R3 곡면을 따로 분석하지 않았다).
- 코(x<4)와 꼬리(x>32)는 내 형상 규칙이 R3와 다르다. 꼬리 아래쪽은 R3가 더 가파르게 올라간다. 이 구간은 도면 윤곽 곡선(R7 방법 M1–M3)이 있어야 맞출 수 있다.

## 5. 대칭, 접합 루프, 테셀레이션 민감도, surfaceCheck 위치

**대칭(y=0, 합집합).** 정점 거울: 36,974개 중 최대 3.85e-6 m(위치 x 43.54, y 0.007, z 11.72, x≥32 m의 float32 한 눈금 3.81e-6 m), p99 2.3e-7 m, 99.78 %가 1e-6 이내. 표면 거울(트라이앵글 표본 517,608점, 거울상 합집합을 합집합 표면에 정확히 투영): 최대 4.0e-5 m(x 23.16, y 1.78, z 3.13, 접합선 근처), p99 2.2e-7 m. 판정: 1e-6 m 이내 대칭이 아니다. 비대칭은 접합 교선 삼각분할 차이이고, 반쪽 CompGeom은 별도로 36,982 삼각형을 낸다(전체의 절반 36,972보다 10개 많음, 절단면 삼각형).

**접합 루프(합집합 삼각형을 가장 가까운 부품 표면으로 라벨링해 센 것).** 동체|주익 2개(각 298 정점, 닫힘), 동체|수평미익 2개(각 220), 동체|수직미익 1개(260, 닫힘). 모호 삼각형 0, 라벨 최대 거리 1.2e-5 m. R6-c의 `surfaceBooleanFeatures` 결과(날개 2, 수평 2, 수직 2이며 수직은 열린 호 4끝)와 방법이 달라 **같은 조건의 비교가 아니다**.

**나쁜 삼각형 위치.** Q<0.01: 414개, 접합선 5 cm 안 290개, 20 cm 안 348개. 최악 Q 5.75e-6 삼각형은 수직미익 앞전 뿌리(x 36.26, z 6.08)다. 동체 정상부를 얕은 각으로 가르는 곳이다.

**테셀레이션 민감도(합집합, 모든 수를 배수).**

| 설정 | 삼각형 | 경계 변 | Q_OF 최소 | Q_OF p1 | Q<1e-3 | Q<1e-2 | surfaceCheck |
|---|---|---|---|---|---|---|---|
| ×0.5 | 32,734 | 0 | 2.2e-6 | 0.0100 | 114 | 328 | 125 |
| ×1 (본 모델) | 73,944 | 0 | 5.8e-6 | 0.0159 | 124 | 414 | 465 |
| ×2 | 192,704 | 0 | 6.7e-7 | 0.0169 | 240 | 1,216 | 2,646 |

세 설정 모두 닫혀 있다. 슬리버 수는 해상도와 함께 늘고 사라지지 않는다. surfaceCheck 기록은 삼각형 수와 거의 비례해 늘어난다.

**surfaceCheck 기록 위치(출력 한계 1000으로 점 목록을 받음).** 동체 858점은 모두 x 7.2–29.8, 합집합 465점은 x 7.27–29.03이다. 배면·정상부 5 mm 안은 동체 9점, 합집합 2점뿐이다. 합집합 465점의 날개·수평미익·수직미익 표면까지 최소 거리는 0.138 m, 중앙값 3.12 m, 5 cm와 10 cm 안은 0점이다(`post-checks.json`). 접합선 위 기록은 없다.

## 6. OpenVSP가 CFD용 표면에서 낫고 못한 점

**낫다.**
- 파일 익형 섹션 로프트가 R6-c 날개·꼬리(R3와 같은 형상)를 4.6 mm 이내로 재현하고 부피를 R3와 0.04 % 이내로 맞춘다. 코드는 섹션 값만 넘긴다.
- 합집합이 한 번에 닫힌 다양체이고 감김과 방향이 맞다. 생성 스크립트 약 210줄(+파라미터·섹션 추출 약 210줄), CompGeom 2 s.
- 동체 단독은 정점이 축 평행 링과 y=0 꼭짓점을 갖고 삼각형이 고르다(Q 최소 0.105, 종횡비 최대 14.7).
- 파라미터화가 공개되어 있고(`.vsp3`, `.af`) 스크립트만으로 재생성된다. Blender가 필요 없다.

**못하다.**
- **접합 슬리버.** CompGeom 절단이 만든 삼각형은 Q 5.8e-6, 최소 각 0.0016도, 종횡비 35,790까지 간다. 품질 규칙(M5의 02c/02d 같은 전용 테셀레이션)이 없고 조절 수단이 없다. 표본에서 수가 해상도와 비례한다.
- **극점.** 동체 코·꼬리 끝에서 정점 차수 64. 계약 02의 "극점·끝 부채 금지"에 걸린다.
- **surfaceCheck 기록**이 곧은 몸통에서 나온다(858 / 465). 이 몸통은 타원 단면의 정확한 축 평행 원통이다. R3 동체(255), R6-c 동체(48)와 같은 종류의 검사기 불일치로 보이지만, 원인은 이 작업에서 증명하지 못했다.
- **대칭이 정확하지 않다**(40 µm). 접합 삼각분할이 좌우에서 다르다.
- 도면 윤곽 같은 임의 곡선은 입력할 수 없다. 동체는 타원·초타원 등 내장 단면 계열과 XSec 위치로만 만든다. 연속성 C2는 단면 간격이 고르지 않으면 진동했다.
- STL이 ASCII 10자리라 이진(float32)으로 바꿔야 한다(변환 오차는 float32 눈금).

## 7. 명령과 벽시계 시간

저장소 루트 `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight`, 브랜치 `feat/a321-r7-fuselage`. 시각은 `date`로 쟀다(KST). 단 게이트와 비교 스크립트의 시간은 스크립트 자체 타이머(`perf_counter`)이고, `uv` 환경 설치 시간(최대 1분 14 s)은 제외했다. `V` = `.worktmp/venvs/openvsp313/Scripts/python.exe`, `R` = `research/a321-quality/r7/openvsp`, `W` = `.worktmp/r7-openvsp`, `WS` = WSL 경로 `/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight`.

| 단계 | 명령(저장소 루트, Git Bash) | 시간 |
|---|---|---|
| 모델 생성 4건 | `$V -I $R/build_a321_vsp.py --mode union --half --out-json $W/build-union.json`; `... --mode components --out-json $W/build-components.json`; `... --mode union --tess-scale 0.5 --tag _t0.5 --out-json $W/build-union_t0.5.json`; `... --mode union --tess-scale 2.0 --tag _t2.0 --out-json $W/build-union_t2.0.json` | 17:20:42–17:21:53, 합계 71 s. CompGeom(스크립트 타이머): 합집합 2.08 s, 반쪽 2.09, 동체 0.34, 날개 0.32, 수평 0.10, 수직 0.19, ×0.5 0.86, ×2 5.87 |
| 게이트 합집합 | `cd research/a321-quality/r6/checks; uv run --no-project r6_gate.py --surface openvsp_union=$PWD/../../../../$W/openvsp_union.stl --checkers locator,meshlab --log-dir ../../r7/openvsp/gate/union --out ../../r7/openvsp/gate/union-report.json` | 66.2 s |
| 게이트 부품 | 같은 디렉터리에서 `--surface openvsp_fuselage=... --surface openvsp_wing=... --surface openvsp_horizontal=... --surface openvsp_vertical=... --checkers locator,meshlab --log-dir ../../r7/openvsp/gate/components --out ../../r7/openvsp/gate/components-report.json` | 28.5 / 34.8 / 22.1 / 28.0 s(합집합과 병렬, 17:22:13 시작) |
| surfaceCheck(WSL, 복사본, `mktemp -d`) | `MSYS_NO_PATHCONV=1 wsl -e bash $WS/$R/run_surfacecheck_r7.sh <union\|fuselage\|wing\|horizontal\|vertical\|union_t0.5\|union_t2.0> $WS/$W/openvsp_<name>.stl 0`; 점 목록은 이름 `fuselage_obj`, `union_obj`에 임계값 `1000` | 9회 합계 17:22:13–17:22:32(WSL 기동 포함), 합집합 0.64 s |
| 비교 | `cd research/a321-quality/r6/checks; uv run --no-project ../../r7/openvsp/compare_openvsp.py --out ../../r7/openvsp/openvsp-compare.json` | 17:24:40 시작, 678.8 s(대칭 35 s, 접합 355 s, 조밀 편차 289 s) |
| 동체 x별 편차 | 같은 디렉터리에서 `uv run --no-project ../../r7/openvsp/fuselage_bins.py --out ../../r7/openvsp/fuselage-deviation-bins.json` | 17:39:11–17:40:05 |
| 사후 점검 | 같은 디렉터리에서 `uv run --no-project ../../r7/openvsp/post_checks.py --out ../../r7/openvsp/post-checks.json` | 18:05:26 시작(환경 설치 제외 수 초–수십 초) |
| 두께·연속성 점검 | `$V -I $R/build_a321_vsp.py --mode components --correct-thickness 1 --tag _ct1 --out-json $W/build-components_ct1.json`; `$V -I $R/check_root_thickness.py --out $R/root-thickness-check.json`; `$V -I $R/check_fuselage_continuity.py --out $R/fuselage-continuity-check.json` | 17:44:16–17:44:42 |
| 렌더 | `$V -I $R/render_openvsp.py` | 17:24:57–17:25:11 |

- 오류 반복 없음. 첫 `compare` 실행은 접합 단계의 `closest_point` 한 번 호출이 메모리 54 GB까지 올라가 내가 중단하고 20,000점 단위로 쪼갰다.
- 첫 모델(`CorrectAirfoilthicknessFlag=1`)로 한 번 전체를 돌리다가 뿌리 두께 오차를 발견해 폐기하고 전부 다시 만들었다. 첫 결과는 보고에 쓰지 않았다.

## 8. 하지 않은 것과 한계

- **G4R(동체 충실도)와 G6**(특징선 제외 이면각, 스테이션 꺾임): 실행하지 않았다.
- **전폭 닫힌 날개·수평미익 부품**: OpenVSP 대칭 날개는 y=0 평면에서 닫힌 부품을 내지 않아 +y 반쪽(평면 캡)으로 대신했다. 그래서 부품 게이트는 R6-c 전폭과 직접 비교가 아니라 반쪽 비교다.
- **VSPAERO**, GUI, 형상 변형 해석: 하지 않았다(계약 03).
- **surfaceCheck 원인 분석**: 위치와 해상도 의존만 보였고, 몸통을 살짝 곡선으로 만드는 대조 실험은 하지 않았다.
- **접합 루프**는 `surfaceBooleanFeatures`가 아니라 라벨 방식이라 R6-c와 같은 조건이 아니다.
- **동체 형상**은 도면 윤곽에 맞추려 하지 않았다. 도면 윤곽 곡선은 R7 동체 작업의 몫이다.
- 임시 `__pycache__`: `r6/gen`의 `r6_io`, `r6_ledger`를 읽기 전용으로 import하면서 `r6/gen/__pycache__`(git 무시 대상)에 `.pyc` 두 개가 생겼고, 마지막에 지웠다.
- 저장소 안에 STL을 두지 않았다. 모든 STL은 `.worktmp/r7-openvsp/`(git 무시)에 있고 SHA-256은 `openvsp-compare.json`의 `stl_sha256`에 있다.

## 9. 산출물

모두 `research/a321-quality/r7/openvsp/` 아래다.

| 파일 | 내용 |
|---|---|
| `build-union.json`, `build-components.json` | 생성 파라미터 기록(섹션, 스테이션, 테셀레이션, 출처 꼬리표) |
| `post-checks.json`, `post_checks.py` | surfaceCheck 점 거리, 아래쪽 윤곽, 최악 정점 |
| `build_a321_vsp.py`, `a321_params.py`, `r3_sections.py`, `stl_tools.py` | 생성 코드와 출처 꼬리표 붙은 파라미터 |
| `a321_openvsp_union.vsp3`, `a321_openvsp_components.vsp3`, `a321_openvsp_union_t0.5.vsp3`, `a321_openvsp_union_t2.0.vsp3` | OpenVSP 모델 |
| `af/*.af` | R3 단면에서 만든 파일 익형 41개 |
| `run_surfacecheck_r7.sh`, `sc/attempts/` | surfaceCheck 시도(로그, SHA 기록, 점 OBJ 2개) |
| `gate/` | r6_gate 보고서(합집합, 부품 4개) |
| `compare_openvsp.py`, `fuselage_bins.py`, `check_root_thickness.py`, `check_fuselage_continuity.py`, `print_tables.py`, `render_openvsp.py` | 비교, 두께·연속성 점검, 표, 렌더 |
| `openvsp-compare.json`, `fuselage-deviation-bins.json`, `root-thickness-check.json`, `fuselage-continuity-check.json` | 모든 수치 |
| `figures/openvsp_top.png`, `openvsp_side.png`, `openvsp_front.png`, `openvsp_wing_root_mesh.png`, `openvsp_tail_mesh.png` | 직교 투영 렌더와 접합부 메시 |
| `PROVENANCE.md` | 출처와 라이선스(OpenVSP NOSA 1.3, 별도 프로그램으로 Python API 사용) |
| `logs/` | 게이트·비교·렌더 로그 |

## 오케스트레이터 검토 메모 (2026-11-16, 커밋 전)

- `a321_openvsp_union_t0.5.vsp3`와 `a321_openvsp_union_t2.0.vsp3`는 테셀레이션 배율만 다른 1.4 MB 사본이라 저장소에서 뺐다. 지금은 `.worktmp/r7-openvsp/vsp3-variants/`에 있고, SHA-256은 `openvsp-compare.json`에 남아 있다.
- 독립성 단서가 두 가지 있다. 이 작업자는 동체 모양 규칙을 정하기 전에 R3 요약값을 보았고, R7 측정 작업자와 같은 세션 스크래치패드를 썼다(탐색 파일 두 개를 덮어씀). 측정 결과 파일은 읽지 않았다고 보고했다.
- 곧은 몸통에서 나온 surfaceCheck 기록(동체 858곳, 합집합 465곳)은 계약 03a의 0단계 원통 관문에 근거로 넘겼다. 원인은 증명되지 않았고, 이 문서는 이를 G3 실패로 적는다.
