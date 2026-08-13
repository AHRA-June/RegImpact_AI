# 워크플로우: E2E 파이프라인 (Walking Skeleton)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효(관통 진행 중)
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. 현재 노드 구현 현황을 스냅샷.

---

## 1. 목적·책임
6·30 시나리오 1건이 **원문 → 판정 → 영향 → 검증 → 보고**까지 끝까지 관통되게 하는
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
      │   rows[]: before/after LtvDecision, direction, delta, note
      ├──────────────► [3a] UI Render ─(HTML)──────► impact/render_html    ✅ DONE
      ▼
[R] Deterministic Rule Engine ─(LtvDecision)───────► rule_engine.py        ✅ DONE
      │   ▲ Impact Matrix가 이 엔진을 두 시점으로 호출(핵심 판정)
      ▼
[4] Rule Change Proposal ─(구조화 스키마)──────────► (미구현)              ⬜ STUB 필요
      ▼
[5] Test Cases + Rule-Regression ─(RegressionReport)► tc_generator/        ✅ DONE
      │   엔진 ⟷ 독립 오라클 차등검증(Pass Rate)
      ▼
[6] Assurance 평가 ─(지표)─────────────────────────► extractor/evaluate    ◐ 부분(Citation)
      │   깊은 4 dimension: ①Grounding ②Completeness ③Temporal ④Regression
      ▼
[7] Human Review → [8] Validation Report ──────────► (미구현)              ⬜ STUB 필요
```

## 3. 현재 관통 상태
- **판정·영향·검증 축은 관통:** [2]→[3]→[R]→[5], + [3a] UI.
- **미구현(스텁 필요):** [4] Rule Change Proposal(구조화), [7]/[8] Human Review·Validation Report.
- **부분:** [6] Assurance — Citation grounding은 있음, 4 dimension 정량화는 Phase 3.

## 4. 노드 ↔ 기능단위 문서 매핑
| 노드 | 기능단위 | 상태 |
|---|---|---|
| [R] 룰엔진 | `features/rule-engine` | ✅ |
| [2] Extractor/Assurance | `features/extractor-assurance` | ✅(실측 NEXT) |
| [3] Impact Matrix | `features/impact-matrix` | ✅ |
| [3a] UI Render | `features/ui-render` | ✅ |
| [5] TC/Regression | `features/tc-generator` | ✅ |
| [4][7][8] Proposal·Report | (예정) | ⬜ |

## 5. 검증 상태
- 관통된 노드는 각 기능단위 테스트로 커버(전체 58 통과).
- **E2E 스모크(단일 6·30 앵커)로 [2]→[3] 실데이터 관통은 `analyze_from_extraction` 테스트가 대리.**

## 6. 알려진 제약·다음 관통 과제
- **다음:** [4] Rule Change Proposal 고정 스키마 1개 + [8] Report stub 연결 → 파이프라인 완주.
- LLM 실측([2]) 1회로 첫 Assurance 수치 확보.
- 코어 완성 정의(04_PLAN): Source→…→Validation Report E2E 완결.
