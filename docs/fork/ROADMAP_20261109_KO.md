# 통합 정리·재시작 로드맵 (2026-11-09)

**결론: A321 연구 브랜치(39acb4a)를 main에 fast-forward로 반영했고, upstream 최신(1475bbf)도 함께 들어왔다. 연구는 M3 FAIL(R5-C 자기교차 15곳) 지점에서 멈춰 있으며, 재시작 첫 작업은 이 15곳의 위치 지도다. 항공기 GPU 해석은 계속 금지(HOLD)다.**

기준 문서는 [A321 핸드오프](../../research/a321-quality/HANDOFF_20261109_KO.md)다. 이 문서는 그것을 고치지 않고, 포크 전체 관점의 정리·계획만 담는다.

## 1. 이번 정리에서 한 일

| 항목 | 결과 |
|---|---|
| main 반영 | `main` 8099602 → **39acb4a** (`--ff-only`, 427커밋: upstream 411 + A321 연구 16) |
| upstream | `upstream` remote 추가(using76/Iteration-CFD). upstream/main 1475bbf 포함 확인 — 뒤처진 커밋 0 |
| 자산 확인 | 핸드오프 핵심 자산 45개 SHA256 main 체크아웃에서 일치(0 불일치) |
| 이정표 태그 | `a321-handoff-20261109` → 39acb4a |
| 개발선 | `v2.1.0-dev` 생성 (main 기준) |
| 재시작 브랜치 | `feat/a321-m3-c15-map` — 기존 연구 worktree에서 전환(로컬 대형 격자 유지) |
| 정리 | 로컬 전용 `codex/a321-cfd-preflight-20261104` 삭제(연구 브랜치에 이미 포함). `codex/a321-aero-shell-20261105`는 동결 보관 |
| 운영 문서 | [포크 운영 기준](README_KO.md), [upstream 반영 절차](UPSTREAM_SYNC_KO.md), `tools/fork/sync-upstream.ps1`, `tools/fork/verify-a321-assets.ps1` |
| 로컬 변경 | main 체크아웃의 `gui/package.json` allowScripts(esbuild) 로컬 변경은 커밋하지 않고 그대로 둠 |

## 2. 지금까지 한 연구 (2026-11-04 ~ 11-09)

```text
R0 원본 감사 ── R2 공력 shell ── R3 보존 shell ── R4 국소 개선 ── R5-A/B/C 재구성
  c3b4a9b         6d4bfed          ab176ae~c5295b0    9b132e6          39acb4a
                                    │
                         hex/poly 대안 snappy-03: 기본 CPU gate PASS
                         (비직교 66.2°≤70°, 폐합 8.3e-15, 음수체적 0)
                         확장 검사 3종 FAIL · 경계층 미완성
```

| 후보 | 삼각형 | 독립 자기교차 | 판정 |
|---|---:|---:|---|
| R3 원본 대조 | 보존 | 72 | 원본도 문제 있음 |
| R4 국소 개선 | 보존 | 86 | 전체 재구성 아님 |
| R5-A | 761,090 | 4,184 | 내부 위상 PASS / 독립 FAIL |
| R5-B | 미생성 | — | 허용오차 1µm < kernel 최소 5.306µm로 생성 전 거부 |
| R5-C | 305,764 | **15** | 내부 PASS / **M3 FAIL** |

## 3. 잘못된 것·남은 결함 (핸드오프 §7 기준, 우선순위 순)

| 우선 | 결함 | 고칠 방법 |
|---|---|---|
| **P0** | R5-C 자기교차 15곳 | 좌표·삼각형·부품·feature 지도 → 원인 분리 → 새 후보에서 0곳 |
| P1 | 극소·긴 삼각형(최소 quality 9.7e-13), 다각형 단면, Boolean 접합 | 적응형 tessellation, LE/TE/tip/wing-body 전이 설계, 새 형상 계약으로 사전 고정 |
| P1 | feature 설계(kink·rounding·두께·곡률 지표) 부분만 있음 | M1 계약 02로 확정 |
| P1 | C native 메타데이터에 R4 설명·mesh명 잔존, C raw 파일명이 `..._R5_B.stl` | 별도 이름 파생본에서 정정 + 새 SHA + 재읽기. 원본·영수증은 수정 금지 |
| P1 | R5-A/C Studio 화면·Ego 시각 QA 미완료 | space15 생존 확인 → 원본/신규 비교 스크린샷 |
| P1 | A 생성 당시 코드 ≠ 사후 보강 코드 | 재현(보존 모델 재사용)과 재생성을 구분해 기록 |
| P1 | 최종 5분야 코드 리뷰 미종결 | B/C helper·Blender adapter 별도 재검토 |
| P1 | 엔진 host-only(CPU) 인수 경로 없음. lowmach `-iters0`도 GPU 초기화 | `Gpu::new` 이전 host-only 검사 경로 설계·회귀 |
| P2 | B/C runner 중복, label 잔여 | 다음 버전에서 모듈화. 동결 코드는 보존 |
| P2 | gui 테스트 기존 실패(dc.seed anchor 등, upstream 기록) | upstream 인계 사항. 포크에서 고치면 upstream 기여 후보 |

## 4. 재시작 로드맵

```text
[M0 보존] DONE
   │
[M1 feature 계약] PARTIAL ◄──────────────┐
   │                                     │
[M2 새 곡면] A/C DRAFT                   │
   │                                     │
[M3 독립 형상 검사] C FAIL 15 ── 지도·원인·새 후보 (← 지금 여기, feat/a321-m3-c15-map)
   │ PASS
[M4 물리·경계층 설계] → [M5 새 CPU 격자 + 확장 검사]
   │
[M6 엔진 host-only 인수] → [M7 sm_89 빌드·장치·VRAM]
   │ 모든 gate PASS
[M8 첫 항공기 GPU 시험] → [M9 수렴·민감도·검증]
```

| 단계 | 브랜치(예정) | 완료 기준 | 예상 소요 |
|---|---|---|---|
| M3-a C15 지도 | `feat/a321-m3-c15-map` | 15곳 각각 좌표·삼각형 쌍·부품·feature 분류 JSON + 시각 자료 | 산정 불가 |
| M3-b 원인 분리·새 후보 R6 | `feat/a321-r6-candidate` | 새 계약 사전 고정, 독립 surfaceCheck 0곳, 내부 위상 PASS | 산정 불가 |
| M1 계약 02 | `feat/a321-m1-contract-02` | feature 목록·허용치 확정 | 산정 불가 |
| 메타데이터 정정 | `fix/a321-r5c-metadata` | 새 이름 파생본, 기하 동일·새 SHA·재읽기 | 산정 불가 |
| M4 물리 명세 | `feat/a321-m4-physics` | 30 m/s·0° runnable 물리 명세 | 산정 불가 |
| M5 CPU 격자 | `feat/a321-m5-mesh` | 비직교≤70°, 폐합≤1e-10, 확장 3종 PASS, 층 손실 없음 | 산정 불가 |
| M6 host-only 경로 | `feat/a321-m6-hostonly` | GPU 없이 case load·검사 | 산정 불가 |
| M7 GPU 준비 | `feat/a321-m7-gpu-prep` | sm_89 빌드, SUPER UUID, VRAM·기준문제 | 산정 불가 |
| M8/M9 | 별도 계획 | — | 산정 불가 |

예상 소요는 과거 같은 작업의 측정 기록이 없어 쓰지 않는다. 첫 Worker 결과가 나오면 그 실측으로 다시 잡는다.

## 5. 병렬로 할 수 있는 일

- M3-a(지도)와 메타데이터 정정은 서로 다른 파일만 만든다 → 병렬 가능.
- M6 host-only 설계(코드 읽기)는 형상과 독립 → 병렬 가능. 단, 수치 코어 변경은 upstream maintainer 계약 대상이라 설계 문서까지만.
- M5 이후는 M3 PASS 전 시작 금지.

## 6. 작업 방식

- Opus: 계획·판정·통합. Codex `gpt-6.1-sol`: 구현·분석 Worker(라벨 `<model>-<effort>:<role>`). 어려운 설계는 `astra-6`. Codex 사용 불가 시 Claude Sonnet.
- Codex 사용량은 10% 남을 때까지 사용(소유자 2026-11-09 승인).
- Worker는 단계마다 커밋·push. 결과는 독립 검토 후 통합.
- 기준 완화 금지. 실패 영수증 보존. 측정하지 않은 것은 "미실행"으로 기록.

## 7. upstream 반영 이력

| 날짜 | upstream SHA | 포크 merge | gate |
|---|---|---|---|
| 2026-11-07 | 1475bbf | a39d590 (연구 브랜치) | 항공기 solver·GPU 미실행 (merge 커밋 기록) |
| 2026-11-09 | 1475bbf (변화 없음) | main ff → 39acb4a | 핸드오프 자산 45/45 일치. cargo·gui 테스트 이번에 미실행 |
