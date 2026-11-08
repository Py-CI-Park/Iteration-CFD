# R3 보존·R4 국소 표면 개선·CPU 격자 연구 조작 기록

시작 HEAD b2de364, 연구 브랜치 codex/a321-aero-shell-20261105. 사용자 지시에 따라 기존 Ego TaskSpace 10을 claim하고 Studio p1·보고서 p2를 이어서 사용했다. 모델링은 Blender CLI와 독립 CPU 기하 프로그램, 실제 표시는 Ego Lite Studio에서 수행했다. 항공기 CFD/GPU solver는 실행하지 않았다.

| 원장 | 실제 결과 |
| --- | --- |
| 01~02 | 기존 작업 공간 claim 및 기존 Studio·보고서 탭 adopt. 새 우회 작업 공간을 만들지 않음. |
| 03~06 | R3 형상 캐시의 positions.bin 교체 EPERM 확인. 해당 생성 캐시를 보존·격리하고 같은 Studio에서 재읽기 성공. reload 한 번은 timeout 후 실제 온라인 상태 확인. 원 R3 파일 미저장. |
| 07~08 | R4 실제 STL 로딩 성공. 최초 대기는 숨은 R3 탭 DOM을 읽어서 실패했으며 visible geometry-info 조건으로 실제 R4를 확인해 촬영. |
| 09 | OpenFOAM layer/mesh-quality 공개 문서를 실제 브라우저에서 읽고 주소·문구 위치를 기록. 설치 실행기 v1912와 문서 버전은 구별. |
| 10~11 | 동일 자동 맞춤 초기 시점에서 같은 확대 입력으로 R3/R4 촬영. R4 촬영은 최소화 오류 후 같은 창을 복원했으며 확대 입력을 중복 적용하지 않음. |
| 12~13 | 08 진단 케이스의 최초 load가 evaluate 대기 시간을 넘었지만 후속 상태에서 완료를 확인. load를 반복하지 않고 정확 cellCount·진단 field 확인 후 전체 벽 및 날개 격자 촬영. |
| 14 | 08 y=10m 실제 cell cut 생성(6399 표시 삼각형). 표시는 가능했으나 화면에서 내부 격자선·첫 층 두께 식별이 충분하지 않아 본문의 근벽 높이 검증 근거로 사용하지 않음. |
| 15 | NASA 사용자 제공 CFD V&V 튜토리얼 원 URL을 실제 열어 제목과 접근 기록 보존. |
| 16~17 | 11 진단 케이스 941938셀 로딩. 고정 0~8 범위와 동일 시점의 전체 벽·날개·격자선 촬영. |
| 18 | 10 진단 케이스 1011614셀을 같은 범위·시점에서 촬영해 buffer 1→3 비교 가능하게 구성. |
| 19 | 최종 HTML 이미지 25개 decode, 고유 로컬 링크 82개 HEAD 200, 파일/서버 HTML SHA 일치. PC·390px 모바일, 이전 원문 4개 모두 펼친 상태도 가로 넘침 없이 확인. |
| 20 | Studio는 10 전체 항공기 시점으로 돌려두고, Studio·최종 보고서 두 탭만 사용자 확인용으로 유지해 finish 1회 완료. |

후속 보고서 QA 조작과 결과는 번호가 이어지는 스크립트 및 evidence/surface-report-qa.json에 남긴다. 검증 완료 후 Studio와 최종 보고서를 사용자 확인용으로 남긴다. TaskSpace가 finish된 뒤에는 같은 page label을 자동 재사용하지 않는다.

다시 실행할 때는 종료된 조작 원장을 통째로 재생하지 않는다. 현재 case·프로세스·작업 공간을 먼저 확인한다. 생성·감사·지도는 기존 출력 거부·실행 lock·입력 해시 검사를 유지한다. 재현 순서는 원 입력 확인 → 새 이름의 형상/CPU 실험 준비 → 외부 CPU mesher → 독립 audit → clone bound check → 명시적 zero 정규화 → seal/map → 진단 표시 복사본 → 결과 패키징 → HTML 렌더·실제 Ego QA다.

R3와 03~07은 보존했다. 08~11은 새 실행이며 clone check는 mesh를 다시 생성하지 않는 별도 확장 검사다. 현재 2종 확장 실패가 남았으므로 engineering/GPU 상태는 HOLD다. 상세한 변경·시험·미실행 범위는 ../evidence/surface-study-closeout.json을 따른다.
