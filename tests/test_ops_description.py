"""현업용 상품설명서 — 손으로 적은 숫자가 없는지, 저장소 문서가 낡지 않았는지 고정한다.

이 문서는 제출용이고, 제출 문서의 수치가 실제와 갈라지는 것이 이 저장소에서 가장 자주
일어난 사고였다(2026-08-21 지원서 점검). 그래서 두 가지를 검사한다.

  ① 렌더러에 도메인 수치 리터럴이 없다      — 검증보고서와 같은 원칙
  ② `docs/business/OPS_PRODUCT_DESCRIPTION.md` 가 지금 시스템에서 다시 나온 것과 같다
     — 코드가 바뀌었는데 문서를 안 돌리면 여기서 걸린다
"""
import re
from pathlib import Path

import pytest

from regimpact.business import ops_description as od
from regimpact.report import collect

REPO = Path(__file__).resolve().parents[1]
RENDERER = Path(od.__file__)
DOC = REPO / "docs" / "business" / "OPS_PRODUCT_DESCRIPTION.md"


@pytest.fixture(scope="module")
def evidence():
    return collect(generated_at="2026-01-01 00:00 UTC")


@pytest.fixture(scope="module")
def doc(evidence):
    return od.render(evidence)


# ---------- 실측을 싣는 절에는 수치 리터럴이 없어야 한다 ----------
#
# **실측 절**은 현재 측정값을 싣는 곳이므로 숫자가 박히면 안 된다. **서술 절**은 수사(修辭)와
# 사람의 경력처럼 엔진이 만들 수 없는 값을 담는다 — 거기에는 리터럴이 있어야 정상이다.
MEASUREMENT_SECTIONS = [
    "_header", "_one_line", "_dday", "_outputs", "_category_table", "_matrix",
    "_portfolio", "_rulechange", "_trust", "_not_measured_table", "_verify",
]
NARRATIVE_SECTIONS = ["_not_automated", "_team"]


def _section_source(name: str) -> str:
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
def test_measurement_sections_have_no_count_literals(section):
    """"변경 75건" 같은 건수도 손으로 적으면 안 된다."""
    found = set(re.findall(r"(?<![\w.])(\d[\d,]*)\s*(?:건|행|곳)", _section_source(section)))
    assert not found, f"{section} 에 하드코딩된 건수: {sorted(found)}"


def test_narrative_sections_are_actually_narrative():
    """면제 목록에 실측 절을 몰래 넣으면 검사가 통째로 비므로, 서술 절인지 확인한다."""
    has_literals = [s for s in NARRATIVE_SECTIONS
                    if re.search(r"(?<![\w.])\d{1,3}[.\d]*\s*%", _section_source(s))]
    assert "_team" in has_literals, "팀 절이 경력 수치를 잃었다"


# ---------- 문서 수치가 실측치와 일치하는가 ----------
def test_extraction_and_matrix_numbers_match_evidence(doc, evidence):
    assert f"변경 **{len(evidence.extraction.changes)}건**" in doc
    assert f"업무영역별 조치 **{len(evidence.matrix.rows)}행**" in doc
    assert f"시행 전 필수 **{len(evidence.matrix.d_minus_required)}건**" in doc


def test_portfolio_numbers_match_evidence(doc, evidence):
    im = evidence.impact
    assert f"신청건 **{im.portfolio_size:,}건**" in doc
    assert f"한도 감소 **{len(im.reduced)}건**" in doc
    assert f"{im.grandfathered_count:,}건" in doc


def test_regression_and_consistency_match_evidence(doc, evidence):
    r = evidence.regression
    cs = evidence.consistency.summary()
    assert f"{r.passed}/{r.total}" in doc
    assert f"{cs['passed']}/{cs['total']} 통과" in doc


def test_human_review_is_reported_with_reasons(doc, evidence):
    """사람에게 넘긴 건을 **사유 없이** 넘기지 않는다는 주장이 문서에서 실제로 지켜지는지."""
    im = evidence.impact
    assert f"사람 검토 **{im.human_review_count}건**" in doc
    for code in im.escalation_reasons:
        assert f"`{code}`" in doc, f"에스컬레이션 사유 {code} 가 문서에 없다"


def test_not_measured_metrics_are_named_not_hidden(doc, evidence):
    """미측정을 통과로 세지 않는다는 문장이 참이 되려면, 무엇이 미측정인지 적혀 있어야 한다."""
    unmeasured = [m.threshold.metric for d in evidence.scorecard.dimensions
                  for m in d.metrics if getattr(m.verdict, "name", "") == "NOT_MEASURED"]
    for name in unmeasured:
        assert name in doc, f"미측정 지표 {name} 가 문서에 이름으로 남지 않았다"


def test_synthetic_portfolio_is_disclosed(doc):
    assert "합성" in doc and "실제 고객 데이터는 쓰지 않았다" in doc


# ---------- 저장소에 커밋된 문서가 낡지 않았는가 ----------
def _normalize(text: str) -> str:
    """실행마다 달라지는 것만 지운다 — 생성 시각과 감사로그 해시."""
    text = re.sub(r"\b[0-9a-f]{16,}\b", "<hash>", text)
    text = re.sub(r"^\| 생성 시각 \|.*$", "| 생성 시각 | <stamp> |", text, flags=re.M)
    text = re.sub(r"\(생성 .*? · provider", "(생성 <stamp> · provider", text)
    return text


def test_committed_document_is_current(doc):
    """코드가 바뀌었는데 문서를 다시 안 돌린 상태를 잡는다.

    고치는 법: `python examples/build_ops_description.py`
    """
    assert DOC.exists(), f"{DOC} 가 없다 — build_ops_description.py 를 돌린다"
    assert _normalize(DOC.read_text(encoding="utf-8")) == _normalize(doc), \
        "저장소 문서가 지금 시스템과 다르다 — python examples/build_ops_description.py"
