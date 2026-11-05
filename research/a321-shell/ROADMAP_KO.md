# A321 공력 전용 외피 연구 로드맵

2026-11-05. 브랜치 `codex/a321-aero-shell-20261105`, 출발 `1769b06e0b7a9ec46eaa5823d74532ca87a9de1f`.

목표: 기존 G1B native를 측정 기준으로 고정하고, 내부·장식·개구를 제거한 별도 외피를 생성한다. 이는 A321 기반 대칭·단순화 연구 모델이며 OEM 형상/성능 인증이 아니다. Blender CLI로 새 형상을 작성하고 CPU로 폐합·정점 link·자기교차/Boolean 유효성·STL 왕복을 검사한다. GPU 수치 계산·렌더·probe는 실행하지 않는다.

| 단계 | 수행 예정 | 통과/중단 조건 |
|---|---|---|
| A0 기준선 | authored G1B SHA, 좌표·객체·단면·범위 고정 | 원본 SHA 불일치 시 정지 |
| A1 형상 설계 | 동체 단면 외곽, 우현 주익·수평미익 단면, 수직미익 단면 추출 | 후보와 원본 차이·가정 기록 |
| A2 새 외피 | Blender loft/삼각화, 좌우 대칭, 뿌리 접합 CPU union | 열린 면·뒤집힘·자가접촉 검사 |
| A3 검증 | 독립 STL·정점 link·체적·단면·거리·왕복 검사 | 불합격은 HOLD, 임계값 완화 금지 |
| A4 계산 준비 | 30m/s·2도 조건, 기준면적·바람축·경계조건·격자계획 | 형상 정확도/실험 validation 분리 |
| A5 CPU 격자 | 지원 도구·CPU 의존성 확인, 가능시 소형 체적격자/품질검사 | CUDA 경로는 호출하지 않음; 자원/기능 실패 기록 |
| A6 전달 | Ego Lite 보고서/뷰어, Blender 사본, 재현 명령, commit/push | 공개 포크에 secret/원본 대형모델 업로드 금지 |
| STOP | GPU probe/solver/validation 직전 | 새 계산 실행 결정 필요 |

기준 native는 Aircraft-Workbench의 `A321_NATIVE_G1B_LOCAL_NORMAL_ENCODING_RESEARCH.blend`, SHA256 `1fd3cfd08b1dbf5e5f2fb288caf9846ad149ff8839a37cc2e4c2c8074bc1073c`, 38,570,017 bytes. native X=기수→꼬리, Y=우현+, Z=위, m. 원본은 읽기 전용. 이전 실패 복셀 후보를 새 외피의 기준으로 쓰지 않는다.

초기 범위는 동체+주익+수평/수직미익. 엔진·파일런·기어·샤클렛·개별 고양력장치 슬롯은 생략/통합 여부를 모델 설명에 명시한다. 공개 자료에 없는 단면을 정확한 실기 단면이라고 주장하지 않는다. 외곽 단면 재구성과 좌우 대칭 적용은 별도 변경으로 기록한다.

NASA [분석 절차](https://www.grc.nasa.gov/www/wind/valid/tutorial/process.html)·[V&V 입구](https://www.grc.nasa.gov/www/wind/valid/tutorial/tutorial.html)의 목적→형상/조건→격자→계산→보존/수렴→민감도→실험 비교→문서화 계보를 따른다. 이전 `../a321-preflight/evidence/nasa-*.json` 보존 기록과 새 Ego Lite 확인을 연결한다.
