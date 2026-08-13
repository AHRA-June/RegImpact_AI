# 검증의 한계 — "100%"가 증명하는 것과 증명하지 않는 것

> 브리프 §12: **"검증의 한계를 숨기지 않는 것이 오히려 신뢰성을 높인다."**
> 이 문서는 이 프로젝트의 여러 지표가 100%로 나오는 이유를 정직하게 분해한다.
> **항상 100%인 검증 시스템은 그 자체가 red flag다.** 그래서 (a) 각 100%의 의미와 한계를
> 명시하고, (b) 하니스에 '이빨'이 있음을 판별력 테스트로 실증한다.

---

## 요약: 각 100%의 실제 강도

| 지표 | 현재값 | 무엇을 증명하나 | 무엇을 증명하지 **않나** | 강도 |
|---|---|---|---|---|
| Rule-regression Pass Rate | 3024/3024 | 엔진이 **독립 오라클**(명세 §H 재구현)과 일치 | 명세가 **현실**에 맞다 / 골드가 옳다 | ★★★ (mutation 실증) |
| 골드셋 scenario 채점 | 86/86 | 골드 기대값이 엔진과 일치 | 골드가 **독립적으로** 옳다 (거의 순환) | ★☆☆ |
| 골드셋 grounding | 34/34 | 인용이 원문에 verbatim 존재 | 인용이 **적절**하다 / 답이 옳다 | ★★☆ |
| Extractor run1 Assurance | 100% | 파이프라인 배관이 동작 | **독립** 추출 성능 (오염됨) | ☆☆☆ |

---

## 왜 100%인가 — 지표별 정직한 분해

### 1. Rule-regression (엔진 ⟷ 오라클) — 가장 강한 100%
- **의미:** 엔진(`rule_engine`)과 오라클(`tc_generator/oracle`)이 **구조적으로 독립**(오라클은 엔진을
  import 하지 않음)인데도 3,024건 층화 케이스에서 100% 일치 → 엔진에 **구현 드리프트가 없다**.
- **이빨 증거:** `test_regression_catches_mutated_*` — 엔진에 버그를 심으면 회귀가 실패로 잡는다.
  `test_portfolio_mutation_power_exceeds_seed_set` — 포트폴리오가 seed보다 10배↑ 실패 검출.
- **한계:** 엔진과 오라클은 **같은 명세(§H)** 에서 유도된다. 100%는 "엔진 == 명세"이지
  **"명세 == 현실"이 아니다.** 명세 자체의 오류(예: regulatory_facts 오독)는 이 지표로 못 잡는다.
  → 그 방어선은 **사람의 명세 확정**(LOCKED §4)과 골드셋 human-confirm이다.

### 2. 골드셋 scenario 채점 — 가장 약한 100% (거의 순환)
- **왜 100%인가:** scenario 아이템의 `expected_ltv/status`를 **작성자(AI)가 룰엔진에 맞춰 기입**했고,
  초안 오류는 엔진 기준으로 수정했다. 그래서 "엔진이 (엔진 보고 쓴) 골드와 같다"에 가깝다.
- **그럼 가치가 없나?** 아니다. 하지만 **현재 형태의 100%는 독립 성능 측정이 아니라 QA 게이트**다.
  이 골드셋의 진짜 가치는 다음 두 가지이며, 둘 다 아직 미완이다:
  1. **사람 확정(HUMAN_CONFIRMED):** 전 115문항이 `AI_DRAFT`. 사람이 regulatory_facts 원문 대조로
     확정해야 "엔진이 **사람이 서명한 현실**과 일치"라는 의미로 승격된다.
  2. **비-scenario 의미론:** NL 질문·escalation 기대·grounding·카테고리 커버리지는 엔진과
     독립적인 신호다(특히 escalation·NO_CHANGE·AMBIGUOUS).
- **이빨 증거:** `test_goldset_scenario_catches_mutated_engine` — 엔진 상수를 변조하면 100%→73%.

### 3. 골드셋 grounding / Citation Correctness — 중간
- **의미:** 인용이 원문에 verbatim 존재 → **환각 인용은 못 통과**한다(결정적).
- **한계:** verbatim 존재 ≠ 인용이 **적절**하다. 원문 아무 문장이나 붙여도 grounded로 통과한다.
  (적절성은 keyword/사람 검토로 보완.) 작성 시 실패한 인용은 고쳤으므로 100%는 부분적으로 자명.
- **이빨 증거:** `test_goldset_grounding_catches_corrupted_quote` — 인용 오염 시 100%→92%.

### 4. Extractor run1 100% — 오염된 참고치
- 세션 모델(claude-opus-4-8)이 **gold를 이미 본 상태**로 추출했고, 고립 API 호출이 아니다.
  → 파이프라인 실배선 실증용이지 **독립 벤치마크가 아니다.** (`regchange_extraction_6_30_run1.json` `_note` 참조)

---

## 하니스에 이빨이 있는가? — 판별력(negative control) 실측

정상 데이터 100%가 의미를 가지려면, **틀린 데이터에서는 <100%** 여야 한다.
`examples/demo_discrimination.py` / `tests/test_discrimination.py`가 이를 실측·고정한다.
의도적으로 오류(환각 인용·항목 누락·시행일/지역 오류·엔진 변조)를 주입한 결과:

| 지표 | 정상 | 오류 주입 | 감지 |
|---|---|---|---|
| Citation Correctness | 100% | 67% | ✓ |
| Change Completeness | 100% | 50% | ✓ |
| Exception Recall | 100% | 0% | ✓ |
| Effective-date / Regions | 100% | 0% / 0% | ✓ |
| E2E 종합 판정(e2e_ok) | True | False | ✓ |
| 골드셋 scenario(엔진 변조) | 100% | 73% | ✓ |
| 골드셋 grounding(인용 오염) | 100% | 92% | ✓ |

→ **모든 지표가 오류에 반응한다.** 100%는 "오류 없음"을 뜻하지 "검증 능력 없음"을 뜻하지 않는다.

---

## 진짜 독립적인 숫자를 얻으려면 (남은 일)

지금의 100%들을 **독립 성능**으로 승격하려면:

1. **오염 없는 LLM 추출(run2):** 사용자 API 키로 `run_extractor.py`(고립 claude-opus-5) 실행 →
   gold를 못 본 모델의 실제 추출 성능 측정. **여기서 처음으로 100% 미만이 정상적으로 기대된다.**
2. **골드셋 human-confirm:** 115문항 `AI_DRAFT` → `HUMAN_CONFIRMED`. 그 후 LOCKED/CHALLENGE를
   1회 실행해 **튜닝하지 않은** 최종 성능 보고(브리프 §12 규율).
3. **명세-현실 검증:** regulatory_facts.md의 claim(C01~)에 원문 URL·hash·확신도를 채우고 사람이 서명.

> 이 문서의 존재 자체가 산출물이다. Model Risk 관점에서 "왜 100%인가"에 답하지 못하는 검증은
> 신뢰할 수 없다. 여기서는 답한다: **일부는 자명(QA 게이트), 하나는 강함(mutation 실증),
> 독립 성능치는 아직 미측정 — 그리고 그 사실을 숨기지 않는다.**
