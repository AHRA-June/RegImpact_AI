"""검증보고서 문서 테스트 — 구조·실측 정합성·분량.

핵심: 문서의 수치가 손으로 적힌 게 아니라 실제 산출물과 일치함을 검증한다.
"""
from regimpact.extractor import measured_assurance
from regimpact.report import build_validation_report
from regimpact.report_doc import build_validation_document


def test_document_has_all_sections():
    doc = build_validation_document()
    for section in [
        "검증보고서 (Validation Report)",
        "1. Executive Summary",
        "2. 서론 및 검증 범위",
        "3. 시스템 개요 및 아키텍처",
        "판정 알고리즘",
        "4. 데이터 및 원문 무결성",
        "5. 검증 방법론",
        "6. 검증 결과",
        "대표 사례 심층",
        "7. Assurance Layer",
        "8. 평가셋 설계 및 freeze",
        "9. 한계 및 알려진 이슈",
        "10. 거버넌스 및 통제",
        "11. 결론 및 권고",
        "부록 A", "부록 B", "부록 C", "부록 D", "부록 E",
    ]:
        assert section in doc, f"누락 섹션: {section}"


def test_document_is_substantial():
    doc = build_validation_document()
    # 15~20쪽 목표 — 최소 분량·구조 보장
    assert len(doc) > 15000
    assert doc.count("\n#") >= 30           # 헤딩
    assert doc.count("\n|---") >= 12        # 표


def test_document_values_match_live_measurements():
    """문서의 핵심 수치가 실제 산출물과 일치(지어내지 않음)."""
    r = build_validation_report()
    m = measured_assurance()
    doc = build_validation_document(r)
    # 골드셋 총 문항·DEV
    assert f"{r.gold_set['total']}문항" in doc
    # 추출 모델·인용 정확도
    assert m.model in doc
    assert f"{m.citation_correctness:.0%}" in doc
    # escalation 사유코드
    assert "OWNER_BASELINE_UNKNOWN" in doc
    # 전체 판정
    assert r.overall_status in doc


def test_no_fabricated_placeholder_or_mockup_values():
    doc = build_validation_document()
    # Stitch 목업의 환각 수치가 절대 없어야
    for bad in ["98.5%", "1,240건", "세종", "부산 해운대", "60% → 50%"]:
        assert bad not in doc
