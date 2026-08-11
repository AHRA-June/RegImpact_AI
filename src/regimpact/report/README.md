# report — E2E 파이프라인 + Validation Report (Walking Skeleton)

6·30 1건을 **끝까지 관통**시키는 노드. 브리프 §18 코어 완성선의 마지막 단계.

```
Source Snapshot → Policy Version Resolution → Before/After(RegChange)
  → Impact Matrix → Structured Rule Proposal → Test Cases
  → Deterministic Rule Regression → Assurance → Human Review → Validation Report
```

## 설계
- 각 실제 노드(`rule_engine`·`impact`·`tc_generator`·`extractor`)를 **배선만** 한다.
- LLM 추출만 주입 가능한 stub(`offline_stub_extraction`)으로 두어 **API 키 없이 E2E 관통**.
  실제 LLM은 `run_e2e(complete=anthropic_completion())`로 주입.
- **LOCKED §4 준수:** 규칙 변경안 LTV 값은 `rule_engine` 상수(확정 명세)에서만 온다.
  추출은 '무엇이/언제/어디서'의 근거(citation)·메타만 제공 → 값과 근거의 출처 분리(검증 가능).
- 규칙 변경안은 `PENDING_HUMAN_APPROVAL` — §4 "AI초안→사람확정" 워크플로의 대상.

## 관통(e2e_ok) 판정
모든 노드가 산출물을 냈고 **Rule Regression Pass Rate = 100%** 일 때 성공.

## 구조
- `pipeline.py` — `run_e2e()` 오케스트레이터 + Source Snapshot·Policy Version·Human Review 게이트
- `proposal.py` — `build_proposal()` Structured Rule Change Proposal(승인 대기 초안)
- `render.py` — `render_markdown()` 사람이 읽는 Validation Report

## 사용
```python
import json
from regimpact.report import run_e2e, render_markdown

gold = json.load(open("docs/eval/regchange_gold_6_30.json", encoding="utf-8"))
rep = run_e2e(gold=gold)          # 오프라인 stub (complete 미주입)
print(rep.e2e_ok)                 # True
open("validation_report.md", "w").write(render_markdown(rep))
```

## 실행
```bash
python -m pytest tests/test_report.py
python examples/demo_e2e_report.py           # docs/eval/validation_report_6_30.md 생성
```

산출 예시: `docs/eval/validation_report_6_30.md`.
