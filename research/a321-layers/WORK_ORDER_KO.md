# R3 보존 경계층 재연구

입력: R3 STL SHA256 `2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745`, 같은 branch `codex/a321-aero-shell-20261105`, base `ab176ae27e5368c58900162ef4435e0c0a7957c0`.

목표: 비뒤집힘 층·비직교·폐합 개선과 Ego Lite Studio 확인·commit/push. GPU 항공기 solver는 품질 통과 전 금지. 이번에는 GPU 진단 재실행도 필요하지 않음. paid AI/API는 사용자 허용 범위이나 핵심 수치 판단은 실제 측정으로 수행.

가설 H1 tiny boundary triangles → edge cap 붕괴/옆면 비직교. H2 concave junction averaged normals → face tangency/층 충돌. H3 cell centroid 또는 warped quad 방향/부동소수점 계산 → closure 비정상. 독립 작은 analytic mesh test와 표면 재분할/법선장 대조로 구분.

원 R3 좌표 파일과 모델은 보존한다. 새 계산표면은 별도 artifact로, 거리/면적/위상/원 SHA를 기록하고 전체 형상 보존과 허용오차 근사를 구분한다. 기존 실패 gate≤70도/closure≤1e-10은 완화하지 않는다. layer coverage·Jacobian·interface conformity를 별도로 평가.
