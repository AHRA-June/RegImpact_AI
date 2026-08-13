# CHANGELOG — E2E 파이프라인 (Walking Skeleton)

> 최신이 위. 각 항목은 해당 버전 파일(`workflow-e2e_vN.md`)의 변경 요약이다.

## v7 (2026-08-13)
- [8] Validation Report 정식 HTML(서사 Phase 3) → **정식 15~20쪽 분석 서사 완성**
  (`docs/reports/validation_report_6_30_full.md`, 약 17쪽). 코어 완성 정의(브리프 §18) 충족.
- 이전(v6) 대비 상세: `workflow-e2e_v7.md` 상단 "변경 이력" 참고.

## v6 (2026-08-13)
- [6] Assurance 부분(실측) → **4 dimension 스코어카드 완성**(누락 3지표 추가 + 확정 임계값 Strict,
  6·30 12/12 PASS). 매핑을 신규 `features/assurance-scorecard`로. 테스트 96→110.
- 이전(v5) 대비 상세: `workflow-e2e_v6.md` 상단 "변경 이력" 참고.

## v5 (2026-08-13)
- [8] Validation Report stub(md) → **정식 HTML 보고서 추가**(`render_report_html`, DESIGN.md 시스템).
  demo_e2e가 md+html 동시 산출. [5] 격자 3,200 반영. 테스트 92→96. 정식 15~20쪽 서사는 Phase 3.
- 이전(v4) 대비 상세: `workflow-e2e_v5.md` 상단 "변경 이력" 참고.

## v4 (2026-08-13)
- [6] Exception Recall 50%→100%(서민·실수요 보완) 반영. **하위 지표 수치를 워크플로우 문서에
  하드코딩하지 않고 features/extractor-assurance 참조로 디커플링**(반복 버전 churn 방지).
- 이전(v3) 대비 상세: `workflow-e2e_v4.md` 상단 "변경 이력" 참고.

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
