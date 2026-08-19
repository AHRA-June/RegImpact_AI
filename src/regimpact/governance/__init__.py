"""AI 거버넌스 산출물 — Model/System Card + AI Risk Register.

리스크 판단(발생가능성·영향)은 사람이 `risk.py` 에 적고, 정량 수치는 검증보고서와 같은
`ValidationEvidence` 에서 온다. 두 문서가 서로 다른 숫자를 말하는 일이 없다.

    from regimpact.governance import render_card, render_register
    from regimpact.report import collect
    ev = collect()
    print(render_card(ev)); print(render_register(ev))
"""
from .card import render as render_card
from .register import render as render_register
from .risk import RISKS, Band, Control, ControlState, Risk, by_category, heatmap, summary

__all__ = [
    "render_card", "render_register",
    "RISKS", "Risk", "Control", "ControlState", "Band",
    "by_category", "heatmap", "summary",
]
