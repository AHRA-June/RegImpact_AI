# 기능단위: Validation Report (검증보고서 stub)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효(stub)
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현: `src/regimpact/validation/`.)

---

## 1. 목적·책임
파이프라인 각 노드의 **실제 산출을 하나의 검증보고서로 조립**한다(Walking Skeleton [8]).
6·30 1건이 원문→판정→영향→제안→검증까지 관통됨을 보이고, **present/missing·사람검토 필요
건수를 정직하게 노출**한다(과대약속 금지). 정식 15~20쪽 보고서(Phase 3)의 골격.

## 2. 입력/출력 인터페이스
- `build_report(scenario_title, extraction?, matrix?, proposal?, regression?, assurance?)
   -> ValidationReport`
- `format_report_md(report) -> str` — 마크다운 렌더.
- `ValidationReport`: 노드 산출 묶음 + `node_status()`, `is_pipeline_complete`,
  `review_required_count`.

## 3. 핵심 로직·설계 결정
- **조립만, 값 미생성:** 각 노드 산출을 참조·요약할 뿐 판정을 새로 만들지 않음(단일 진실 유지).
- **관통 판정:** 핵심 4노드(추출·영향·제안·회귀) 존재 시 `is_pipeline_complete=True`.
- **정직성 섹션(§7):** stub 명시, 검토 필요 건수, Assurance 부분, 초안 미승인 여부를 항상 표기.
- **메타 유도:** policy_id·effective_from·regions를 있는 소스에서 우선순위로 유도.

## 4. 관련 파일
- `src/regimpact/validation/` — `report.py`(ValidationReport, build_report, format_report_md)
- `tests/test_validation.py` · E2E 데모 `examples/demo_e2e.py`
- 산출물: `docs/reports/validation_6_30.md`

## 5. 검증 상태
- `tests/test_validation.py` — 7건(전체 72 통과에 포함):
  노드 present/missing, 관통·부분관통 판정, 메타 유도, 검토필요 건수, MD 실데이터 반영, 초안 미승인 표기.

## 6. 알려진 제약·모호성
- **stub:** 실데이터 조립 + 요약까지. 정식 보고서(15~20쪽)·HTML 렌더·해석 서사는 Phase 3.
- Assurance는 선택 입력(dict) — 4 dimension 정량화 연동은 후속.
