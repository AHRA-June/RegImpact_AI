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

from regimpact.models import RegionStatus                       # noqa: E402
from regimpact.regions import (                                 # noqa: E402
    ALIASES, REGISTRY, SIDO_ORDER, resolve_region_status,
)
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


def export_regions() -> list[dict]:
    """전국 지역 레지스트리를 그대로 내보낸다.

    웹 샌드박스가 241개 지역표를 JS에 다시 옮겨 적으면 그 전사(轉寫)가 다음 사고가 된다.
    데이터는 `regions.REGISTRY` 하나만 두고, JS는 여기서 내보낸 것을 읽어 해석만 한다.
    """
    order = {sido: i for i, sido in enumerate(SIDO_ORDER)}
    regions = sorted(REGISTRY.values(), key=lambda r: (order.get(r.sido, 99), r.name))
    return [
        {
            "code": r.code,
            "sido": r.sido,
            "name": r.name,
            "capital_area": r.capital_area,
            "versions": [
                {
                    "status": v.status.value,
                    "from": v.effective_from.isoformat() if v.effective_from else None,
                    "to": v.effective_to.isoformat() if v.effective_to else None,
                    "regulated_type": v.regulated_type.value,
                }
                for v in r.versions
            ],
        }
        for r in regions
    ]


# 지역 시점해석 프로브 — 전국 × 주요 시점의 Python 판정을 문자열로 압축해 고정한다.
# 웹의 JS 해석기가 이 표와 한 글자라도 다르면 즉시 드러난다(전국 단위 대조).
PROBE_DATES = [
    "2016-11-02",  # 강남4구 조정 지정 전일
    "2016-11-03",  # 강남4구 조정 지정일
    "2017-08-03",  # 강남4구 투기과열 전환
    "2025-10-15",  # 서울21구·경기12곳 지정 전일
    "2025-10-16",  # 위 지정일
    "2026-06-30",  # 6·30 신규지정 효력 전일
    "2026-07-01",  # 6·30 신규지정 효력일
]
_PROBE_LETTER = {
    RegionStatus.REGULATED: "R",
    RegionStatus.NON_REGULATED: "N",
    RegionStatus.UNKNOWN: "U",
}


def export_region_probe() -> dict:
    dates = [date.fromisoformat(d) for d in PROBE_DATES]
    return {
        "dates": PROBE_DATES,
        "status": {
            code: "".join(_PROBE_LETTER[resolve_region_status(code, d)[0]] for d in dates)
            for code in sorted(REGISTRY)
        },
    }


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
        "regions_source": "docs/sources/raw/molit_press_20260630.txt 참고2 현황표",
        "case_count": len(cases),
        "regions": export_regions(),
        "region_probe": export_region_probe(),
        "region_aliases": dict(ALIASES),
        "cases": cases,
    }


if __name__ == "__main__":
    out = ROOT / "web" / "fixtures.json"
    out.parent.mkdir(exist_ok=True)
    payload = build()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} — {payload['case_count']} cases, "
          f"{len(payload['regions'])} regions, "
          f"{len(payload['region_probe']['status'])}×{len(PROBE_DATES)} region probes)")
