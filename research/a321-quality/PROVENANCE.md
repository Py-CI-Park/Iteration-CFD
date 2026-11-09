# A321 표면·격자 연구 코드 출처

이 연구의 신규 도구는 보존된 R3 단면 원장과 STL, 별도 실행한 OpenFOAM v1912의 입출력, 공개 API 문서를 바탕으로 작성했다. OpenFOAM·Blender 등 GPL 구현 소스를 읽거나 복사하지 않았으며 Rust/CUDA 솔버 수치 코드를 변경하지 않았다.

| 파일 | 작성 근거·역할 |
| --- | --- |
| smooth_loft.py / test_smooth_loft.py | 원 R3 단면 원장, 3차 Hermite의 끝점·접선 보간과 국소 이동 상한. 앞전·뒷전 유지·기하 변경·과도 이동 거부·출처 해시 회귀. 별도 Manifold CPU API로 합집합 구성. |
| prepare_surface_trials.py / test_surface_trials.py | 기존 06의 고정 입력 바이트를 복제하는 독립 실험 준비·변조 거부. |
| run_surface_trial.sh | OpenFOAM 외부 CLI만 호출. 입력·R3·파생 형상 원장 검증 후 CPU 생성·재구성·검사. 실제 실행본을 각 lock에 보존. |
| normalize_zero_sets.py / test_normalize_zero_sets.py | 외부 검사 실행 로그의 명시적 통과 문구에만 연결하는 빈 진단 집합. 미측정·누락을 0으로 취급하지 않음. 설치 바이너리 출력 문자열만 대조하며 구현 소스 미열람. |
| run_bound_check.sh | 원 격자와 진단을 보존한 별도 복사본에서 실제 constant 확장 검사를 반복한다. source/clone mesh·set의 전후 해시와 두 로그를 연결한다. 유동 solver를 실행하지 않음. |
| bound_check_models.py / bound_replay.py / test_bound_replay.py | 재검사 sidecar의 typed 데이터 모델과 원본·clone·constant 실행 경로·해시를 결합하는 검증. 새 합성 zero 추가는 영수증에 명시된 항목만 허용하는 별도 회귀. |
| zero_set_test_support.py | 정상·위조·불완전 native 로그와 source/clone 결합을 격리 fixture에서 만드는 테스트 전용 지원 코드. 실제 연구 결과를 만들거나 대체하지 않음. |
| package_surface_trials.py / test_package_surface_trials.py | 직렬화 격자·원시 로그·층수 지도·해시를 묶는 연구 비교 기록과 격리된 입력·출처 결합 회귀 테스트. 수용 기준을 바꾸지 않음. |
| surface_package_checks.py | 복사 실패 시 자신이 만든 파일만 정리하고, 완결된 native 로그·합성 zero의 역사 기록·새 bound 재검사 증거를 교차 확인하는 typed 보조 도구. 테스트는 test_package_surface_trials.py에 포함. |
| native_surface_binding.py / test_native_surface_binding.py | 공개 binary STL 레코드 형식과 동결 STL 해시를 기준으로 NPZ 정점·면의 삼각형 대응을 확인하는 독립 연구 도구·테스트. 같은 배열 크기의 좌표 치환·뒤집힌 winding·STL 해시 변경을 거부하는 계약. 솔버 수치나 공학적 형상 인수를 대신하지 않음. |
| plot_smooth_geometry.py | 동결된 R4 생성 원장의 실제 보간 폭을 사용한 단면 궤적·기울기 비교. 유동 해석 그림이 아님. |
| blender_r4.py | 독립 작성한 별도 Blender bpy 프로그램. R4 native 저장 및 새 프로세스의 좌표·삼각형 정확 재읽기. GPL-2.0-or-later outbound 분류는 기존 ../a321-shell/LICENSE-NOTICE.md 정책을 따름. 솔버에 연결하지 않음. |
| smooth-gallery/*.mjs | Ego Lite 실제 화면 조작과 앱 API 기반 표시 검증 원장. 로딩 성공·렌더링은 공학적 검증과 구별. |

`smooth-gallery/01`~`12`의 저장된 `.mjs`에는 실행 후 출처·라이선스 주석 헤더를 추가했다. 이 보완에서 기존 스크립트 본문 바이트는 그대로 보존했으며, 헤더를 포함한 현재 파일 전체가 실행 당시 원본 코드와 바이트 동일하다고 주장하지 않는다. 기존 화면·출처 receipt를 새로 실행한 기록으로 취급하지 않는다.

`blender_r4.py`는 기존 [Blender research adapter outbound notice](../a321-shell/LICENSE-NOTICE.md)에 따라 **GPL-2.0-or-later로 배포하는 별도 Blender 프로그램**이다. 독립 작성한 bpy 조작 어댑터로서 GPL 구현 소스를 읽거나 복사하지 않았으며 Rust/CUDA 솔버에 링크하지 않는다. 이 outbound 분류는 솔버·다른 연구 코드의 루트 라이선스를 변경하거나 OEM 형상의 권리를 주장하지 않는다.

공개 파라미터 참고: [OpenFOAM layer controls](https://doc.openfoam.com/2212/tools/pre-processing/mesh/generation/snappyhexmesh/layers/), [mesh quality controls](https://doc.openfoam.com/2606/tools/pre-processing/mesh/generation/snappyhexmesh/meshquality/). 문서 버전과 설치 실행기 v1912는 다르므로 실제 저장 로그로 결과를 판정한다. 문서의 권장값을 항공기 공학적 합격 기준으로 승격하지 않는다.

새 모델은 R3와 구분한 연구 파생 형상이며 OEM 형상 정확도·공력 성능은 미검증이다. GPU/항공기 솔버를 실행하지 않는다.

## 2026-11-09 중단 복구 스냅샷

| 파일/범위 | 작성 근거·분류 |
|---|---|
| rebuild/*.py, rebuild/surface_check.sh, rebuild/test_*.py | 독립 작성한 원 단면 궤적·삼각분할·CPU union·바이트 custody·native binding·회귀. 세부 파일별 근거는 rebuild/PROVENANCE.md. 공개 API/형식·별도 외부 CLI만 사용, GPL 구현 소스 참조 없음. |
| r5_cleanup_trial.py / r5_cleanup_c_trial.py / test_r5_cleanup_guard.py | 공개 manifold3d simplify/get_tolerance, NumPy/SciPy/trimesh API 및 원 형상 계약. B는 상한 거부, C는 별도 사전 계약의 CPU 실험. test guard 원본에는 저장소 헤더가 누락돼 있으며 이 실행 스냅샷의 미해결 소스 메타데이터로 남긴다. 기능/실행 증거를 소급 변경하지 않는다. |
| r5_c_surface_check.sh / r5_c_surface_check02.sh | 설치 OpenFOAM1912 공개 help와 외부 CLI만 사용. 01은 입력이름 부재 거부, 02가 실제 검사. 새 원시 로그로만 재실행. |
| blender_r5c.py | 기존 독립 Blender adapter를 C용으로 파생. GPL-2.0-or-later 별도 bpy 프로그램, 솔버 링크 없음. C geometry binding 통과와 R4 설명/명명 잔여 결함을 동시에 기록. |
| rebuild/artifacts/rebuild-r5-{a,b,c}/ | 재개용으로 명시 수록한 실패 형상·배열·실행 코드 사본·입력 원장. accepted CFD 모델 아님. executed-code.py는 당시 runner의 바이트 동결본이며 출처/라이선스는 각 원 runner와 동일. |
| execution-gallery/*.mjs | 독립 Ego Lite task-space/public-app API 조작 기록. 최신 화면 검사 성공으로 소급 해석하지 않음. |
| HANDOFF*.md / 실행상태 / HTML / handoff evidence | 전달된 요청·로컬 Git·보존된 원시 영수증의 인계 정리. 새 CFD/GPU/mesher 실행 아님. |

A의 생성 전 계약/입력 동결과 생성 후 코드 snapshot·안전 보강 시점은 구분한다. 모든 raw receipts는 보존하며 최종 상태는 별도 follow-up 영수증으로 연결한다. 기존 R3/R4·대형 CPU mesh에는 쓰지 않았다.
