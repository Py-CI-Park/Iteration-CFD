# 2026-11-07 위치 지도·CPU 재검사 원장

- 시작 HEAD `1e08cbd`, 연구 브랜치 유지. R3 및 snappy-03 격자는 변경하지 않는다.
- `map_hotspots.py`: 실제 실패 집합·processor 주소·층 필드를 원시 ID에 연결한다. seals는 생성 후 snapshot이며 새 실행 전 동결이라는 주장이 아니다. 기존 기준 집합은 복사 mesh에서 독립 checkMesh로 재검사했다.
- 전체 CSV는 로컬 `artifacts/snappy-03-hotspot-map/coordinates.csv` 및 04·05에 있다. Git에는 사진·숫자·해시·주요 로그·입력 사전을 보존한다.
- 새 후보: `uv run research/a321-quality/prepare_hotspot_trials.py` 후 WSL `run_hotspot_trial.sh snappy-04` / `snappy-05`. 기존 후보나 경로 이탈은 거부한다. 입력 manifest와 R3 SHA를 검사한다. 기존 디렉터리에서 재생성하지 않는다.
- 이번 실행 중 스크립트를 수정한 실수로 후처리가 중단됐다. `resume_hotspot_checks.sh`가 생성 완료 결과만 재구성·검사했다. 이 복구는 새 격자 생성이 아니며 손실된 전처리 로그를 복원한 것처럼 기록하지 않는다.
- 완료 뒤 `audit_poly.py --case <case> --run-id v5`, `seal_diagnostics.py --candidate <name>`, `map_hotspots.py --candidate <name>`, `compare_hotspot_trials.py`로 검증·지도·판정을 만든다. 새 수치 감사는 centers NPZ 해시도 기록한다.
- `gpu_diagnostic.py`는 이전 연구 코드를 새 artifacts 경로로 복사해 실행했다. SUPER UUID 고정, 1 GiB 할당·64 MiB 대조만 수행했다. 원래 GPU 영수증은 덮어쓰지 않았다.
- `probe_anthropic_base.mjs`는 현재 Studio 어댑터를 격리된 loopback SSE fixture로 시험한다. 더미 키만 쓰며 도구는 실행하지 않는다. 실제 OpenCodex를 시작·설정·호출하지 않았다.
- Ego TaskSpace 13 원장: 01 접속, 02 실제 read API, 03~04 지원하지 않는 VTU 시험과 실패 관찰, 05 원래 volume mesh의 geometry-only 표시, 06 보고서 첫 검사(옛 보고서 문자열 검사 기준 오류), 07 기준을 고친 브라우저 검사. 이미지 지도는 CPU 산출물이며 Studio의 가짜 색상 지도가 아니다.
- Python 의존성 패키지 설치와 공개 문서 조회는 네트워크를 사용할 수 있다. 사용자 데이터·키를 외부 모델에 보냈다는 뜻은 아니다.
- `uv run research/a321-quality/build_report.py`로 최신 요약과 이전 문서 전체를 재구성한다. 로컬 HTML은 `http://127.0.0.1:8776/a321-quality/report.html`.
