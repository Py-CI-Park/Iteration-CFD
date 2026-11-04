# 최종 검토와 중단 영수증

2026-11-04 KST. 범위: CPU 형상 준비 1~5단계. 연구 결과는 **PARTIAL**, 전기체 표면은 **FIX_FIRST**, 하위체계는 **제한된 변 위상 검사 통과 / NOT_VALIDATED**.

## 독립 검토 5개

| 담당 | 최초 | 보완 | 최종 |
|---|---|---|---|
| 목표·범위 | FIX_FIRST | RUNBOOK의 4→5 기하 테스트 수 정정 | PASS |
| 실제 QA | PASS | 원본·frozen·STL SHA·왕복 바이트·CPU 테스트 직접 확인 | PASS |
| 코드·과학적 주장 | FIX_FIRST | closed_oriented를 변 incidence 검사로 명시, 정점 다양체 UNMEASURED와 점 접촉 한계 기재 | PASS |
| 파일 보존 | FIX_FIRST | 출력 범위·동결 input·기존 결과 거부와 4회귀 추가 | PASS |
| NASA·문맥 | PASS | 404 제외, V&V 구분, wing-box와 전기체 분리 | PASS |

이 PASS는 연구 구현·문서·custody의 제한 검토다. 항공기 모델·체적 격자·CFD·물리 정확도 승인이 아니다.

## 실제 검증

- 독립 struct/numpy/scipy STL 리더로 원 추출·80mm·40mm·wing-box 4개 검사.
- native 40mm 후보와 wing-box를 새 Blender background 프로세스에서 재열기, 재출력 STL SHA 동일.
- 출력 보호 적용 후 wing-box를 새 `wing-guarded-check` 폴더로 다시 추출·독립 재검사: 기존과 같은 STL SHA.
- CPU 기하 테스트 5개 + 출력 보호 4개 = **9 passed**; ruff check 통과.
- 비유한 좌표 거부는 실패 1/통과4 확인 뒤 검사 추가. 나머지 초기 기하 검사는 analytic invariants로 작성·실행했으며 모두 failing-first였다고 주장하지 않는다.
- Ego Lite에서 보고서 한국어 본문, 9개 제목, NASA 링크 8개, 실제 SVG 이미지 로딩 확인.
- 원본 source와 frozen의 SHA 동일·원본 미변경.
- GPU probe·CUDA context·GPU solver·GPU validation·체적 메셔·Blender 렌더 실행 없음. 디스플레이 GPU 사용 0을 주장하지 않음.

## 보존·인계

정확 바이너리는 `artifacts/`, SHA·바이트 목록은 `evidence/artifact-manifest.json`에 있다. Git에는 보고서·코드·JSON/SVG 근거를 기록하고 약 400MB의 모델/실패본은 local artifacts로 보존한다. 이 폴더를 제거하거나 작업트리를 정리하기 전에 바이너리를 별도 보존해야 한다.

다음 작업은 Crown/Belly 외피·return·개구 분리와 국소 폐합 검토다. 정점 link·자기교차·접촉 검사는 아직 필수 잔여다. 현재 전기체를 체적 메셔나 solver에 넣는 단계로 진행하지 않는다.
