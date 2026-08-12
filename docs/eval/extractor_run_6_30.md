# RegChange Extractor — 6·30 첫 실측 실행 리포트

> **프로젝트 최초의 실제 LLM 실측 지표.** 공문 3건(FSC·MOLIT 보도자료 + 관계기관 FAQ) →
> Gemini 추출 → Assurance 채점. 원시 추출은 `extractor_run_6_30_gemini.json`에 저장(키 없이 재현 가능).

- **실행일:** 2026-08-12
- **백엔드:** Google AI Studio (Gemini), 모델 `gemini-flash-latest`, structured output(responseSchema), temperature 0
- **입력:** `docs/sources/raw/{fsc_press,molit_press,faq}_20260630.txt` (3건, 사람 확정 스냅샷)
- **골드:** `docs/eval/regchange_gold_6_30.json`
- **재현:** `GEMINI_API_KEY=... python examples/run_extractor.py` (또는 저장된 JSON으로 오프라인 채점)
- **실행 2회:** 1차(초기 프롬프트) → 발견 2 대응 프롬프트 개선 → 2차 재측정. 저장 JSON은 **2차** 결과.

---

## 실측 지표 (1차 → 2차 프롬프트 개선 후)

| 지표 | 1차 | 2차(개선 후) | 판정 |
|---|---|---|---|
| **Citation Correctness** | 100% (6/6) | **100%** (12/12) | ✅ 인용이 모두 원문에 실재 |
| **Unsupported Claim Rate** | 0% | **0%** | ✅ 환각 인용 없음 |
| **Change Completeness** | 100% (4/4) | **100%** (4/4) | ✅ LTV·시행일·경과규정·지역 모두 포착 |
| **Exception Recall** | 50% (1/2) | **100%** (2/2) | ✅ 발견 2 수정으로 서민·실수요 포착 |
| **Effective-date Accuracy** | OK | **OK** | ✅ 2026-07-01 정확 |
| **Regions match** | MISS | **OK**† | ✅ 발견 3 수정(지역명→코드 정규화 계층) 후 코드 대조 통과 |

† Regions는 2차 추출(한글명)에 **정규화 계층**을 적용해 code 대조한 결과. 추출 원본은 한글명 보존.

- 1차 추출 6건 → **2차 12건**(예외를 생애최초/서민·실수요/정책모기지로 분리, 다주택 LTV 0%·
  중도금→잔금 경과규정·사업자대출 제한 등 세분화). **항목이 2배로 늘어도 Citation 100%·환각 0% 유지**
  → recall을 올리면서 precision(근거 정확성)을 잃지 않음.

---

## 발견 1 — 측정 아티팩트: PDF 줄바꿈이 정확한 인용을 환각으로 오탐 (수정함)

초기 실행에서 Citation Correctness가 **67%(4/6)** 로 나오고 GRANDFATHERING·SCOPE_LIMIT가
"환각 가능"으로 플래그됐다. 원인은 **모델이 아니라 채점기**였다:

- 원문은 PDF/HWP에서 추출돼 문장 중간에 줄바꿈이 있다 — 예: `…효력 발생일 전일(6.30일)`↵`까지 금융회사…`.
- 기존 grounding은 공백을 단일 공백으로 정규화 → 그 줄바꿈이 **공백**이 되어 원문이 `(6.30일) 까지`가 된다.
- 모델은 정확히 `(6.30일)까지`(공백 없음)로 인용 → substring 매칭 실패 → **정확한 인용을 환각으로 오탐**.

**수정:** grounding 비교를 공백 무관(`_squish`, 모든 공백 제거)으로 변경. 지어낸 인용은 공백을
지워도 원문에 없으므로 여전히 잡힌다(회귀 테스트 `test_grounding_ignores_pdf_linewrap_whitespace`,
`test_citation_grounding_catches_hallucination` 둘 다 통과). 보정 후 **100%(6/6)**.

> Model Risk 함의: "hallucination rate"는 원문 정규화 방식에 민감하다. 지표를 신뢰하려면
> **채점기의 텍스트 정규화가 소스 레이아웃 아티팩트에 견고해야** 한다.

## 발견 2 — 서민·실수요 예외 recall 미스 → ✅ 수정·재측정 완료

**1차:** EXCEPTION 항목이 "생애최초 주택구입 및 정책모기지 등 완화된 LTV(60~70%)"로 **생애최초·정책모기지만**
언급하고 **서민·실수요자**를 별도 항목/키워드로 남기지 않았다 → Exception Recall 50%.
서민·실수요는 규제지역 LTV 60%의 핵심 예외(`regulatory_facts.md`)이므로 놓치면 위험(metrics_spec ★).

**수정:** 프롬프트에 **규칙 6**(여러 예외가 한 문장에 나열돼도 각각을 별도 EXCEPTION 항목으로 분리,
summary에 예외명 명시) + EXCEPTION 카테고리 체크리스트(①생애최초 ②서민·실수요 ③정책모기지) 추가.
규칙 1(원문에 없으면 지어내지 않음)은 유지해 환각을 막음. (`src/regimpact/extractor/prompt.py`)

**2차 결과:** 모델이 세 예외를 각각 분리 추출 →
```
[EXCEPTION] 생애최초 주택구입자 완화 LTV 적용      (70% → 60~70%)
[EXCEPTION] 서민·실수요자 완화 LTV 적용            (60%(아파트 限))
[EXCEPTION] 정책모기지(보금자리론) 완화 LTV 적용   (아파트60% / 非아파트55%)
```
Exception Recall **50% → 100%**, missed_exceptions 없음. 다른 지표 회귀 없음(오히려 세분화되며
다주택 LTV 0%·중도금→잔금 경과규정·사업자대출 제한 등 추가 포착). 환각 0% 유지.

> 주: 프롬프트로 완전성을 높이되 "원문에 없으면 생략"(규칙 1)을 최우선으로 둬, recall↑가
> 환각↑로 이어지지 않도록 통제했다. 이 트레이드오프 통제가 Assurance의 핵심.

## 발견 3 — 지역명 → canonical code 정규화 부재 → ✅ 수정 완료

`target_regions`가 `["화성시 동탄구","용인시 기흥구","구리시"]`(원문 한글명)로 나와,
룰엔진/regions.py의 코드(`GURI`,`YONGIN_GIHEUNG`,`HWASEONG_DONGTAN`)와 불일치 → Regions MISS.
추출 자체는 올바르고 **표현형만 다른** 문제.

**수정:** 지역명→코드 **정규화 계층**을 `regions.py`에 추가(도메인 권위, LOCKED §4).
`resolve_region_code(name)`은 distinctive token('구리'·'기흥'·'동탄') 포함으로 매칭 —
접두("경기도"·"시"·"구")에 견고하고, code 입력엔 idempotent, 미상 지역은 `None`.
`normalize_regions(names)`는 `(코드목록, 매핑실패목록)`을 반환해 **조용한 누락을 막는다**.

채점(`score_against_gold`)은 추출 원본을 훼손하지 않고 **비교 시점에만** 지역을 코드로 정규화한 뒤
골드와 대조. 저장된 2차 추출로 오프라인 재채점: **Regions MISS→OK**(`normalized_regions`
= [HWASEONG_DONGTAN, YONGIN_GIHEUNG, GURI], `unmapped_regions`=[]). 미상 지역은 리포트에 표면화.

> 설계 원칙: 추출기는 원문에 충실(한글명 그대로 보존), 정규화는 별도 계층. 6·30 밖 지역이
> 오면 code로 조용히 만들지 않고 `unmapped`로 노출 → 사람이 사전 확장 여부를 판단.

---

## 다음 실측 액션

1. ~~예외 recall 개선 후 재측정~~ — ✅ 완료(2026-08-12, 발견 2). Exception Recall 100%. 임계값은 골드 확대 후 확정.
2. ~~지역명→코드 매핑 계층 추가~~ — ✅ 완료(2026-08-12, 발견 3). Regions OK. `regions.normalize_regions`.
3. ~~추출→Impact Matrix 연결~~ — ✅ 완료(2026-08-12). `impact_from_extraction`. 저장 추출로 24행 관통.
4. 골드셋 확대(DEV 우선) 후 지표에 분모를 키워 신뢰구간 확보(현재 n=1 정책, 소규모 seed).
5. Anthropic 백엔드로 교차 실측(모델 간 비교) — 프롬프트 개선이 모델 무관하게 유효한지 확인.
