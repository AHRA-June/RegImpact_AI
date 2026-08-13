# CHANGELOG — E2E 파이프라인 (Walking Skeleton)

> 최신이 위. 각 항목은 해당 버전 파일(`workflow-e2e_vN.md`)의 변경 요약이다.

## v3 (2026-08-13)
- **[6] Assurance 첫 실측치 E2E 연결.** demo_e2e가 저장 추출을 로드해 채점 하네스로 실측한 수치를
  검증보고서 [6]에 표기 → 전 노드([2]~[8]) 관통 표기. 테스트 72→75.
- 이전(v2) 대비 상세: `workflow-e2e_v3.md` 상단 "변경 이력" 참고.

## v2 (2026-08-13)
- **핵심 관통 완료.** [4] Rule Change Proposal(⬜→✅, `proposal/`), [7] Human Review(→✅ approval envelope),
  [8] Validation Report(⬜→✅ stub, `validation/`) 구현으로 [2]→[3]→[R]→[4]→[7]→[5]→[8] 관통.
- `is_pipeline_complete` 판정 추가, E2E 데모(`examples/demo_e2e.py`) 추가. 테스트 +14(총 72).
- 이전(v1) 대비 상세: `workflow-e2e_v2.md` 상단 "변경 이력" 참고.

## v1 (2026-08-13)
- 최초 작성 (신규). 파이프라인 노드 간 데이터 계약과 구현 현황 스냅샷.
- 관통: [2]Extractor→[3]Impact Matrix→[R]룰엔진→[5]TC/Regression + [3a]UI. 미구현: [4]Proposal, [7][8]Report.
- 이전 버전 없음.
