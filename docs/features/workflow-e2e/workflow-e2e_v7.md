# 워크플로우: E2E 파이프라인 (Walking Skeleton)

> **버전:** v7   **날짜:** 2026-08-13   **상태:** 유효(전 노드 관통 + 정식 검증보고서 완성)
> **이전 버전:** v6 (`workflow-e2e_v6.md`)

## 변경 이력 (v6 → v7)
- **[범위]** [8] Validation Report: `정식 HTML(서사 Phase 3)` → **정식 15~20쪽 분석 서사 완성**.
  `docs/reports/validation_report_6_30_full.md`(약 17쪽). 코어 완성 정의(브리프 §18)의 최종 산출물 충족.
- **[상태]** 파이프라인 [1]~[8] 전 노드 실질 완결(RAG·정식 audit 등 인프라 심화만 잔여).

---

## 1. 목적·책임
6·30 시나리오 1건이 **원문 → 판정 → 영향 → 제안 → 검증 → 보고**까지 끝까지 관통되게 하는
전체 흐름(수직 슬라이스). 각 노드는 개별 기능단위 문서를 가진다. 이 문서는 **노드 간 연결과
데이터 계약(interface)**을 정의한다(노드 내부 수치·상태는 각 기능단위 문서가 단일 진실).
근거 계획: `docs/04_PLAN.md`.

## 2. 파이프라인 흐름 (노드 = 데이터 계약)
```
[1] Source Snapshot ─(원문 txt + hash)─────────────► docs/sources/         ✅ DONE(수동)
      ▼
[2] RegChange Extractor(E) ─(RegChangeExtraction)──► extractor/            ✅ DONE (grounded 추출 산출)
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
[5] Test Cases + Rule-Regression ─(RegressionReport)► tc_generator/        ✅ DONE (seed30/큐레이션106/격자3200)
      ▼
[6] Assurance Scorecard ─(4 dim, 12지표)───────────► assurance/            ✅ DONE (확정 임계값, 12/12 PASS)
      ▼
[8] Validation Report ─(md + HTML + 정식 서사)─────► validation/ + 서사문서  ✅ DONE
          자동: docs/reports/validation_6_30.{md,html}
          정식: docs/reports/validation_report_6_30_full.md (약 17쪽, authored)
```

## 3. 현재 관통 상태
- **전 노드 관통 + 정식 보고서:** [2]→[3]→[R]→[4]→[7]→[5]→[6]→[8], + [3a] UI. `is_pipeline_complete=True`.
- **[8]:** 자동 요약(md/html) + **정식 분석 서사(17쪽)** 완성 — 코어 완성 정의(브리프 §18) 충족.
- 데모: `demo_e2e.py`, `assurance_scorecard.py`, `demo_portfolio.py`.

## 4. 노드 ↔ 기능단위 문서 매핑
| 노드 | 기능단위 | 상태 |
|---|---|---|
| [R] 룰엔진 | `features/rule-engine` | ✅ |
| [2] Extractor | `features/extractor-assurance` (v3) | ✅ (실측, Recall 100%) |
| [3] Impact Matrix | `features/impact-matrix` | ✅ |
| [3a] UI Render | `features/ui-render` | ✅ |
| [4] Rule Change Proposal | `features/rule-proposal` | ✅ |
| [7] Human Review | `features/rule-proposal`(approval envelope) | ✅ |
| [5] TC/Regression | `features/tc-generator` (v3, 격자 3,200) | ✅ |
| [6] Assurance Scorecard | `features/assurance-scorecard` (v1, 12지표) | ✅ |
| [8] Validation Report | `features/validation-report` (v3, 정식 서사) | ✅ |

## 5. 검증 상태
- 관통 노드는 각 기능단위 테스트로 커버(전체 110 통과). 정식 서사의 수치는 실측과 일치(재현 명령 포함).

## 6. 알려진 제약·다음 관통 과제
- 코어 완성 정의(04_PLAN·브리프 §18) **충족.** 잔여는 인프라·심화: RAG/retrieval, 정식 audit trail,
  자동 claude-opus-5 API 무인 실행(키 확보 후), 추가 규제이벤트 확보 시 추출 골드셋 다문서 확대.
