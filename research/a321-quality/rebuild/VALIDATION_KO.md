# R5-A 실행 결과 — 형상 인수 FAIL / 실패 초안 보존

| 항목 | 실제 결과 |
|---|---|
| 생성 | 전 부품 길이/스팬 대응점 PCHIP 궤적 재구성, 761,090 삼각형 |
| 원래 단면 제어점 | float32 후 최대 약 1.92 µm, 계약 10 µm 안 |
| bbox extrema | R3와 차이 0 m |
| 부피 | 504.86086945391304 m³, R3 대비 상대 변화 8.932705597627663e-8 |
| 실제 생성 표본 변화 | 동체 2.03993 mm / 주익 0.0622548 mm / 수평미익 0.00698954 mm / 수직미익 0.268610 mm |
| 내부 위상 | closed, winding, 단일 component; 퇴화/중복 face 0, vertex link 실패 0 |
| 독립 surfaceCheck v1912 | **자기교차 4,184곳 FAIL**, illegal triangle 없음, 폐합/단일 zone 통과 |
| 삼각형 품질 | 최소 1.19287e-11, 0~0.05 구간 48.1293%; CFD 표면 채택 금지 |
| Blender | 5.2.2 LTS background 저장 및 새 프로세스 재읽기 PASS, STL/NPZ/native 삼각 좌표 정확 일치 |
| GPU/CFD | 미실행 |

생성 영수증의 DRAFT_INTERNAL_GATES_PASS_M3_OPEN은 내부 검사만 뜻합니다.
별도 독립 검사 실패가 최종 형상 판정을 지배합니다. M3는 FAIL/HOLD이고 volume mesh 진행 금지입니다.
shell.npz/STL/BLEND 및 원래 생성 영수증을 덮어쓰지 않았습니다.

## 명확한 범위

단면 원장의 모든 대응 점 궤적을 재구성했습니다. 원래 station의 ring 좌표는 유지하나 단면의 다각형을 chordwise C1으로 바꾸지 않았습니다.
PCHIP 궤적 자체는 C1이지만 삼각형 STL·Boolean 접합부가 전역 C1인 것은 아닙니다.
부품 내부에 묻힌 원래 단면은 합집합 외부 표면 vertex로 남을 필요가 없습니다.
의도적인 평면형 kink는 별도로 분류하지 못했으므로 형상 인수 조건으로 남습니다.
LE/TE도 원래 station 위치는 유지하나 station 사이 궤적이 미세 변경됩니다.
표본 최대 편차는 연속 최대·Hausdorff 거리 증명이 아닙니다.
OEM 형상·공력 정확도·경계층 적합성·시각적인 전체 매끈함을 보증하지 않습니다.

## 다음 구현 가설

2%/98% 좁은 보조 구간은 원래 단면을 지키지만 가느다란 삼각형을 대량 생성했습니다.
이는 측정 결과에 근거한 가설이며 자기교차 4,184곳의 정확한 원인으로 확정하지 않습니다.
다음 후보는 원본 계약을 그대로 두고 적응형 곡선 tessellation/접합부 feature 처리와 교차 위치 지도를 분리해야 합니다.
기존 R3/R4 및 실패 R5-A를 보존하고 새 candidate 이름으로 진행해야 합니다.

## 테스트 실행

최초 생성기 미구현 상태: 3 passed / 1 failed (generate 모듈 없음).
생성기 구현 후: 4 passed.
binding 신규 미구현 상태: 1 failed (binding 모듈 없음).
binding 구현 후: 5 passed (기존 4 + binding 1).
이 RED는 누락 모듈 상태 확인이며 수치 결함의 실패 재현과 구별합니다.
추가 정점 링크 테스트: 2 passed / 141.12초 (별도 실행). 합산 7개 통과이나 단일 suite 재실행은 아님.
no-excuse audit: no violations in 8 files.

커밋·push·부모 관리 문서는 이 작업 범위 밖이며 수행하지 않았습니다.

## 사후 P2 안전 보강 (A 실행 당시 코드와 구별)
- curves 자체 경계에서 비유한 입력·cap 초과 거부.
- custody 동일 캡처 바이트 해시/파싱, M1 freeze 및 원래 R4 해시 대조.
- Blender 새 강화 재읽기: world identity·parent·modifier·저장 SHA 확인 PASS.
- 실제 Blender mini fixture 거부 회귀 5개 PASS.
- native 생성은 배타 .blend.lock 예약 후 재확인.
- surface_check.sh는 mktemp 신규 attempt 로그와 noclobber 사용.
- B 최초 실행은 실제 tolerance 5.306005277816439e-6이 1e-6을 넘어 생성 전 거부. 이후 B trial은 부모 소유.
- 기존 A 영수증을 사후 보강 코드의 실행 증거로 재해석하지 않음.

B 초기 코드 동결은 당시 거부된 실행의 이력입니다. 이후 P2 보강으로 generate.py/curves.py 등이 바뀌었으므로 cleanup_b.py를 그 동결 원장으로 재실행하면 코드 불일치 거부가 정상입니다. 새 B 실행은 부모의 별도 원장·러너를 사용해야 합니다. 최초 B 상한 거부 뒤의 코드 after-equal 검증은 별도 캡처하지 않았으며 이를 통과로 소급 주장하지 않습니다.
