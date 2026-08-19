"""검증보고서 — 손으로 적은 숫자가 없는지, 실측치와 맞는지 고정한다.

보고서에 하드코딩된 수치가 하나라도 있으면 그 보고서는 시간이 지나며 조용히 거짓말이 된다.
UI 그라운딩 테스트(`tests/test_ui.py`)와 같은 방향이다.
"""
import re
from pathlib import Path

import pytest

from regimpact import rule_engine
from regimpact.report import collect, render
from regimpact.report import validation_report as vr

RENDERER = Path(vr.__file__)


@pytest.fixture(scope="module")
def evidence():
    return collect(generated_at="2026-01-01 00:00 UTC")


@pytest.fixture(scope="module")
def report(evidence):
    return render(evidence)


# ---------- 실측을 싣는 절에는 수치 리터럴이 없어야 한다 ----------
#
# 검사 대상을 절 단위로 나눈다. **실측 절**(현재 측정값을 싣는 곳)에 숫자가 박히면
# 엔진이 바뀌어도 보고서가 안 바뀌므로 금지한다. 반면 **서술 절**은 과거 값을 인용한다 —
# §12 발견사항의 "Exception Recall 50%였다"는 그 시점의 사실이고 지금 값으로 바뀌면 안 된다.
MEASUREMENT_SECTIONS = [
    "_summary", "_s7_implementation", "_s8_extraction",
    "_s9_outcomes", "_s10_governance", "_s13_reproducibility", "_s14_conclusion",
]
NARRATIVE_SECTIONS = ["_s3_method", "_s11_limits", "_s12_findings"]


def _section_source(name: str) -> str:
    """렌더러 소스에서 함수 하나의 본문을 떼어낸다."""
    source = RENDERER.read_text(encoding="utf-8")
    start = source.index(f"def {name}(")
    rest = source[start:]
    end = rest.find("\ndef ", 1)
    body = rest if end == -1 else rest[:end]
    return re.sub(r"\{[^{}]*\}", "", body)      # f-string 표현식은 계산식이므로 제외


@pytest.mark.parametrize("section", MEASUREMENT_SECTIONS)
def test_measurement_sections_have_no_percentage_literals(section):
    found = set(re.findall(r"(?<![\w.])(\d{1,3})\s*%", _section_source(section)))
    assert not found, f"{section} 에 하드코딩된 백분율: {sorted(found)}"


@pytest.mark.parametrize("section", MEASUREMENT_SECTIONS)
def test_measurement_sections_have_no_ltv_decimal_literals(section):
    found = set(re.findall(r"(?<![\w.])0\.\d{1,2}(?![\d])", _section_source(section)))
    assert not found, f"{section} 에 하드코딩된 LTV 소수: {sorted(found)}"


def test_narrative_sections_are_actually_narrative():
    """서술 절 면제가 무력화되지 않았는지 확인한다.

    면제 목록에 실측 절을 몰래 넣으면 검사가 통째로 비는데, 그러면 이 테스트가 실패한다
    — 서술 절은 과거 수치를 인용하므로 리터럴이 **있어야** 정상이다.
    """
    has_literals = [s for s in NARRATIVE_SECTIONS
                    if re.search(r"(?<![\w.])\d{1,3}\s*%", _section_source(s))]
    assert "_s12_findings" in has_literals, \
        "발견사항 절이 과거 수치를 잃었다 — 기록이 지워졌는지 확인"


def test_renderer_reads_engine_constants_not_copies():
    """LTV 상수는 rule_engine 에서 읽어야 한다."""
    source = RENDERER.read_text(encoding="utf-8")
    assert "rule_engine.LTV_MULTI" in source
    assert "from ..grandfathering import CUTOFF" in source
    assert "from ..regions import REG_EFFECTIVE" in source


# ---------- 보고서 수치가 실측치와 일치하는가 ----------
def test_extraction_count_matches_evidence(report, evidence):
    assert f"변경 **{len(evidence.extraction.changes)}건**" in report


def test_regression_numbers_match_evidence(report, evidence):
    r = evidence.regression
    assert f"**{r.passed}/{r.total} ({r.pass_rate:.0%})**" in report


def test_citation_metrics_match_evidence(report, evidence):
    g = evidence.grounding
    assert f"{g.citation_correctness:.0%}** ({g.grounded}/{g.total})" in report


def test_coverage_numbers_match_evidence(report, evidence):
    im = evidence.impact
    assert f"**{im.decision_coverage:.1%}**" in report
    assert f"**{im.impact_coverage:.1%}**" in report


def test_consistency_verdict_matches_evidence(report, evidence):
    s = evidence.consistency.summary()
    assert f"{s['passed']}/{s['total']}" in report
    assert evidence.proposal.status.value in report


def test_audit_head_hash_is_in_the_report(report, evidence):
    """보고서가 감사로그의 외부 앵커 역할을 한다 — head 해시가 반드시 실려야 한다."""
    assert evidence.audit.head_hash in report


def test_region_registry_count_matches(report, evidence):
    assert f"**{evidence.baseline_region_count}곳**" in report


# ---------- 구조 ----------
@pytest.mark.parametrize("heading", [
    "## 5. 데이터 적정성 검증",
    "## 6. 개념적 건전성 검증",
    "## 7. 구현 정확성 검증",
    "## 10. 거버넌스 검증",
    "## 11. 한계 및 가정",
    "## 12. 발견사항 및 조치",
    "## 13. 재현성 및 감사추적",
])
def test_report_has_validation_report_sections(report, heading):
    """모델 검증보고서의 관례적 절을 갖춘다 — 검증인이 읽는 순서."""
    assert heading in report


def test_every_extracted_change_appears_in_appendix(report, evidence):
    """부록이 추출 전체를 싣는다 — 요약만 있고 원본이 없으면 검증할 수 없다."""
    appendix = report.split("## 부록 A")[1].split("## 부록 B")[0]
    rows = [ln for ln in appendix.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(rows) - 1 == len(evidence.extraction.changes)


def test_limitations_are_stated_not_hidden(report):
    """브리프 §12 — 한계를 숨기지 않는다."""
    for marker in ("L1", "L5", "L7"):
        assert f"| {marker} |" in report


def test_findings_include_self_discovered_defects(report):
    """자체 발견 결함을 기록하는 것이 §12의 목적이다."""
    for fid in ("R-01", "R-01b", "D-02", "D-03", "P-01", "C-01"):
        assert f"| {fid} |" in report


def test_report_is_long_enough_to_be_a_report(report):
    """브리프 §18: 검증보고서 15~20쪽. 한 쪽 ≈ 35줄로 잡는다."""
    assert len(report.splitlines()) >= 15 * 35


# ---------- 결정성 ----------
def test_render_is_deterministic_for_the_same_evidence(evidence):
    assert render(evidence) == render(evidence)


def test_conclusion_does_not_claim_full_automation(report, evidence):
    """미통과 항목이 남아 있는 동안 '완전 자동 승인'을 주장하면 안 된다."""
    if evidence.consistency.summary()["failed"]:
        assert "완전 자동 승인은 적절하지 않다" in report
