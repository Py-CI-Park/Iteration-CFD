# 포크 운영 기준 — Py-CI-Park/Iteration-CFD

**작성 2026-11-09 KST. 결론: 이 포크의 main은 upstream `using76/Iteration-CFD` main(1475bbf, 2026-10-27)과 A321 공력 연구(R0~R5 핸드오프)를 모두 담는다. 다음 작업은 `v2.1.0-dev`에서 갈라진 feature 브랜치에서만 한다.**

이 포크는 원 저장소(upstream)를 따라가는 "지점"이다. 본점의 새 물건(upstream 커밋)은 정해진 통로(sync 브랜치)로만 들여오고, 지점의 자체 상품(연구)은 지점 진열대(fork main)에만 둔다.

## 1. 원격(remote)

| 이름 | 주소 | 용도 |
|---|---|---|
| `origin` | https://github.com/Py-CI-Park/Iteration-CFD | 이 포크. push 대상 |
| `upstream` | https://github.com/using76/Iteration-CFD | 원 저장소. **fetch만** 한다. push 금지 |

새 clone에서는 `git remote add upstream https://github.com/using76/Iteration-CFD.git`를 한 번 실행한다.

## 2. 브랜치 체계

```text
upstream/main ──(sync/upstream-YYYYMMDD)──┐
                                           v
main  ◄── 검증된 통합선(안정). 직접 커밋 금지, ff 또는 merge만
  │
  └─ v2.1.0-dev  ◄── 현재 개발선. 모든 feature가 여기서 출발·복귀
        ├─ feat/a321-m3-c15-map        (M3 P0: C 자기교차 15곳 지도)
        ├─ feat/a321-...               (이후 M1~M9 단계별)
        └─ sync/upstream-YYYYMMDD      (upstream 반영 전용)

보관(동결): codex/a321-aero-shell-20261105  ← 핸드오프 문서가 이름으로 참조. 삭제·추가커밋 금지
```

| 브랜치 | 규칙 |
|---|---|
| `main` | `v2.1.0-dev`가 단계 gate를 통과했을 때만 ff/merge. 사람이 직접 커밋하지 않는다 |
| `v2.1.0-dev` | 소유자 규칙의 `v*.*.*-dev` 개발선. 숫자 2.1.0은 "upstream 2.0.0 이후"라는 뜻이며 upstream 릴리스 번호를 선점하지 않는다 |
| `feat/<영역>-<내용>` | 한 단계(M1~M9 중 하나)나 한 결함만 담는다. 단계마다 커밋·push |
| `sync/upstream-YYYYMMDD` | upstream 반영 전용. [UPSTREAM_SYNC_KO.md](UPSTREAM_SYNC_KO.md) 절차를 따른다 |
| `codex/a321-aero-shell-20261105` | 2026-11-09 핸드오프 시점 동결. 다른 PC의 clone 명령이 이 이름을 쓴다 |

## 3. 버전·태그

- **`v*` 태그는 upstream 전용이다.** upstream이 `v0.1.0`, `v2.0.0`을 쓰고 있고, 앞으로 `v2.1.0` 같은 태그를 만들 수 있다. 포크가 같은 이름을 만들면 `git fetch upstream --tags`가 충돌한다.
- 포크의 이정표 태그는 `a321-<이정표>-<YYYYMMDD>` 형식의 annotated tag로 만든다.
  - `a321-handoff-20261109` → 39acb4a (R5 핸드오프, M3 FAIL 상태 보존)
  - 예정: `a321-m3-pass-…`, `a321-m5-mesh-pass-…`, `a321-first-gpu-…`
- `rust/Cargo.toml`과 `gui/package.json`의 버전(2.0.0)은 upstream 값이다. 연구 작업으로 올리지 않는다(솔버 수치 코어를 바꾸지 않으므로).
- 이정표 태그를 만든 뒤 개발선이 바뀌어야 하면(예: upstream이 v2.1.0을 릴리스) 다음 개발선 `v2.2.0-dev`를 만든다.

## 4. worktree

| 폴더 | 브랜치 | 주의 |
|---|---|---|
| `D:\Chanil_Park\Project\Programming\Iteration-CFD` | `main` | 통합·문서·릴리스 작업 |
| `D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight` | `feat/a321-m3-c15-map` | **git이 추적하지 않는 대형 격자(snappy-01~11 등)가 이 폴더에만 있다.** `git worktree remove`·`git clean` 금지 |

## 5. 커밋 규칙

- `git commit -s`(CONTRIBUTING). 한글 커밋 메시지 사용.
- 형식: `<type>: <설명>` (feat, fix, docs, test, chore, research …).
- 연구 결과는 새 후보·새 영수증으로 남긴다. 기존 영수증·로그를 고치지 않는다.

## 6. 관련 문서

- [upstream 반영 절차](UPSTREAM_SYNC_KO.md)
- [통합 정리·재시작 로드맵 2026-11-09](ROADMAP_20261109_KO.md)
- [A321 핸드오프](../../research/a321-quality/HANDOFF_20261109_KO.md) · [현재 상태](../../research/a321-quality/EXECUTION_STATUS_KO.md)
