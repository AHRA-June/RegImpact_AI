# 기능단위: Validation Report (검증보고서)

> **버전:** v3   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v2 (`validation-report_v2.md`)

## 변경 이력 (v2 → v3)
- **[범위]** **정식 15~20쪽 분석 서사 완성**: `docs/reports/validation_report_6_30_full.md`(약 17쪽,
  28.8k자). 모델검증 보고서 형식(Executive Summary·방법론·Dimension별 발견·룰엔진 심층·고위험 실패
  분석·한계·권고·부록). 자동 생성 요약본(md/html)과 별개의 **authored 분석 문서**.
- **[제약 해소]** v2의 "정식 15~20쪽 분석 서사는 Phase 3" → **완료**. 남은 심화는 다문서 확대·정식 audit.

---

## 1. 목적·책임
파이프라인 각 노드의 실제 산출을 검증보고서로 제공한다. **3가지 형식**:
1. **마크다운 요약**(`format_report_md`) — 로그·CI용, demo_e2e 자동 생성.
2. **정식 HTML**(`render_report_html`) — 프레젠테이션·포트폴리오용, 데이터바인딩.
3. **정식 분석 서사**(`docs/reports/validation_report_6_30_full.md`) — authored, 모델검증 보고서.
present/missing·사람검토 필요 건수·오라클 한계를 정직하게 노출(과대약속 금지).

## 2. 입력/출력 인터페이스
- `build_report(...) -> ValidationReport` · `format_report_md(report) -> str` · `render_report_html(report) -> str`
- `ValidationReport`: `node_status()`, `is_pipeline_complete`, `review_required_count`.
- 정식 서사는 코드 산출이 아니라 실측 수치에 근거한 authored 문서(재현 명령은 문서 §13.5).

## 3. 핵심 로직·설계 결정
- **조립만, 값 미생성:** 자동 산출(md/html)은 노드 산출을 참조·요약(단일 진실).
- **서사는 authored:** 15~20쪽 분석은 해석·평가·권고를 포함하므로 사람/분석가가 작성(수치는 실측 고정).
- **정직성:** stub/부분/계획 구분, 오라클 challenger 한계, provenance를 모든 형식에 명시.

## 4. 관련 파일
- `src/regimpact/validation/` — `report.py`(조립·md), `render_html.py`(HTML)
- `tests/test_validation.py` · `examples/demo_e2e.py`
- 산출물: `docs/reports/validation_6_30.{md,html}`(자동), `docs/reports/validation_report_6_30_full.md`(정식 서사)

## 5. 검증 상태
- `tests/test_validation.py` — 11건(md 7 + HTML 4, 전체 110 통과에 포함).
- 정식 서사의 수치는 실측(스코어카드 12/12 PASS, 격자 3,200/3,200 등)과 일치, 재현 명령 포함.

## 6. 알려진 제약·모호성
- 정식 서사는 6·30 앵커 point-in-time 문서. 시스템 변경 시 재실행·갱신.
- 다문서 확대·정식 audit trail·자동 LLM 실행은 후속.
