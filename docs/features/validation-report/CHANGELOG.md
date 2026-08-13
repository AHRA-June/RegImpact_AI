# CHANGELOG — Validation Report (검증보고서 stub)

> 최신이 위. 각 항목은 해당 버전 파일(`validation-report_vN.md`)의 변경 요약이다.

## v3 (2026-08-13)
- **정식 15~20쪽 분석 서사 완성**(`docs/reports/validation_report_6_30_full.md`, 약 17쪽/28.8k자).
  모델검증 보고서 형식(Executive Summary·방법론·Dimension별 발견·룰엔진 심층·고위험 실패 분석·한계·권고·부록).
  v2의 "정식 서사 Phase 3" 제약 해소. 자동 요약본(md/html)과 별개의 authored 문서.
- 이전(v2) 대비 상세: `validation-report_v3.md` 상단 "변경 이력" 참고.

## v2 (2026-08-13)
- **정식 HTML 보고서 `render_report_html()` 추가.** DESIGN.md 디자인 시스템 기반 self-contained,
  7개 섹션 데이터바인딩(하드코딩 없음). demo_e2e가 md + html 동시 생성(`validation_6_30.html`).
- HTML 렌더 테스트 4건(전체 96). 정식 15~20쪽 분석 서사는 Phase 3(내용 깊이는 미포함).
- 이전(v1) 대비 상세: `validation-report_v2.md` 상단 "변경 이력" 참고.

## v1 (2026-08-13)
- 최초 작성 (신규). 기능단위 문서화 시작.
- 대상 구현: build_report(노드 산출 조립), is_pipeline_complete 관통 판정,
  format_report_md(정직성 섹션 포함). 테스트 7건. 산출물 docs/reports/validation_6_30.md.
- 이전 버전 없음.
