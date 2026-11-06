# 2026-11-06 검토·중단·재개 영수증

결과: **PARTIAL**, mesh acceptance **FIX_FIRST**, aircraft solver **NOT_RUN**.

## 실제 검증

- Ego Lite의 연구 workspace Studio에서 R2/R3 STL 실제 탐색기 클릭·canvas 표시, geometry REST 응답 기록.
- R2 trailing-edge notch failing test: -6.43006 slope → R3 연구용 보간 후보 테스트 통과. root/seam 최대이동 각각1.01256/1.15849m, OEM 충실도 HOLD.
- R3 Blender 새 프로세스 재열기·STL 재출력 SHA 동일, exact topology/vertex-link 확인.
- hybrid5층 생성·861165셀 polyMesh 변환, streaming 재읽기·모든 saved face-cell incidence·7patch ranges/coordinate planes 확인.
- 품질은 maxnonorth90.8168°, closure3.34156, sampled inverted prisms20, collapsed stack → **거부**.
- CUDA driver memory1GiB allocation /64MiB roundtrip·release, RTX4080SUPER UUID 고정, 전후free 동일. arithmetic kernel·항공기 solver·ofgpu probe NOT_RUN.
- 20tests passed (geometry/profile/topology/custody plus groove/conversion/interface), ruff/check whitespace 통과.
- 원본 source SHA 고정, default/pin·main 수정 없음. 전체 실패 artifact와 debug emit파일은 연구 artifacts로 이동 보존.

## 독립 검토

목표·과학적 주장·security는 bounded report PASS. QA는 파일/해시·품질값 재확인 후 mesh FIX_FIRST를 확인했다. 코드 검토에서 per-step 변경량이 누적 계산되는 bookkeeping과 boundary/face 재읽기 누락을 지적하여 수정했다. 새 `polyMesh-readback-contract.json`으로 모든 saved incidence와 boundary metadata를 확인했다. 독립 검토 PASS를 mesh 승인으로 사용하지 않는다.

최종 bounded research/evidence QA도 PASS로 확인했다. 코드 검토의 후속 patch membership 지적은 각128 farfield 및129522 aircraft-wall 예상면수와 원 wall face 집합 exact comparison으로 보완했고, 실제 재실행 영수증의 `aircraft_wall_face_membership_exact=true`, `expected_patch_counts_checked=true`를 확인했다. 최종5관점의 연구 전달 판정 PASS이며, 과학적 mesh acceptance는 계속 FIX_FIRST다.

GPU의 일반 드라이버 메모리 접근만 확인됐고 CUDA Toolkit12.6/문서13.x와 ofgpu binary 미존재는 계속 잔여다. 셀수별 solver VRAM 요구·커널 호환·수렴·실기 물리 검증은 모두 미측정이다.

다음 한 건: 폐합·곡률을 보존하는 표면 재메시/clearance 기반 경계층 알고리즘을 마련해 프리즘 Jacobian·비직교·폐합을 통과시킨다. 현재 층은 실패 예제로 고정하고 GPU solver에 투입하지 않는다.
