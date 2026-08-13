# regimpact.impact — Impact Analysis + E2E Pipeline (Walking Skeleton)

6·30 규제 변경 **1건을 Source부터 Validation Report까지 관통**시키는 배관.
`04_PLAN.md`의 최대 리스크("E2E 관통 실패")를 해소하는 수직 슬라이스다.

## 관통 경로 (04_PLAN "코어 완성의 정의")

```
Source Snapshot        extractor.sources.load_sources
  → Before/After        impact.anchor.anchor_extraction  (또는 주입된 실제 LLM 추출)
  → Impact Matrix       impact.matrix.build_impact_matrix (룰엔진 2시점)
  → Rule Change Proposal impact.proposal.build_proposal
  → Test / Regression   tc_generator.run_regression       (독립 명세 오라클 차등검증)
  → Assurance           extractor.evaluate (Citation grounding + Gold 대조)
  → Validation Report   impact.report.format_e2e_report
```

## 설계 원칙

- **값의 출처 분리(provenance).** Impact Matrix·Proposal의 LTV 값은 전부 deterministic
  룰엔진(확정 명세)에서 온다 → auditable. LLM 추출은 **검증 대상**(Citation grounding)으로만
  흐른다. Proposal은 `narrative_changes`(LLM, citation 보존)와 `segment_impacts`(룰엔진)를
  분리해 담는다.
- **LOCKED §4 (AI초안→사람확정).** `RuleChangeProposal`은 `AI_DRAFT`로 태어나고,
  `.confirm()` 전까지 확정이 아니다(코드로 통제).
- **오프라인 관통.** 기본 추출은 원문에 grounding된 앵커라 **API 키 없이** E2E가 돈다.
  실제 LLM 추출을 `run_e2e(extraction=...)`로 주입하면 동일 파이프라인으로 그 출력의
  grounding·gold 점수를 측정한다.

## Impact Matrix 의미

각 행 = (세그먼트 × 지역). **시행 전(6.30)** 과 **시행 후(7.2)** 를 같은 룰엔진으로 평가해
`delta_ltv`를 낸다. 한쪽이라도 escalation(`NEEDS_HUMAN_REVIEW`/`DISCOVERY`)이면 delta는
`None`(= 기계 비교 불가, 사람 검토 필요라는 정직한 신호). 대표 산출:

| 세그먼트 | before | after | Δ |
|---|---:|---:|---:|
| 무주택 일반 | 70% | 40% | −30%p (고영향) |
| 생애최초 | 70% | 70% | 0 |
| 서민·실수요자 | 70% | 60% | −10%p |
| 비처분 1주택 | (기준값 부재→escalation) | 0% | 정의불가 |
| 다주택 | (escalation) | 0% | 정의불가 |

## 실행

```bash
python examples/demo_e2e_6_30.py     # 전체 관통 보고서 출력 (오프라인)
python -m pytest tests/test_impact.py
```

## 현재값 (6·30 앵커)

- Citation Correctness 100% (grounded 6/6), Change Completeness 100%, Exception Recall 100%
- Rule-regression 30/30 (100%), Impact Matrix 18행(고영향 12/escalation 6)
- 종합: ✅ E2E 관통 성공
