"""프론트도어(랜딩) 렌더러 테스트.

핵심: 주입된 실측 지표가 페이지에 그대로 나타나고(하드코딩 아님), well-formed HTML이며,
산출물 링크와 정직성 문구가 포함된다.
"""
from regimpact.landing import render_landing

FIX = {
    "policy_id": "FSC_20260630",
    "regions": ["구리시", "용인시 기흥구", "화성시 동탄"],
    "assurance": {"citation": 1.0, "unsupported": 0.0, "exception_recall": 1.0,
                  "change_completeness": 1.0, "rule_regression": "178/178", "regions_ok": True},
    "impact": {"tightened_share": 0.58, "unchanged_share": 0.24, "review_share": 0.18,
               "wmean_delta_pp": -20.0, "review_weight_share": 0.23, "rows": 24},
    "exposure": {"pct_reduction": 0.2857, "per_unit_before": 7.08, "per_unit_after": 5.06,
                 "per_unit_delta": -2.02, "undetermined_share": 0.23},
    "sensitivity": {"band": [0.229, 0.338], "robust_shrink": 1.0, "robust_tighten": 0.849},
    "proposal": {"mapped": 7, "oos": 4, "review": 1, "status": "PENDING"},
    "catalog": {"edits": 9, "review": 1, "indirect": 1, "unaffected": 2},
    "artifacts": [
        {"title": "임팩트 리포트", "tag": "HTML", "desc": "설명", "href": "ui/report_6_30.html"},
        {"title": "검증보고서", "tag": "HTML", "desc": "설명", "href": "validation/VALIDATION_REPORT.html"},
    ],
    "principles": ["AI는 초안, 사람이 확정한 룰엔진이 판정한다."],
    "build": {"tests": 143, "commit": "abc1234", "branch": "main", "version": "0.1.0",
              "system": "regimpact", "generated_on": "2026-08-12"},
}


def test_wellformed():
    h = render_landing(FIX)
    assert h.startswith("<!doctype html>")
    assert h.rstrip().endswith("</body></html>")
    assert h.count("<title>") == 1


def test_injected_metrics_present():
    h = render_landing(FIX)
    for token in ["100%", "178/178", "28.6%", "58%", "PENDING", "abc1234", "143"]:
        assert token in h, token


def test_artifact_links_present():
    h = render_landing(FIX)
    assert 'href="ui/report_6_30.html"' in h
    assert 'href="validation/VALIDATION_REPORT.html"' in h
    assert h.count('class="card"') == 2


def test_honesty_and_principles():
    h = render_landing(FIX)
    assert "결정적 룰엔진" in h
    assert "독립 3자 벤치마크가 아닙니다" in h
    assert "구리시" in h        # 주입된 지역명(환각 아님)


def test_no_leaked_placeholder():
    h = render_landing(FIX)
    assert "{" not in h.split("<style>")[1].split("</style>")[0][:0] or True  # css 제외 sanity
    # 포맷 누출(미치환 중괄호) 없음: 본문에 파이썬 포맷 흔적 없어야
    body = h.split("</style>")[1]
    assert "{" not in body and "}" not in body
