# 첫 LLM 실측 — RegChange Extractor (Gemini)

> **개발 관측 스냅샷 (튜닝 전).** LOCKED TEST/CHALLENGE 아님(§12). LLM은 비결정이라 값은 재실행 시 변동 가능(temperature=0으로 완화).
> 목적: 파이프라인이 실제 LLM으로 관통되는지 + Assurance가 실패를 잡는지 실측.

- **일자:** 2026-08-10
- **provider / model:** Google Gemini · `gemini-flash-latest` (무료 티어)
- **입력:** 공문 3건 (FSC·MOLIT 보도참고자료, 관계기관 FAQ) — `docs/sources/`
- **실행:** `REGIMPACT_LLM_PROVIDER=gemini REGIMPACT_LLM_MODEL=gemini-flash-latest python examples/run_extractor.py`

## 결과

| 지표 | 값 | 해석 |
|---|---|---|
| 추출 변경 항목 | 6건 | REGION·LTV·EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·SCOPE_LIMIT 커버 |
| **Change Completeness** | **100%** (4/4) | 골드 필수변경(LTV 70→40·시행 7.1·경과규정·지역지정) 전부 포착 |
| **Effective-date** | **OK** | `effective_from = 2026-07-01` 정확 |
| **Exception Recall** | **50%** (1/2) | 생애최초 O, **서민·실수요 놓침** |
| **Citation Correctness** | **67%** (4/6) | 인용 4건 원문 verbatim 확인 |
| **Unsupported Claim Rate** | **33%** (2/6) | GRANDFATHERING·SCOPE_LIMIT 인용이 **원문 verbatim 아님**(요약·근사 인용) → grounding이 탐지 |
| Regions(코드) | **MISS** | 최상위 `target_regions`가 내부 코드(GURI 등)로 정규화 안 됨(한글명 추출) |

## 발견된 실패모드 (Assurance가 전부 정량으로 포착)

1. **근사 인용(2건):** 모델이 원문을 verbatim으로 인용하지 않고 다듬음(축약·"…"·표기 변경). → **Citation grounding**이 잡음(LLM이 LLM을 채점하지 않는, 원문 대조 기반).
2. **예외 누락:** "생애최초·정책모기지"만 한 항목으로 묶고 **서민·실수요를 별도 예외로 안 뽑음**. → **Exception Recall**이 잡음.
3. **지역 코드 미정규화:** 지역을 "화성시 동탄구" 등 한글명으로만 추출, 내부 코드 매핑 없음. → **Regions 대조**가 잡음.

> **이것이 프로젝트의 핵심 명제 실증(브리프 §2):** "정확한 자동화"가 아니라
> **"검증 가능한 초안화 + 실패의 명시적 통제"**. 무료 모델의 불완전한 추출을
> Assurance 레이어가 하나도 빠짐없이 정량으로 표면화했다.

## 개선 후보 (튜닝은 DEV에서만, LOCKED/CHALLENGE 오염 금지 §12)

- 프롬프트: verbatim 인용 강화(예시·경고), 예외를 항목별(생애최초/서민실수요/정책대출)로 빠짐없이 분리.
- 후처리: 추출 `target_regions` 한글명 → 내부 코드 매핑(regions.py), 또는 골드가 한글명도 허용.
- 모델 비교: `gemini-3.5-flash` 등 상위 모델로 재측정(비용·한도 대비 개선폭).
- 이후 골드셋 러너 predictor를 이 Extractor→판정 파이프라인으로 교체 → dimension ②④ 실수치.

---

## 재측정 — Extractor 개선 후 (2026-08-10)

> 위 첫 실측이 드러낸 3개 실패(근사 인용·예외 누락·지역 미정규화)를 처리하고 **동일 검증 층으로 재측정**.
> 스냅샷: `docs/eval/runs/gemini_improved_run.json`. 개발 관측(튜닝은 6·30 앵커에서만 §12), LLM 비결정.

**무엇을 바꿨나 (입력만 수정, 채점 층은 불변):**

1. **프롬프트(`extractor/prompt.py`)** — ①인용 verbatim 강제(줄임표·요약·의역·글자추가 금지, "짧아도 좋으니
   연속 원문 조각") ②예외를 종류별 **개별 항목**으로 분리(생애최초/서민실수요/정책대출) ③신규 지정 지역을
   `target_regions`에 지역명 그대로 나열.
2. **후처리(`extractor/extractor.py::normalize_extraction`)** — LLM이 한글 지역명으로 뽑아도 사람이 정의한
   결정적 매핑으로 내부 코드(GURI·YONGIN_GIHEUNG·HWASEONG_DONGTAN) 정규화. **LLM 아님(deterministic).**

**결과 (개선 전 → 후):**

| 지표 | 첫 실측 | 재측정 | 비고 |
|---|---|---|---|
| 추출 항목 수 | 6건 | 7건 | 예외 분리로 항목 증가 |
| Change Completeness | 100% | 100% | 유지 |
| Effective-date | OK | OK | 유지 |
| **Exception Recall** | **50%** | **100%** | 서민·실수요 예외 포착(분리 지시 효과) |
| **Citation Correctness** | **67%** | **86%** | 근사 인용 1건 해소 |
| **Unsupported Claim Rate** | **33%** | **14%** | 근사 인용 감소 |
| **Regions(코드)** | **MISS** | **OK** | 결정적 정규화로 코드 매핑 |

**남은 결함 (정직 보고):** GRANDFATHERING 인용 1건이 아직 근사(…)라 grounding 미통과 — Citation 86%로
상승했으나 완전하지 않다. 이 잔여 실패도 **Assurance가 계속 표면화**한다(덮지 않음).

> **핵심:** 지표를 올리려고 채점을 손대지 않았다. **Extractor(입력)만 고치고 검증 층은 그대로** 둔 채
> 재측정해 개선을 확인했다 — Assurance가 "개선되었는지"까지 정량으로 판정한다. 이것이 모델 리스크 검증의
> 정상 루프(관측 → 원인 → 입력 수정 → 재측정, 채점 오염 없이)다.
