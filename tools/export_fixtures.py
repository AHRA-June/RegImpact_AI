"""회귀 픽스처 export — Python 엔진/오라클의 판정을 JSON으로 고정한다.

용도: 웹 샌드박스(web/sandbox.html)에 박히는 '골든 기대값'의 출처를 사람 손이 아니라
**실제 Python 엔진 실행**으로 만든다. 브라우저의 JS 포팅본은 이 JSON과 대조되어,
두 구현이 어긋나면 화면에 즉시 드러난다(= 포팅 드리프트 탐지).

실행:  python tools/export_fixtures.py
출력:  web/fixtures.json
"""
from __future__ import annotations

import dataclasses
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regimpact.rule_engine import evaluate                      # noqa: E402
from regimpact.tc_generator.generator import generate_all       # noqa: E402


def _jsonable(v):
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "value"):          # Enum
        return v.value
    if isinstance(v, tuple):
        return list(v)
    return v


def _dump(obj) -> dict:
    return {k: _jsonable(v) for k, v in dataclasses.asdict(obj).items()}


def build() -> dict:
    cases = []
    for c in generate_all():
        decision = evaluate(c.app)
        cases.append({
            "case_id": c.case_id,
            "category": c.category.value,
            "description": c.description,
            "spec_note": c.spec_note,
            "input": _dump(c.app),
            "engine": _dump(decision),      # 실제 Python 엔진 출력 (= 골든)
            "oracle": _dump(c.expected),    # 독립 명세 오라클 기대값
        })
    return {
        "generated_by": "tools/export_fixtures.py",
        "spec": "docs/05_RULE_SPEC.md v1 (§C·§E·§F·§H)",
        "case_count": len(cases),
        "cases": cases,
    }


if __name__ == "__main__":
    out = ROOT / "web" / "fixtures.json"
    out.parent.mkdir(exist_ok=True)
    payload = build()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} — {payload['case_count']} cases")
