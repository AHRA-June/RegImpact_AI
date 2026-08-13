# 워크플로우: E2E 파이프라인 (Walking Skeleton)

> **버전:** v6   **날짜:** 2026-08-13   **상태:** 유효(전 노드 관통, [8] 심화만 Phase 3)
> **이전 버전:** v5 (`workflow-e2e_v5.md`)

## 변경 이력 (v5 → v6)
- **[범위]** [6] Assurance: `◐ 부분(실측치 확보)` → `✅ 4 dimension 스코어카드 완성`.
  누락 3지표(Source Contradiction·Grandfathering Recall·Policy-version Consistency) 추가 + 확정
  임계값(Strict) 판정 → 12지표 6·30 전부 PASS(종합 PASS). `src/regimpact/assurance/`.
- **[문서]** [6] 매핑을 신규 기능단위 `features/assurance-scorecard`로. 임계값 확정 `metrics_spec §0-C`.
- **[검증]** 테스트 96 → 110(스코어카드 14).

---

## 1. 목적·책임
6·30 시나리오 1건이 **원문 → 판정 → 영향 → 제안 → 검증 → 보고**까지 끝까지 관통되게 하는
전체 흐름(수직 슬라이스). 각 노드는 개별 기능단위 문서를 가진다. 이 문서는 **노드 간 연결과
데이터 계약(interface)**을 정의한다(노드 내부 수치·상태는 각 기능단위 문서가 단일 진실).
근거 계획: `docs/04_PLAN.md`.

## 2. 파이프라인 흐름 (노드 = 데이터 계약)
```
[1] Source Snapshot ─(원문 txt + hash)─────────────► docs/sources/         ✅ DONE(수동)
      │
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
      │   ① Grounding ② Completeness ③ Temporal ④ Regression — Strict, 고위험 FAIL→전체 FAIL
      ▼
[8] Validation Report ─(md + 정식 HTML)────────────► validation/           ✅ DONE (HTML, 서사 Phase 3)
          build_report + format_report_md + render_report_html
          → docs/reports/validation_6_30.{md,html}
```

## 3. 현재 관통 상태
- **전 노드 관통:** [2]→[3]→[R]→[4]→[7]→[5]→[6]→[8], + [3a] UI. `is_pipeline_complete=True`.
- **[6] Assurance:** 4 dimension 12지표 확정 임계값 판정 완성(6·30 종합 PASS). 지표·임계는 assurance-scorecard 참조.
- **[8] Validation Report:** 정식 HTML 렌더 완료. 정식 15~20쪽 분석 서사만 Phase 3.
- 데모: `demo_e2e.py`(→ validation_6_30.{md,html}), `assurance_scorecard.py`(→ assurance_scorecard.md).

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
| [8] Validation Report | `features/validation-report` (v2, 정식 HTML) | ✅ |

## 5. 검증 상태
- 관통된 노드는 각 기능단위 테스트로 커버(전체 110 통과).
- E2E 관통 `demo_e2e.py` + `test_validation`, Assurance 스코어카드 `test_assurance_scorecard`(가드레일 포함).

## 6. 알려진 제약·다음 관통 과제
- **다음:** [8] 정식 15~20쪽 분석 서사(HTML 프레젠테이션·[6] 정량화는 완료).
- Extractor **자동 claude-opus-5 API 무인 실행 1회**(키 확보 후) — 수동 추출 수치와 비교.
- 코어 완성 정의(04_PLAN): Source→…→Validation Report E2E 완결 — **전 노드 관통 + 4 dim Assurance 충족.**
