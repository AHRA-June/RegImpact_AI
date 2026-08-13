# Assurance 첫 실측 — 2026-06-30 규제 변경

- 추출 항목: 9건 · 원문: FSC/MOLIT 보도참고자료, 관계기관 FAQ
- provenance: Claude Code 세션에서 SYSTEM_PROMPT 규칙(원문 verbatim 인용·추론 금지)에 따라 6·30 원문 3건(FSC/MOLIT 보도참고자료, 관계기관 FAQ)에서 수동 grounded 추출한 결과. 자동 claude-opus-5 API 무인 실행은 API 키 확보 후 재실행 예정(현재 환경에 키 없음). Assurance 채점(Citation Grounding·Gold 대조)은 결정론 오프라인 코드(src/regimpact/extractor/evaluate.py)로 실측.

## Dimension ① Source Grounding & Citation
- Citation Correctness: **100%** (9/9 verbatim 확인)
- Unsupported Claim Rate: **0%**

## Dimension ②③ Change/Exception Completeness · Temporal
- Change Completeness: **100%**
- Exception Recall: **50%**  ⚠ 놓친 예외: ['real_demand']
- Effective-date Accuracy: **OK**
- Region Completeness: **OK**

## 해석 (정직성)
- Citation grounding 100% / Unsupported 0% — 인용은 전부 원문 verbatim(환각 없음).
- **Exception Recall 50%** — 보수적 1차 추출이 ['real_demand'] 예외를 별도 항목으로 표면화하지 못함. **Assurance가 이 고위험 누락을 포착**(가드레일 작동). 원문(FAQ)에 존재하므로 다음 추출 반복에서 보완 대상.
- 이 수치는 6·30 단일 앵커 기준 첫 실측이다(n=1 문서셋). 골드셋 100~120 확대 시 통계화.
