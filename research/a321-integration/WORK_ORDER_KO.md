# Studio·날개 표면·경계층·polyMesh 연구

2026-11-06. 기준 브랜치 `codex/a321-aero-shell-20261105`, 시작 SHA `6d4bfed29618a5755898dbb9cd8fcd4d4e62656a`. R2와 원본 native는 동결 보존.

사용자 승인: Ego Lite에서 Studio 실제 STL 로딩 → 날개 홈/접합 확인 및 필요시 재구성 → sliver/경계층 CPU 개선 → polyMesh 변환/품질 → 연구 기록·commit/push. RTX4080 SUPER 짧은 GPU/VRAM 진단 허용. 항공기 본해석은 실행하지 않음.

가설: H1 장치 표면의 변화가 원본 부품 flap/slat 불연속을 section envelope가 승계함. H2 station 간 직선 loft와 convex-hull sampling이 스팬 방향 꺾임/홈을 만듦. H3 위상은 정상이지만 smooth shading/법선이 홈을 강조함. 실제 단면·앞전/뒷전·두께 연속성과 Studio 화면으로 구분한다.

순서: 독립 Studio 포트/연구 workspace 실행 → R2 표면 실제 표시 → 소스/날개 span parameter 계측 → 사본 R3 시험 → 원형/수리 fidelity 기록 → CPU prism/layer와 background grid 생성/검사 → polyMesh 독립 재읽기·폐합·비직교·연결성 → 제한 CUDA diagnostic → 로컬 보고서·5관점 검토·commit/push. 실패 관문은 완화하지 않는다.

GPU diagnostic은 UUID `GPU-2147afeb-b9fc-c7f5-398b-d5d00a3a5a90`로 한정하며 최대 1GiB scratch allocation·쓰기/읽기 검증·해제 확인만 한다. 다른 작업을 종료하지 않음. CUDA runtime/solver 호환은 diagnostic과 별개다.
