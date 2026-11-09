# R5 재구성 코드 출처

모든 신규 코드는 Codex가 동결된 로컬 단면 데이터와 사용자 형상 계약을 기준으로 독립 작성했습니다. GPL 구현 소스를 읽거나 복사하지 않았습니다. OpenFOAM·Blender는 별도 CLI 실행만 사용합니다.

| 파일 | 작성 근거 |
|---|---|
| curves.py | SciPy PCHIP 공개 API, 동결 단면별 대응 점 궤적; 원래 꺾은선 위 2%/98% 보조 제어점 |
| geometry.py | 일반적인 삼각형 ring loft·체적 방향·정점 링크 순환 검사 |
| generate.py | 부모 동결 계약과 R3 측정 원장, manifold3d 공개 API로 별도 CPU 합집합 |
| binding.py | binary STL 공개 파일 형식과 native 삼각 좌표 직접 비교 |
| blender_adapter.py | 별도 bpy 공개 API로 새 BLEND 저장·독립 프로세스 재읽기 |
| test_rebuild.py | 원래 단면 보존·실제 형상 변화·연속성·신규 산출물 덮어쓰기 금지 |
| test_binding.py | native/STL 불일치 거부 회귀 |
| test_topology.py | 폐합 및 pinch 정점 링크의 독립 검사 |
| surface_check.sh | 설치 OpenFOAM v1912 CLI help만 사용; 구현 소스 참조 없음 |

루트 provenance 행은 부모 작업자가 관리합니다.

| cleanup.py / cleanup_b.py | 독립 작성; manifold3d 설치 공개 API simplify/get_tolerance 문서만 사용. 고정 1 µm 정리, A↔B 표본 거리·M1 해시 검사 |
| test_cleanup.py / test_hardened_curves.py | 고정 정리 허용치 RED→GREEN 및 곡선 경계 회귀 |
| test_blender_guards.py | 별도 Blender 실제 mini BLEND 파일로 transform/parent/modifier/SHA/lock 5종 거부 회귀, GPL-2.0-or-later 별도 어댑터 |

blender_adapter.py는 사용자 지시 및 기존 어댑터 관례에 따라 GPL-2.0-or-later SPDX를 사용하며, 별도 Blender 프로그램 안에서 실행됩니다. 다른 Python 계산 모듈은 저장소 헤더를 따릅니다.

| custody.py / test_custody.py | 독립 작성; 동일 captured bytes 해시/파싱과 부모 M1 동결 R4 비교 회귀 |
