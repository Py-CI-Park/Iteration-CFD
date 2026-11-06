# 2026-11-07 Studio 갤러리 촬영·확인 기록

- 상위 저장소: `using76/Iteration-CFD`의 `1475bbf781e08f33f681661ec40e00727f1e7021`. 병합 커밋 `a39d590`. 기존 A321 연구 모델·과거 보고서 diff 없음.
- 새 연구용 Studio: `http://127.0.0.1:5185/` (API 8815), 데모·mock 모드. 새 worktree-local `npm ci` 의존성을 사용. 항공기 실행·GPU 시험·외부 AI API 미사용. 뷰어의 WebGPU는 표시 기능이다.
- 입력: R3 원본 STL, `snappy-03/calculation-wall-v5.stl`, 동일 후보의 저장 polyMesh. 실제 viewer state는 [표시 원장](../evidence/studio-20261107-receipt.json) 참조.
- `01~04`: Studio 접속, 모델 열기. `05`: 데이터셋을 열었으나 창 최소화로 첫 촬영 실패. `06`: 창 복구, y=10 단면 레이어 시험. 화면에서 내부 셀을 확인하지 못해 증거로 채택하지 않음. `07`: 바깥 6경계+aircraft 와이어프레임, aircraft 표면 모서리, 날개 확대 촬영. `09`: 같은 수준으로 확대해 기준 모델과 파생 벽면을 다시 촬영.
- `08`: 보고서 새 탭 로딩·390 px 모바일·이전 보고서 링크 확인. 최종 화면 확인은 `10`. 번호 파일은 당시 Ego TaskSpace 12 조작 원장이다. 소유권 이전 뒤 그대로 재실행하지 않는다.
- 현황: 독립 CPU 단면은 기존 `mesh-section.png`를 사용한다. Studio 컷 시험을 실제 단면 성공으로 표기하지 않는다. 표시용 삼각 분할 수나 부호 있는 벽 체적은 계산 셀 수/체적과 별개다.
- 테스트: `npm run typecheck` shared/server/web 통과. 서버·웹의 `unstructuredSlice.test.ts`는 각각 4개 통과. 합성 테스트의 통과를 실물 단면 표시 합격으로 확대하지 않는다. 보고서 생성기 Ruff 검사·format 통과. 브라우저 증거는 [보고서 QA](../evidence/report-20261107-qa.json).
- 다시 열기: `uv run research/a321-quality/build_report.py`. `python -m http.server 8776 --bind 127.0.0.1 --directory research`로 연구 전체를 제공하면 [통합 보고서](http://127.0.0.1:8776/a321-quality/report.html)의 과거 보고서 링크도 열린다. Studio는 병합된 GUI에서 별도 루프백 포트를 사용했다.
