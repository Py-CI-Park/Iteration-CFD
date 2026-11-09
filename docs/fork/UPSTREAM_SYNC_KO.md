# upstream 반영 절차

**결론: upstream 변경은 `sync/upstream-YYYYMMDD` 브랜치에서 merge하고, gate를 통과한 뒤 `v2.1.0-dev` → `main` 순서로 올린다. GitHub의 "Sync fork" 버튼은 쓰지 않는다.**

택배를 현관(sync 브랜치)에서 먼저 뜯어 확인하고 거실(dev)·진열장(main)으로 옮기는 방식이다. 포크 main에는 upstream에 없는 연구 커밋이 있으므로 GitHub "Sync fork"는 merge 커밋을 바로 main에 만들거나 거부한다. 그래서 수동 절차를 쓴다.

## 1. 언제 확인하나

- 새 작업 단계(M 단계)를 시작할 때마다 한 번.
- 또는 `tools/fork/sync-upstream.ps1`(점검 모드)를 주 1회 실행.

2026-11-09 기준: `upstream/main` = `1475bbf`(2026-10-27). 이미 a39d590으로 반영되어 **포크가 0커밋 뒤처져 있다.** upstream의 다른 브랜치(feat/cad, feat/gpu-gaps, feat/ontology, feat/t17, feat/mesh-2 등)도 모두 포함되어 있다.

## 2. 점검(읽기 전용)

```powershell
powershell -ExecutionPolicy Bypass -File tools/fork/sync-upstream.ps1
```

출력: upstream main의 새 커밋 수, 목록, 충돌 위험 파일(아래 4절)이 바뀌었는지.

## 3. 반영

```powershell
powershell -ExecutionPolicy Bypass -File tools/fork/sync-upstream.ps1 -Apply
```

스크립트가 하는 일:
1. working tree가 깨끗한지 확인(아니면 중단).
2. `git fetch upstream --tags --prune`.
3. `v2.1.0-dev`에서 `sync/upstream-YYYYMMDD` 생성.
4. `git merge --no-ff upstream/main` (충돌 나면 멈추고 파일 목록 출력).
5. push는 하지 않는다.

그 다음은 사람이(또는 오케스트레이터가) 직접 한다:

```powershell
# gate (모두 통과해야 다음 단계)
cargo build --release --manifest-path rust/Cargo.toml
cargo test --release --manifest-path rust/Cargo.toml --lib -- xref provenance_audit
npm --prefix gui test
powershell -ExecutionPolicy Bypass -File tools/fork/verify-a321-assets.ps1   # 핸드오프 핵심 자산 45개 해시
# 통과 후
git switch v2.1.0-dev; git merge --ff-only sync/upstream-YYYYMMDD; git push origin v2.1.0-dev
# 다음 main 반영 때 함께 올라간다
```

GPU가 필요한 `ofgpu-validate` 전체 실행은 upstream이 이미 측정한 기록을 따르고, 포크에서는 필요한 단계에서만 다시 잰다(측정하지 않았으면 "미실행"이라고 기록).

## 4. 충돌이 잘 나는 파일 (과거 merge 기록 기준)

| 파일 | 이유 | 처리 |
|---|---|---|
| `rust/PROVENANCE.md` | upstream 소스 목록 + 포크 A321 연구 출처 행 | 양쪽 행을 모두 유지 |
| `NOTICE` | 소스 파일 개수 문장 | merge된 트리에서 감사가 쓰는 find로 다시 센다 |
| `gui/package-lock.json` | 버전·의존성 | upstream 쪽을 받고 `npm install`로 재생성 |
| `docs/schema/*.json` | 생성 파일 | 쓰기 테스트로 재생성 |
| `.gitignore`, `.gitattributes` | 포크의 연구 예외 규칙 | 양쪽 규칙을 모두 유지 |

연구 폴더 `research/a321-*`는 upstream에 없으므로 보통 충돌하지 않는다.

## 5. 포크에서 upstream으로 기여할 때

포크 main에는 연구 커밋이 섞여 있다. upstream에 PR을 보낼 때는 **`upstream/main`에서 새 브랜치를 만들고** 필요한 커밋만 cherry-pick한다. 포크 main이나 dev에서 바로 PR을 열지 않는다.

```powershell
git fetch upstream
git switch -c contrib/<내용> upstream/main
git cherry-pick <커밋>
```

## 6. 기록

반영할 때마다 `docs/fork/ROADMAP_*.md`의 "upstream 반영 이력" 표에 날짜·upstream SHA·merge SHA·gate 결과를 한 줄 추가한다.
