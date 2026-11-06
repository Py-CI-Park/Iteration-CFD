# 교차 검토 기록

이번 연구는 `review-work` 절차로 목표/제약, 코드, 보안/원본 보존, 실행 QA, 기존 문맥/출처의 다섯 독립 검토를 받았다. **초기 전체 판정은 FIX_FIRST**였으며 항공기 GPU 해석 허가로 사용하지 않는다.

## 발견과 처리

| 발견 | 처리 |
|---|---|
| 재시도 후 실패한 prism도 accepted artifact로 저장할 수 있음 | 실패 artifact 이름 분리, NaN/Inf/0/음수 거부, downstream에서도 실제 Jacobian 재검사 |
| exterior 실패 JSON 후 종료 코드 0 | 실패 영수증 보존 후 SystemExit(2), 회귀 검사 추가 |
| 기존 hybrid 덮어쓰기 가능 | 생성 전 existing hybrid/raw artifact 거부, 바이트 보존 회귀 검사 |
| 좌표 일치만으로 접합면 conformity를 판단할 수 없음 | 모든 내부 면 반대 cyclic winding, 정확한 접합·벽면 삼각형 multiset 검사 및 누락/분할/같은 winding 회귀 추가 |
| 이차식 내부 최소값을 테스트하지 않음 | 기존 높이 표본 0/.5/1이 놓치는 t=.25의 음수/0 최소값 fixture 추가 |
| alternate audit이 중간 volume 파일을 신뢰함 | 저장된 polyMesh face/owner/neighbour에서 체적 재계산. tested fan geometry는 공유하므로 완전히 독립적인 체적 공식 검증이라고 부르지 않음 |
| quality 후보와 audit 경로가 다름 | converter 및 두 audit의 --quality가 quality-exterior-03으로 일치. 실패 후보는 자동 대체하지 않음 |
| artifacts 부모 폴더가 없는 clone에서 생성 실패 | 경계층 builder가 parents=True로 생성 |
| provenance/runbook과 polyMesh UI 증거 부족 | artifact 해시·환경 metadata·재현 순서·실제 UI 화면/DOM 기록 추가 |

## 남아 있는 검토 실패

- Engineering: 최대 비직교 89.9927°와 상대 폐합 4.0103e-10 및 alternate 1.5276e-9는 각각 유지 기준을 초과한다.
- 유효 경계층: 첫 층 최소 약 31.8 nm, solved y+ 미측정, 실제 경계층 전체 포착 미확인.
- 전역 셀 overlap/collision은 미측정이다. 양수 Jacobian은 전역 겹침 없음의 증명이 아니다.
- 제외된 품질 사면체 trial은 64,763개의 외곽 정점 중 2개의 정확 좌표를 찾지 못했다. 최근접 거리와 동일 정점 이동량을 혼동하지 않는다.
- 실제 ofgpu solver mesh gate, pressure/velocity, 공력 계수, 항공기 GPU 계산은 실행하지 않았다.

코드·안전장치 회귀 검사 통과와 연구 자료의 게시 가능 여부를 위 engineering 합격 여부와 구분한다. 검사 출력과 최종 재검토 범위는 `evidence/verification.json`에 별도로 기록한다. 독립 코드 검토자는 현재 1,036,176 프리즘의 해석적 최소값을 직접 계수식으로 재계산해 같은 최솟값과 비양수/비유한 0개를 확인했다. 이는 전역 충돌 또는 공력 validation을 포함하지 않는다.

최종 scoped 재검토에서 이전 코드/보존 결함은 해결됐고, 독립 실행 QA는 19개 테스트·lint·format을 통과했다. 코드 검토자는 임시 파일 테스트 2개를 제외한 17개 및 전체 mesh guard를 별도로 실행했다. 당시 공통 잔여 지적이었던 verification.json 부재는 부모 실행자가 실제 도구 출력을 모아 파일을 추가·파싱하여 처리했다. 전체 engineering 판정은 여전히 FIX_FIRST다. 세부 범위는 `evidence/review-closeout.json`에 남겼다.
