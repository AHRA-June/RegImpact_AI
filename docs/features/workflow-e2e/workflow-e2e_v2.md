# 워크플로우: E2E 파이프라인 (Walking Skeleton)

> **버전:** v2   **날짜:** 2026-08-13   **상태:** 유효(핵심 관통 완료)
> **이전 버전:** v1 (`workflow-e2e_v1.md`)

## 변경 이력 (v1 → v2)
- **[범위]** [4] Rule Change Proposal: `⬜ STUB 필요` → `✅ DONE` — `src/regimpact/proposal/` 구현
  (build_proposal + record_decision). ImpactMatrix에서 유도한 구조화 초안, AI초안→사람확정 envelope.
- **[범위]** [7] Human Review: (암묵) → `✅ DONE(approval envelope)` — `record_decision`으로 승인/반려 기록.
- **[범위]** [8] Validation Report: `⬜ STUB 필요` → `✅ DONE(stub)` — `src/regimpact/validation/`
  (build_report + format_report_md). 노드 산출 조립 + present/missing·검토필요 정직 표기.
- **[로직]** 관통 판정 추가: 핵심 4노드(추출·영향·제안·회귀) 존재 시 `is_pipeline_complete=True`.
- **[문서]** §3 관통 상태·§4 매핑 표를 완결 상태로 갱신, E2E 데모(`examples/demo_e2e.py`) 추가.
- **[검증]** 테스트 +14(proposal 7, validation 7) → 전체 72 통과.

---

## 1. 목적·책임
6·30 시나리오 1건이 **원문 → 판정 → 영향 → 제안 → 검증 → 보고**까지 끝까지 관통되게 하는
전체 흐름(수직 슬라이스). 각 노드는 개별 기능단위 문서를 가진다. 이 문서는 **노드 간 연결과
데이터 계약(interface)**을 정의한다. 근거 계획: `docs/04_PLAN.md`.

## 2. 파이프라인 흐름 (노드 = 데이터 계약)
```
[1] Source Snapshot ─(원문 txt + hash)─────────────► docs/sources/         ✅ DONE(수동)
      │
[2] RegChange Extractor(E) ─(RegChangeExtraction)──► extractor/            ✅ DONE (LLM 실측 NEXT)
      │   policy_id, effective_from, target_regions, changes[]
      ▼
[3] Impact Matrix (Before/After) ─(ImpactMatrix)───► impact/               ✅ DONE
      │   analyze_from_extraction(extraction, segments, region_code)
      ├──────────────► [3a] UI Render ─(HTML)──────► impact/render_html    ✅ DONE
      ▼
[R] Deterministic Rule Engine ─(LtvDecision)───────► rule_engine.py        ✅ DONE
      │   ▲ Impact Matrix가 이 엔진을 두 시점으로 호출(핵심 판정)
      ▼
[4] Rule Change Proposal ─(RuleChangeProposal)─────► proposal/             ✅ DONE
      │   build_proposal(matrix, extraction) — AI초안(PENDING_REVIEW)
      ▼
[7] Human Review ─(ReviewDecision)─────────────────► proposal.record_decision  ✅ DONE
      │   승인/반려/수정요청 기록(approval envelope). LOCKED §4.
      ▼
[5] Test Cases + Rule-Regression ─(RegressionReport)► tc_generator/        ✅ DONE
      │   엔진 ⟷ 독립 오라클 차등검증(Pass Rate)
      ▼
[6] Assurance 평가 ─(지표)─────────────────────────► extractor/evaluate    ◐ 부분(Citation)
      │   깊은 4 dimension: ①Grounding ②Completeness ③Temporal ④Regression
      ▼
[8] Validation Report ─(ValidationReport/MD)───────► validation/           ✅ DONE(stub)
          build_report(...) + format_report_md → docs/reports/validation_6_30.md
```

## 3. 현재 관통 상태
- **핵심 관통 완료:** [2]→[3]→[R]→[4]→[7]→[5]→[8], + [3a] UI. `is_pipeline_complete=True`.
- **부분:** [6] Assurance — Citation grounding은 있음, 4 dimension 정량화는 Phase 3.
- **stub 성격:** [8] Validation Report는 실데이터 조립 + 요약(정식 15~20쪽은 Phase 3).
- 데모: `python examples/demo_e2e.py` → 콘솔 보고서 + `docs/reports/validation_6_30.md`.

## 4. 노드 ↔ 기능단위 문서 매핑
| 노드 | 기능단위 | 상태 |
|---|---|---|
| [R] 룰엔진 | `features/rule-engine` | ✅ |
| [2] Extractor/Assurance | `features/extractor-assurance` | ✅(실측 NEXT) |
| [3] Impact Matrix | `features/impact-matrix` | ✅ |
| [3a] UI Render | `features/ui-render` | ✅ |
| [4] Rule Change Proposal | `features/rule-proposal` | ✅ |
| [7] Human Review | `features/rule-proposal`(approval envelope) | ✅ |
| [5] TC/Regression | `features/tc-generator` | ✅ |
| [8] Validation Report | `features/validation-report` | ✅(stub) |

## 5. 검증 상태
- 관통된 노드는 각 기능단위 테스트로 커버(전체 72 통과).
- E2E 관통은 `examples/demo_e2e.py` + `test_validation`(관통 판정·부분관통·정직표기)로 검증.

## 6. 알려진 제약·다음 관통 과제
- **다음:** [6] Assurance 4 dimension 정량화(Phase 3), [8] 정식 보고서(15~20쪽)·HTML 렌더.
- LLM 실측([2]) 1회로 첫 Assurance 수치 확보.
- 코어 완성 정의(04_PLAN): Source→…→Validation Report E2E 완결 — **핵심 노드 기준 충족.**
