"""RegImpact AI — UI 렌더 레이어 (화면 = 엔진/평가 산출물).

각 화면 렌더러는 `ImpactMatrix`·RegChange gold·rule_engine 상수·tc_generator 회귀·합성
포트폴리오 집계에서 HTML을 생성한다. 디자인 시스템은 `chrome.page()`가 공유하고, 값은
손으로 적지 않으므로 Stitch 목업의 환각이 재발할 수 없다.

화면 → data-path:
- regchange.render()   regulatory-analysis  (규제 변경 분석)
- impact_matrix.render() impact-matrix       (임팩트 매트릭스)
- rule_proposal.render() rule-amendments     (Rule 변경안)
- assurance.render()   verification-assurance (검증)
- portfolio.render()   portfolio-impact       (고객·포트폴리오 영향)
"""
from . import assurance, impact_matrix, portfolio, regchange, report, rule_proposal
from .chrome import page
from .render_all import GENERATED_DIR, SCREENS, render_all

__all__ = [
    "page",
    "render_all",
    "SCREENS",
    "GENERATED_DIR",
    "regchange",
    "impact_matrix",
    "rule_proposal",
    "assurance",
    "portfolio",
    "report",
]
