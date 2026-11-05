# 검토·인계 영수증

2026-11-05. 목표: 새 공력 전용 외피 생성과 GPU 수치 계산 직전의 가능한 CPU 준비. 현재 **형상 R2 DONE, CPU tetrahedra DONE, 공력용 격자 수용 FIX_FIRST, 물리 validation NOT_RUN**.

## 실제 검증

- 고정 native SHA와 동결 입력 일치, 원본 재저장 없음.
- 최종 native Blender CLI 작성·별도 프로세스 재열기·STL 재출력 SHA 일치. Blender GUI에서 `models/A321_AIRFRAME_SHELL_R2.blend` 실제 창/형상 확인.
- 129,532 triangles / 64,768 vertices; 변 incidence 실패0·정점 link 실패0·Euler2·연결성분1·Manifold kernel NoError.
- 18개 직접 단면 범위, 48개 독립 중간 단면, 부품별 양방향 거리 표본 측정. 큰 거리 outlier와 전체 형상 충실도 HOLD를 문서에 표시.
- 저장된 793,977 tets 독립 재계산: nonpositive0, 전체 체적 일치, fluid region1, mean-ratio<0.01 4,797개. 경계층0 → 격자 FIX_FIRST.
- 테스트 15 passed: 새 profile4 + vertex-link2 + 이전 geometry5 + custody4. ruff/check whitespace 통과.
- Ego Lite에서 NASA process 원문 재확인, 로컬 보고서 제목·모델 링크·그림2개 실제 로딩 확인.
- GPU probe·CUDA context·solver·validation·Blender render 호출 없음. 일반 창 표시는 OS 그래픽을 사용한다.

## 독립 검토 5개

| 관점 | 지적·수정 | 최종 |
|---|---|---|
| 목표·범위 | 실제 push 전 pushed=true 오인 제거, publish_intended로 변경·index 재확인 | PASS |
| 코드 | 주요 기하·격자 분석 스크립트 정적 검토, 모두 250LOC 이내 | PASS |
| 실제 QA | 모델/manifest 해시·STL·정점link·tet 배열 재계산; bpy 분류 누락 보완 | PASS |
| 파일보존·보안 | 원본/secret 제외·모델 파생물·고정 출력 경계 검토 | PASS |
| 과학적 주장 | 샤클렛 포함 span의 pinned 객체 bounds 근거 추가 | PASS |

PASS는 이 연구 코드·근거·문서의 제한 검토다. 실기 A321 성능·공력 격자·GPU readiness 승인으로 확대하지 않는다. Gmsh 실패 원인은 확정하지 않았다. 독립 mesher의 다른 성공이 같은 Gmsh 입력이 정상임을 증명하지 않는다.

## 전달과 다음 한 건

공개 포크 `Py-CI-Park/Iteration-CFD`의 `codex/a321-aero-shell-20261105` 브랜치에 새 파생 `.blend/.stl`과 코드/근거/문서를 전달한다. 원본 native·reference NPZ·대용량 격자·전체 로그는 로컬 artifacts에 보존하고 SHA/bytes만 기록한다. 실제 원격 반영 SHA는 push 뒤 검증해 응답에 기록한다. main 병합·릴리스·태그는 범위 밖이다.

**다음 한 건:** root/끝단 outlier 위치를 분류하고 허용 형상 근사를 결정한 뒤, CPU 경계층 생성이 가능한 격자 경로로 sliver와 외부 경계 해상도를 보완한다. 독립 ofgpu mesh gate 및 solver runtime 준비가 남아 있으므로 지금의 격자로 계산을 시작하지 않는다.
