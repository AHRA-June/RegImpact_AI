# 워크플로우: E2E 파이프라인 (Walking Skeleton)

> **버전:** v3   **날짜:** 2026-08-13   **상태:** 유효(전 노드 관통, [6][8] 부분/stub)
> **이전 버전:** v2 (`workflow-e2e_v2.md`)

## 변경 이력 (v2 → v3)
- **[범위]** [6] Assurance: `◐ 부분(Citation grounding만)` → `◐ 부분(첫 실측치 확보 + E2E 연결)`.
  6·30 grounded 추출을 결정론 채점 하네스로 실측(Citation 100%/Unsupported 0%/Completeness 100%/
  Exception Recall 50%/시점·지역 OK), `demo_e2e.py`가 이 수치를 검증보고서 [6] 섹션에 실어 관통.
- **[로직]** `demo_e2e.py` [2] Extractor를 하드코딩 골드에서 **저장 추출 로드**
  (`docs/eval/regchange_extracted_6_30.json`)로 교체 — 파이프라인이 실제 추출 산출을 소비.
- **[검증]** 전 노드([2]~[8]) 검증보고서에서 ✅ 표기(관통), 테스트 72 → **75**.

---

## 1. 목적·책임
6·30 시나리오 1건이 **원문 → 판정 → 영향 → 제안 → 검증 → 보고**까지 끝까지 관통되게 하는
전체 흐름(수직 슬라이스). 각 노드는 개별 기능단위 문서를 가진다. 이 문서는 **노드 간 연결과
데이터 계약(interface)**을 정의한다. 근거 계획: `docs/04_PLAN.md`.

## 2. 파이프라인 흐름 (노드 = 데이터 계약)
```
[1] Source Snapshot ─(원문 txt + hash)─────────────► docs/sources/         ✅ DONE(수동)
      │
[2] RegChange Extractor(E) ─(RegChangeExtraction)──► extractor/            ✅ DONE (grounded 추출 산출)
      │   docs/eval/regchange_extracted_6_30.json (자동 API 무인 실행은 키 확보 후)
      ▼
[3] Impact Matrix (Before/After) ─(ImpactMatrix)───► impact/               ✅ DONE
      ├──────────────► [3a] UI Render ─(HTML)──────► impact/render_html    ✅ DONE
      ▼
[R] Deterministic Rule Engine ─(LtvDecision)───────► rule_engine.py        ✅ DONE
      ▼
[4] Rule Change Proposal ─(RuleChangeProposal)─────► proposal/             ✅ DONE
      ▼
[7] Human Review ─(ReviewDecision)─────────────────► proposal.record_decision  ✅ DONE
      ▼
[5] Test Cases + Rule-Regression ─(RegressionReport)► tc_generator/        ✅ DONE (30/30)
      ▼
[6] Assurance 평가 ─(지표 dict)────────────────────► extractor/evaluate    ◐ 부분(첫 실측치 확보)
      │   Citation 100% / Unsupported 0% / Completeness 100% / Exception Recall 50% / 시점·지역 OK
      ▼
[8] Validation Report ─(ValidationReport/MD)───────► validation/           ✅ DONE(stub)
          build_report(...) + format_report_md → docs/reports/validation_6_30.md
```

## 3. 현재 관통 상태
- **전 노드 관통:** [2]→[3]→[R]→[4]→[7]→[5]→[6]→[8], + [3a] UI. `is_pipeline_complete=True`.
- **[6] Assurance:** dimension ①②③ 첫 실측 확보(E2E 보고서에 수치 표기). ④(Rule Regression)는 [5]가 담당.
  4 dimension 정량화 완성·임계값은 Phase 3.
- **[8] stub:** 실데이터 조립 + 요약(정식 15~20쪽은 Phase 3).
- 데모: `python examples/demo_e2e.py` → 보고서 + `docs/reports/validation_6_30.md`;
  `python examples/measure_assurance_6_30.py` → `docs/reports/assurance_6_30.md`.

## 4. 노드 ↔ 기능단위 문서 매핑
| 노드 | 기능단위 | 상태 |
|---|---|---|
| [R] 룰엔진 | `features/rule-engine` | ✅ |
| [2] Extractor/Assurance | `features/extractor-assurance` (v2) | ✅ (첫 실측) |
| [3] Impact Matrix | `features/impact-matrix` | ✅ |
| [3a] UI Render | `features/ui-render` | ✅ |
| [4] Rule Change Proposal | `features/rule-proposal` | ✅ |
| [7] Human Review | `features/rule-proposal`(approval envelope) | ✅ |
| [5] TC/Regression | `features/tc-generator` | ✅ |
| [6] Assurance | `features/extractor-assurance` (채점 하네스) | ◐ 부분(실측) |
| [8] Validation Report | `features/validation-report` | ✅(stub) |

## 5. 검증 상태
- 관통된 노드는 각 기능단위 테스트로 커버(전체 75 통과).
- E2E 관통은 `examples/demo_e2e.py` + `test_validation`으로, Assurance 실측은 `test_assurance_measure`로 고정.

## 6. 알려진 제약·다음 관통 과제
- **다음:** [6] Assurance 4 dimension 완성·임계값, [8] 정식 보고서(15~20쪽)·HTML 렌더.
- Extractor **자동 claude-opus-5 API 무인 실행 1회**(키 확보 후) — 수동 추출 수치와 비교.
- 코어 완성 정의(04_PLAN): Source→…→Validation Report E2E 완결 — **전 노드 관통 충족(심화는 Phase 3).**
