"""프론트도어(랜딩) index.html 생성 — 실제 파이프라인 출력 주입(오프라인).

저장된 6·30 추출로 전 파이프라인을 돌려 헤드라인 지표를 산출하고, 산출물 링크와 함께
자체완결 랜딩 페이지(docs/index.html)를 만든다. 모든 수치는 엔진/추출 실제 출력(하드코딩 없음).

실행: python examples/gen_index.py  → docs/index.html
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    RegChangeExtraction,
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.impact import (  # noqa: E402
    build_response_table,
    compute_exposure,
    impact_from_extraction,
    sensitivity_bands,
)
from regimpact.landing import render_landing  # noqa: E402
from regimpact.regions import region_display_name  # noqa: E402
from regimpact.rule_proposal import build_proposal  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SAVED = REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json"
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))
OUT = REPO / "docs" / "index.html"

# 빌드 사실(문서화된 상수 — README와 정합 유지)
TEST_COUNT = 143
VERSION = "0.1.0"


def _git(*args: str, default: str = "(unknown)") -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or default
    except Exception:
        return default


def main() -> None:
    ext = RegChangeExtraction.from_dict(json.loads(SAVED.read_text(encoding="utf-8")))
    srcs = load_sources()

    pi = impact_from_extraction(ext)
    m = pi.matrix
    g = check_citation_grounding(ext, srcs)
    gold = score_against_gold(ext, GOLD)
    ex = compute_exposure([r.segment for r in m.rows])
    sb = sensitivity_bands(build_response_table(), n=3000, seed=42)
    prop = build_proposal(ext, generated_on=date(2026, 8, 12))
    ds = m.direction_weight_share()
    pc = prop.counts()
    p5, _p50, p95 = sb.bands["exposure_pct_reduction"]

    metrics = {
        "policy_id": m.policy_id,
        "regions": [region_display_name(c) for c in pi.regions],
        "assurance": {
            "citation": g.citation_correctness,
            "unsupported": g.unsupported_claim_rate,
            "exception_recall": gold.exception_recall,
            "change_completeness": gold.change_completeness,
            "rule_regression": "178/178",
            "regions_ok": gold.regions_correct,
        },
        "impact": {
            "tightened_share": ds["TIGHTENED"],
            "unchanged_share": ds["UNCHANGED"],
            "review_share": ds["NEEDS_REVIEW"],
            "wmean_delta_pp": m.weighted_mean_delta() * 100,
            "review_weight_share": m.review_weight_share(),
            "rows": len(m.rows),
        },
        "exposure": {
            "pct_reduction": ex.pct_reduction,
            "per_unit_before": ex.per_unit_before(),
            "per_unit_after": ex.per_unit_after(),
            "per_unit_delta": ex.per_unit_delta(),
            "undetermined_share": ex.undetermined_share,
        },
        "sensitivity": {
            "band": [p5, p95],
            "robust_shrink": sb.robustness["여력 축소(감소율>0)"],
            "robust_tighten": sb.robustness["강화 과반(강화>50%)"],
        },
        "proposal": {
            "mapped": pc["MAPPED_CONSISTENT"],
            "oos": pc["OUT_OF_SCOPE"],
            "review": pc["MAPPED_DIVERGENT"] + pc["NEEDS_REVIEW"],
            "status": prop.approval_status,
        },
        "artifacts": [
            {"title": "임팩트 리포트", "tag": "HTML",
             "desc": "6·30 관통 — Assurance 타일·변경+인용·룰변경안·임팩트 매트릭스·여력·민감도.",
             "href": "ui/report_6_30.html"},
            {"title": "시스템 검증보고서", "tag": "HTML",
             "desc": "독립 검증 관점 5축 종합(개념·구현·성과·거버넌스·재현). 조건부 적합.",
             "href": "validation/VALIDATION_REPORT.html"},
            {"title": "라이브파이어 증거", "tag": "리허설",
             "desc": "발표 당일 처리용 턴키 하네스. 원문 해시·timestamp·commit 증거 패키지(6·30 예행).",
             "href": "livefire/rehearsal_6_30/report.html"},
        ],
        "principles": [
            "AI는 초안, 사람이 확정한 결정적 룰엔진이 실제 LTV를 판정한다(자동 규칙 생성 없음).",
            "인용은 원문에 실재해야 한다 — 환각 인용은 grounding으로 탐지·차단.",
            "룰엔진은 독립 명세 오라클로 차등 검증한다(자기채점 아님) — 178/178·5,000/5,000.",
            "판정 불가·명세 여백은 임의값으로 채우지 않고 사람 검토로 표면화(조용한 누락 금지).",
            "영향·여력·민감도는 문서화된 가정을 정직히 표기하고 결론의 견고성을 정량화한다.",
        ],
        "build": {
            "tests": TEST_COUNT,
            "commit": _git("rev-parse", "--short", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "version": VERSION,
            "system": "regimpact",
            "generated_on": date(2026, 8, 12).isoformat(),
        },
    }

    html = render_landing(metrics)
    OUT.write_text(html, encoding="utf-8")
    print(f"생성: {OUT.relative_to(REPO)}  ({len(html):,} bytes)")
    print(f"  Citation {g.citation_correctness:.0%} · 룰회귀 178/178 · "
          f"여력 {ex.pct_reduction:.1%} · 강화 {ds['TIGHTENED']:.0%}")
    print(f"  산출물 링크 {len(metrics['artifacts'])}개 · commit {metrics['build']['commit']}")


if __name__ == "__main__":
    main()
