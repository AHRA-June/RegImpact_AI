"""라이브파이어 예행연습(REHEARSAL) — 6·30 사건으로 하네스 턴키 검증.

⚠️ 이것은 **예행연습**이다. 6·30은 과거·골드셋 수록 사건이므로 **실제 라이브파이어가 아니다.**
   실제 Live Fire #1 은 다음 신규 대책 발표 당일 `mode="LIVE"` 로 돌린다(docs/livefire/README.md).

이 스크립트는 저장된 6·30 추출(오프라인, API 키 불필요)로 전 파이프라인을 돌려
증거 패키지(docs/livefire/rehearsal_6_30/: manifest.json·report.html·extraction.json·
impact_summary.json·README.md)를 생성한다 — 실제 발표일엔 추출만 실시간 LLM으로 바꾸면 된다.

실행: python examples/livefire_rehearsal.py

주의: 표준 데모 스모크 체인에는 넣지 않는다(증거 timestamp가 매번 바뀌지 않게 의도적 수동 실행).
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import RegChangeExtraction, load_sources  # noqa: E402
from regimpact.livefire import run_livefire  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SAVED = REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json"
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))
OUT = REPO / "docs" / "livefire" / "rehearsal_6_30"
SRC = REPO / "docs" / "sources" / "original"

# 리허설 기준시각(고정) — 예행연습이므로 재현 가능하게 못박는다. 실제 LIVE는 now()를 쓴다.
REHEARSAL_TS = "2026-08-12T09:00:00+09:00"

SOURCE_FILES = [
    ("FSC_PRESS_20260630", SRC / "fsc_press_20260630.pdf"),
    ("MOLIT_PRESS_20260630", SRC / "molit_press_20260630.pdf"),
    ("FAQ_20260630", SRC / "faq_20260630.hwp"),
]


def main() -> None:
    extraction_dict = json.loads(SAVED.read_text(encoding="utf-8"))
    extraction = RegChangeExtraction.from_dict(extraction_dict)
    sources = load_sources()

    manifest = run_livefire(
        extraction=extraction,
        extraction_dict=extraction_dict,
        sources=sources,
        source_files=SOURCE_FILES,
        out_dir=OUT,
        mode="REHEARSAL",
        label="6·30 규제지역 추가 지정 (예행연습)",
        gold=GOLD,
        generated_on=date(2026, 8, 12),
        analysis_timestamp=REHEARSAL_TS,   # 고정(리허설 재현성). LIVE는 생략 → now()
        report_title="6·30 규제 변경 영향분석 리포트 (라이브파이어 리허설)",
    )

    a, h = manifest.assurance, manifest.headline
    print(f"라이브파이어 리허설 생성: {OUT.relative_to(REPO)}/")
    print(f"  mode={manifest.mode} · policy={manifest.policy_id} · commit={manifest.system_commit[:12]}")
    print(f"  원문 {len(manifest.sources)}건 해시 고정 · 추출해시 {manifest.extraction_sha256[:12]}…")
    print(f"  Assurance: Citation {a['citation_correctness']:.0%} · 환각 {a['unsupported_claim_rate']:.0%} · "
          f"예외재현 {a.get('exception_recall',0):.0%} · 룰회귀 {a['rule_regression']}")
    band = h["sensitivity_pct_reduction_band"]
    print(f"  헤드라인: 강화 {h['direction_weight_share']['TIGHTENED']:.0%} · "
          f"여력 감소율 {h['exposure_pct_reduction']:.1%} (밴드 [{band[0]:.1%}, {band[1]:.1%}])")
    print(f"  산출물: {', '.join(manifest.artifacts.values())}")
    print(f"\n증거 기록: {(OUT / 'README.md').relative_to(REPO)}")


if __name__ == "__main__":
    main()
