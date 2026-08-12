"""라이브파이어 하네스 테스트 (evidence package 무결성·구조).

검증 축:
  1. 하네스 턴키 — run_livefire가 증거 패키지 5종을 남긴다.
  2. 무결성 고정 — 원문 sha256이 registry(SOURCES.md)와 일치, 추출 해시 결정적.
  3. 매니페스트 필수 필드 — §19 증거요소(원문해시·timestamp·commit·버전·산출물) 존재.
  4. Assurance/헤드라인 결정적 값 — 6·30 리허설 실측값 고정(회귀).
  5. 정직성 — REHEARSAL은 예행연습임을 매니페스트·기록에 명시.
  6. 신규 정책(gold=None) — recall 미산정 + 골드 미비 고지.
"""
import json
from datetime import date
from pathlib import Path

from regimpact.extractor import RegChangeExtraction, load_sources
from regimpact.livefire import render_evidence_record, run_livefire, sha256_file

REPO = Path(__file__).resolve().parents[1]
SAVED = json.loads((REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json").read_text(encoding="utf-8"))
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))
SRC = REPO / "docs" / "sources" / "original"
SOURCE_FILES = [
    ("FSC_PRESS_20260630", SRC / "fsc_press_20260630.pdf"),
    ("MOLIT_PRESS_20260630", SRC / "molit_press_20260630.pdf"),
    ("FAQ_20260630", SRC / "faq_20260630.hwp"),
]
TS = "2026-08-12T09:00:00+09:00"
COMMIT = "deadbeef" * 5


def _run(tmp_path, mode="REHEARSAL", gold=GOLD):
    ext = RegChangeExtraction.from_dict(SAVED)
    return run_livefire(
        extraction=ext, extraction_dict=SAVED, sources=load_sources(),
        source_files=SOURCE_FILES, out_dir=tmp_path, mode=mode, gold=gold,
        label="6·30 (test)", generated_on=date(2026, 8, 12),
        analysis_timestamp=TS, system_commit=COMMIT,
    ), tmp_path


def test_evidence_package_written(tmp_path):
    _, out = _run(tmp_path)
    for name in ("manifest.json", "report.html", "extraction.json",
                 "impact_summary.json", "README.md"):
        assert (out / name).exists(), name


def test_source_hashes_match_registry(tmp_path):
    m, _ = _run(tmp_path)
    # 매니페스트 해시 == 파일 재해시 (무결성 고정)
    for s in m.sources:
        path = next(p for did, p in SOURCE_FILES if did == s.doc_id)
        assert s.sha256 == sha256_file(path)
    # SOURCES.md registry 에도 동일 해시가 등재돼 있어야 함
    registry = (REPO / "docs" / "sources" / "SOURCES.md").read_text(encoding="utf-8")
    for s in m.sources:
        assert s.sha256 in registry, s.doc_id


def test_extraction_hash_deterministic(tmp_path):
    m1, _ = _run(tmp_path / "a")
    m2, _ = _run(tmp_path / "b")
    assert m1.extraction_sha256 == m2.extraction_sha256
    assert len(m1.extraction_sha256) == 64


def test_manifest_required_evidence_fields(tmp_path):
    m, out = _run(tmp_path)
    d = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for key in ("mode", "policy_id", "analysis_timestamp", "system_version",
                "system_commit", "sources", "extraction_sha256", "artifacts",
                "assurance", "headline", "honesty"):
        assert key in d, key
    assert d["analysis_timestamp"] == TS
    assert d["system_commit"] == COMMIT
    assert len(d["sources"]) == 3


def test_rehearsal_deterministic_assurance(tmp_path):
    m, _ = _run(tmp_path)
    a = m.assurance
    assert a["citation_correctness"] == 1.0
    assert a["unsupported_claim_rate"] == 0.0
    assert a["exception_recall"] == 1.0
    assert a["rule_regression"] == "178/178"
    h = m.headline
    assert h["direction_weight_share"]["TIGHTENED"] == 0.58
    assert abs(h["exposure_pct_reduction"] - 0.2857) < 1e-3


def test_rehearsal_labeled_as_not_real(tmp_path):
    m, out = _run(tmp_path, mode="REHEARSAL")
    assert m.mode == "REHEARSAL"
    assert any("예행연습" in n for n in m.honesty)
    record = (out / "README.md").read_text(encoding="utf-8")
    assert "예행연습" in record and "실제 라이브파이어" in record


def test_new_policy_without_gold(tmp_path):
    m, _ = _run(tmp_path, mode="LIVE", gold=None)
    # recall류는 골드 없으면 미산정
    assert "exception_recall" not in m.assurance
    assert "change_completeness" not in m.assurance
    # 정답 불필요 지표는 여전히 보고
    assert "citation_correctness" in m.assurance
    assert m.assurance["rule_regression"] == "178/178"
    assert any("골드셋 미비" in n for n in m.honesty)
    record = render_evidence_record(m)
    assert "골드셋 미비" in record
