# 외형 재구성 로드맵 작업 기록

이번 작업은 질문에 대한 직접 수행 범위·한계와 실행 계획을 문서화한 것이다. 새 R5, 새 CPU 격자, GPU probe/kernel/항공기 solver를 실행하지 않았다.

- 01: 기존 승인된 Ego 작업 공간 10 claim. 보고서는 p1, 기존 Studio는 p2로 adopt했다. NASA/Blender 공개 문서를 확인했다.
- 02: NASA CFD 절차·격자 수렴 원 페이지를 읽어 실제 주소·제목을 기록했다.
- 03: 최초 계획 HTML의 표 5개·로컬 링크 7개·390px 모바일 폭·문서/서버 SHA를 검사했다.
- 04: 실패 시 격자 재생성으로 돌아가는 C 분기를 명확히 하고 CPU-only 인수 경계를 추가한 최종본을 재검사했다. 별도 final QA와 final 스크린샷을 보존했다.
- 05: 최종 계획 보고서와 기존 Studio 탭을 사용자 확인용으로 남기고 finish 1회 완료했다.

렌더 명령은 저장소 루트에서 다음과 같다.

```powershell
uvx --from markdown markdown_py research/a321-quality/REBUILD_ROADMAP_KO.md -x tables -x fenced_code -x attr_list -f research/a321-quality/artifacts/rebuild-roadmap-body.html
```

생성된 fragment에 UTF-8 문서 head, report.css 링크, 목차 nav와 main을 붙여 별도 rebuild-roadmap.html로 저장했다. 기존 report.html과 실험 Markdown·측정 JSON은 수정하지 않았다. 과거 143개 테스트 통과는 기존 연구 결과이며 이번 문서 작업의 재실행 결과로 쓰지 않았다.

현재 결과: http://127.0.0.1:8776/a321-quality/rebuild-roadmap.html
최종 증거: ../evidence/rebuild-roadmap-final-qa.json
