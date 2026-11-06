# 검토와 미완료 범위

`review-work` 절차의 다섯 검토(목표/제약, 코드, custody, 실제 QA, 출처/기존 문맥)를 수행했다. 초기 판정은 FIX_FIRST였다. 생성 중의 누락 영수증과 실제 결함을 구분해서 처리했다.

## 수정한 결함

- 오목 다각형에 절댓값 fan 면적을 써 중심이 달라지는 문제: signed 면적 중심과 삼각형별 signed 체적·1차 모멘트로 수정했다. U형의 정확 중심과 warped cube의 정확 체적/중심으로 red→green 회귀를 만들었다.
- warped 3D 면의 투영이 교차할 때 평면 ear clipping으로 거부되는 경우: 실제 polygon 좌표를 fixture로 보존했다. 평면 non-star 면은 경계를 유지하는 ear clipping, 비평면 면은 명시한 native 3D center-fan을 사용한다. 이것을 임의의 warped 표면에 대한 전역 overlap 증명이라고 부르지 않는다.
- wall export의 자동 정점 병합으로 틈이 숨겨지는 문제: process=False와 원시 정점 ID의 signed edge incidence를 acceptance에 사용한다.
- `(7)` 좌표 broadcasting, 음수 serialized ID/잘못된 footer: 파서 경계에서 거부한다.
- 이전 감사 숫자와 현재 mesh를 섞을 수 있는 문제: 후보·원본 SHA와 다섯 mesh 파일의 현재 SHA 일치를 강제한다.
- 기존 결과 덮어쓰기·동시 실행: 배타적 trial/audit lock, 기존 mesh/log/processor 거부, 고정 R3 SHA·입력 manifest 검사로 차단했다. 실제 WSL 동시/기존/변경 입력 대조를 남겼다.

## 최종 상태를 제한하는 미해결 항목

요청한 비직교·폐합과 기본 CPU 검사에서는 snappy-03이 제한적 통과다. 사면체 경로는 통과하지 못했다. 확장 검사 3개 실패, 면적 기준 층 coverage 33.2675%, 미합의 형상 허용오차와 최대 46.3mm 표본 편차 때문에 **전체 engineering 판정은 계속 FIX_FIRST / GPU_HOLD**다.

23:18~23:19 KST의 초기 검토는 v2 수치 64.924°를 보았다. 수정된 적분 v4와 최종 snapshot guard를 거친 v5는 모두 66.204°이며 여전히 70° 이하이다. 초기 검토를 v5 재실행 증거로 바꾸어 쓰지 않는다. 검사 명령·범위·재검토는 `evidence/verification.json`과 `evidence/review-closeout.json`에 별도로 남긴다.

Studio의 최초 `loading` 영수증을 완료로 간주하지 않았다. 이후 실제 완료 manifest·DOM·계산 벽·3D viewer 화면을 저장했다. 압력/속도/공력 계수나 GPU 시험은 생성하지 않았다.
