"""첫 Assurance 실측 회귀 고정 — docs/eval/regchange_extracted_6_30.json 을
결정론 채점 하네스에 통과시켜 지표를 잠근다(회귀 방지).

측정 대상(metrics_spec.md dimension ①②③):
    Citation Correctness / Unsupported / Change Completeness / Exception Recall /
    Effective-date / Region.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))
EXTRACTED = json.loads((ROOT / "docs/eval/regchange_extracted_6_30.json").read_text(encoding="utf-8"))


def _ext():
    return RegChangeExtraction.from_dict(EXTRACTED)


def test_all_citations_grounded_verbatim():
    """실측 지표: Citation Correctness 100%, Unsupported 0% (인용 전부 원문 verbatim)."""
    g = check_citation_grounding(_ext(), load_sources())
    assert g.total == 10
    assert g.grounded == 10
    assert g.citation_correctness == 1.0
    assert g.unsupported_claim_rate == 0.0
    assert g.ungrounded == []


def test_gold_completeness_and_recall_measured():
    """실측 지표(v2 반복 후): Change Completeness 100%, Exception Recall 100%, 시점·지역 OK.

    v1(9건)은 서민·실수요 누락으로 Exception Recall 50%였으나, FAQ Q2 원문 근거로
    서민·실수요 예외 항목을 보완(v2) → 100%. Assurance 피드백 루프로 완전성 개선.
    """
    s = score_against_gold(_ext(), GOLD)
    assert s.change_completeness == 1.0
    assert s.exception_recall == 1.0
    assert s.missed_exceptions == []
    assert s.effective_date_correct is True
    assert s.regions_correct is True
    assert s.missed_changes == []


def test_extraction_meta_provenance_present():
    """산출물에 provenance(무인 API 실행 아님)가 명시돼야 한다(정직성)."""
    assert "_meta" in EXTRACTED
    assert "provenance" in EXTRACTED["_meta"]
