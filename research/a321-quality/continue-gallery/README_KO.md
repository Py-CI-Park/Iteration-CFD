# 경계층 조건 연구·2026-11-08 재부팅 복구

## 보존과 수행 범위

시작 HEAD `3a67a10`. 사용자 선택은 저속 **30 m/s·기준 받음각 0°**다. R3 원본과 03·04를 보존했고 GPU CFD는 미실행이다. 06·07 생성은 종료 전에 완료됐으며 재부팅 뒤 같은 작업을 다시 실행하지 않았다.

- `prepare_conditioning_trials.py`: 06 명목 firstLayerThickness 1→4 mm, 07 surface min level 4→5의 단일 변경. 원 R3 SHA와 입력 사전을 고정한다.
- `run_conditioning_trial.sh`: 원래 실행된 파일은 각 trial의 `.execution.lock/runner.sh`에 보존돼 있다. 수정 후 runner는 자기 절대경로를 cd 전에 확정한다. `--inspect`는 읽기 전용이고 상대/절대 호출 결과가 같았다.
- `measure_wall_centers.py`: 실제 float64 벽 삼각형까지의 최근접 중심 거리를 측정했다. 첫 층 전체 높이나 y⁺가 아니다. 재부팅 뒤 identity guard를 추가했으며 현재 04·06 seal/audit/NPZ를 대조했다. 대형 거리 측정을 다시 돌린 것으로 기록하지 않는다.
- `diagnostic_owner_view.py`: 지원 형식의 volume diagnostic을 별도 clone에 쓴다. owner가 공유하는 native face값의 최소를 쓰며 비벽 -1. 원본 case에는 필드를 쓰지 않는다. 이번 04·06은 공유 face값 충돌 0, 각각 57,556면 일치다.
- `package_conditioning.py`: 측정 결과를 현재 bytes와 대조하고 원시 로그·입력 사전·manifest를 보존한다. 기본 CPU gate와 확장 실패, 실제 평균 층 수를 구분한다.
- `native_summary.py`: 로그 첫 요청 표의 8층을 평균으로 잘못 읽던 문제를 final overall thickness 표 선택으로 수정했다. 요청값 8과 실제 1.81/3.14/3.16을 대조하는 red→green 회귀를 남긴다.

## UI 재시작

`powershell -File research/a321-quality/start-research.ps1`은 demo/mock Studio와 로컬 보고서 서버만 띄운다. 기존 포트 소유자를 종료하지 않는다. 실행 뒤 브라우저에서 실제 workspace와 후보를 확인한다. 현재 보고서: `http://127.0.0.1:8776/a321-quality/report.html`.

Ego의 이전 작업 space15는 종료 후 복구 목록에 없어서 새 복구 TaskSpace10을 한 번 생성했다. 이 폴더의 01~04는 종료 전 조작 원장이며, 05 이후는 재부팅 뒤의 현재 검증이다. 번호 파일은 설치 스크립트가 아니며 끝난 TaskSpace를 다음 세션에 자동 재사용하지 않는다.

## 검증

`uv run --with numpy --with scipy --with trimesh --with meshpy --with matplotlib --with typer --with pydantic --with pytest pytest research/a321-quality -q`와 Ruff 검사, 실제 Ego 시각 검사를 사용한다. 격자 gate가 통과했다고 저속 시험이 실행됐거나 벽처리 적합성이 검증됐다는 뜻은 아니다. 전체 절차·오류 수정·범위는 `evidence/recovery-20261108.json`을 따른다.
