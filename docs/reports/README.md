# Reports — 산출물

파이프라인·평가 산출물. 대부분 데모 스크립트로 **재생성 가능**(결정론).

| 파일 | 내용 | 생성 |
|---|---|---|
| `validation_report_6_30_full.md` | **정식 검증보고서(약 17쪽)** — 모델검증 형식 분석 서사 | authored |
| `validation_6_30.md` / `.html` | 검증보고서 자동 요약(md + 정식 HTML) | `demo_e2e.py` |
| `assurance_scorecard.md` | Assurance 4 dimension 12지표 스코어카드(확정 임계값) | `assurance_scorecard.py` |
| `assurance_6_30.md` | 추출 Assurance 실측(grounding·골드 대조) | `measure_assurance_6_30.py` |
| `rule_portfolio_stats.md` | 룰 큐레이션 평가셋 106건 통계 | `demo_portfolio.py` |
| `rule_grid_stats.md` | 룰 조합 격자 3,200건 통계 | `demo_portfolio.py` |

재생성:
```bash
python examples/demo_e2e.py && python examples/assurance_scorecard.py \
  && python examples/demo_portfolio.py && python examples/measure_assurance_6_30.py
```

> 자동 생성 산출물의 수치는 실측이며 결정론적이다. 정식 검증보고서(`_full`)는 이 수치들을 근거로
> 작성한 authored 분석 문서다(재현 명령은 해당 문서 §13.5).
