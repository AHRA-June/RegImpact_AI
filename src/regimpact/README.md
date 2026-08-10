# regimpact — deterministic 주담대 LTV 룰엔진

확정 명세 `docs/05_RULE_SPEC.md` v1의 구현. **LLM이 규칙을 생성하지 않는다(LOCKED §4).**
이 엔진은 LLM 출력(RegChange Extractor 등)을 검증하는 **기준점(ground truth)**이다.

## 구조
- `models.py` — 입력/출력 스키마(dataclass), 상태·reason_code enum
- `regions.py` — 지역 규제상태의 시점 버전 해석 (6·30 3개 지역: 7.1부터 REGULATED)
- `grandfathering.py` — 경과규정 G1/G2/G3 판정 (컷오프 2026-06-30)
- `rule_engine.py` — 통합 판정 알고리즘 H (P0~P7 우선순위)

## 사용
```python
from datetime import date
from regimpact import MortgageApplication, evaluate

d = evaluate(MortgageApplication(region_code="GURI", evaluation_date=date(2026,7,2),
                                 house_count=0, first_home_buyer=True))
print(d.max_ltv, d.applicable_rule_id, d.reason_codes)   # 0.7 REG_FIRSTHOME ['EXCEPTION_FIRST_HOME']
```

## 실행
```bash
pip install -e ".[dev]"     # 또는: pip install pytest
python -m pytest            # 테스트 23개
python examples/demo_6_30.py
```

## 판정 요약 (규제지역, 시행 후)
| 차주 | LTV |
|---|---|
| 무주택 일반 / 처분조건부 1주택 | 40% |
| 생애최초 | 70% |
| 서민·실수요자 | 60% |
| 유주택(비처분 1주택+) | 0% |
| 다주택 | 0% |
| 경과규정 해당 | 종전규정 70% |
| 정책대출 | Discovery(수동) |

> ⚠️ brief §15 초기 TC001(1주택=40%)은 FAQ Q2 확정 전 값. 확정 사실은 **유주택(비처분)=0%**, 처분조건부만 40%.
