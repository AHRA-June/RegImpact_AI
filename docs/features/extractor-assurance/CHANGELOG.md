# CHANGELOG — RegChange Extractor(E) + Citation Assurance(A)

> 최신이 위. 각 항목은 해당 버전 파일(`extractor-assurance_vN.md`)의 변경 요약이다.

## v3 (2026-08-13)
- **Exception Recall 50%→100%.** FAQ Q2 원문 근거(verbatim)로 서민·실수요 예외 항목 보완
  (추출 9→10건), Citation 10/10·Unsupported 0% 유지. Assurance 피드백 루프(측정→포착→보완) 완결.
- test_assurance_measure 기대값 갱신(total 10, recall 1.0). 전체 75 통과.
- 이전(v2) 대비 상세: `extractor-assurance_v3.md` 상단 "변경 이력" 참고.

## v2 (2026-08-13)
- **첫 Assurance 실측 확보.** 6·30 grounded 추출을 결정론 채점 하네스로 측정:
  Citation Correctness 100%(9/9)·Unsupported 0%·Change Completeness 100%·Exception Recall 50%
  (서민·실수요 누락, Assurance가 고위험 예외 miss 포착)·시점/지역 OK.
- 산출물: `docs/eval/regchange_extracted_6_30.json`, `examples/measure_assurance_6_30.py`,
  `docs/reports/assurance_6_30.md`. E2E 보고서 [6] 노드 실측 연결. 회귀 고정 테스트 3건.
- 이전(v1) 대비 상세: `extractor-assurance_v2.md` 상단 "변경 이력" 참고.

## v1 (2026-08-13)
- 최초 작성 (신규). 기능단위 문서화 시작.
- 대상 구현: structured output 추출, LLM 주입(오프라인 테스트), Citation grounding 환각 탐지,
  골드 대조. 테스트 5건.
- 이전 버전 없음.
