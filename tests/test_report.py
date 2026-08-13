"""검증보고서 생성기 테스트 — 라이브 수치로 조립되고 핵심 섹션·정직성 문구를 포함한다."""
from regimpact import rule_engine
from regimpact.report import build_validation_report, discrimination_pairs, e2e_control


def test_report_builds_with_key_sections():
    md = build_validation_report()
    for section in ["검증보고서", "Impact Matrix", "Rule Change Proposal",
                    "판별력", "검증의 한계", "결론"]:
        assert section in md
    # 라이브 수치가 실제로 박혀 있어야 함
    assert "3024/3024" in md
    assert "115문항" in md
    assert "AI_DRAFT" in md


def test_report_does_not_leak_engine_mutation():
    """보고서 생성이 엔진 상수를 변조 후 복원해야 한다(부작용 없음)."""
    before = rule_engine.LTV_REGULATED_STANDARD
    build_validation_report()
    assert rule_engine.LTV_REGULATED_STANDARD == before


def test_report_includes_honest_limits():
    md = build_validation_report()
    # 오염·순환·미측정을 숨기지 않았는지
    assert "오염" in md
    assert "독립 성능치는 아직 미측정" in md


def test_discrimination_pairs_show_dynamic_range():
    pairs = discrimination_pairs()
    assert pairs
    assert all(p.detects for p in pairs)      # 전 지표가 오류에 하락
    good_ok, bad_ok = e2e_control()
    assert good_ok is True and bad_ok is False
