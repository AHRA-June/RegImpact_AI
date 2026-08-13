# 기능단위: Validation Report (검증보고서)

> **버전:** v2   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v1 (`validation-report_v1.md`)

## 변경 이력 (v1 → v2)
- **[범위]** **정식 HTML 보고서** 추가: `render_report_html(report)` — 마크다운 stub에 더해
  DESIGN.md 디자인 시스템(Institutional Navy·Noto Sans·JetBrains Mono·상태색) 기반 self-contained
  HTML 렌더. 7개 섹션(관통현황·추출·영향매트릭스·룰제안·회귀·Assurance·한계) 데이터바인딩.
- **[범위]** `demo_e2e.py`가 `docs/reports/validation_6_30.html` 동시 생성(md + html).
- **[검증]** HTML 렌더 테스트 4건(실데이터 바인딩·전 노드 표기·부분관통·환각값 부재). 전체 96 통과.
- **[제약]** 여전히 '프레젠테이션 골격' — 정식 15~20쪽 분석 서사는 Phase 3(내용 깊이 미포함).

---

## 1. 목적·책임
파이프라인 각 노드의 **실제 산출을 하나의 검증보고서로 조립**한다(Walking Skeleton [8]).
마크다운(로그·CI)과 **정식 HTML**(프레젠테이션·포트폴리오) 두 형식으로 렌더한다.
present/missing·사람검토 필요 건수·오라클 한계를 **정직하게 노출**(과대약속 금지).

## 2. 입력/출력 인터페이스
- `build_report(scenario_title, extraction?, matrix?, proposal?, regression?, assurance?) -> ValidationReport`
- `format_report_md(report) -> str` — 마크다운.
- `render_report_html(report) -> str` — self-contained HTML(외부 스크립트 없음, 하드코딩 없음).
- `ValidationReport`: `node_status()`, `is_pipeline_complete`, `review_required_count`.

## 3. 핵심 로직·설계 결정
- **조립만, 값 미생성:** 각 노드 산출을 참조·요약(단일 진실 유지).
- **디자인 시스템 재사용:** impact UI 렌더와 동일 토큰 → 산출물 일관성.
- **관통 판정:** 핵심 4노드 존재 시 `is_pipeline_complete=True`(HTML 상단 verdict 배지).
- **정직성 섹션(§7):** stub 명시·검토필요 건수·Assurance 부분·초안 미승인·오라클 challenger 한계.

## 4. 관련 파일
- `src/regimpact/validation/` — `report.py`(조립·md), `render_html.py`(HTML)
- `tests/test_validation.py` · `examples/demo_e2e.py`
- 산출물: `docs/reports/validation_6_30.md`, `docs/reports/validation_6_30.html`

## 5. 검증 상태
- `tests/test_validation.py` — 11건(md 7 + HTML 4, 전체 96 통과에 포함):
  노드 present/missing, 관통·부분관통, 메타 유도, 검토필요, md/HTML 실데이터 반영, 환각값 부재.

## 6. 알려진 제약·모호성
- **프레젠테이션 골격:** 실데이터 조립 + 렌더까지. 정식 15~20쪽 분석 서사·해석은 Phase 3.
- Assurance는 선택 입력(dict) — 4 dimension 정량화 연동은 후속.
