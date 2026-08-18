"""E2E 결과 export — 검증보고서 웹 페이지(web/impact.html)가 읽을 JSON.

샌드박스와 같은 원칙: 웹은 숫자를 스스로 계산하지 않는다. Python 파이프라인이 산출한 값을
그대로 싣는다(전사·재구현 없음). 따라서 이 파일은 룰이 바뀌면 반드시 다시 돌려야 한다.

실행:  python tools/export_impact.py
출력:  web/impact.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regimpact.impact import Phase, render_report, run_e2e   # noqa: E402

GOLD = json.loads((ROOT / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def build() -> dict:
    r = run_e2e(gold=GOLD)
    impact, m = r.impact, r.matrix
    no_event = impact.no_event_only()

    return {
        "generated_by": "tools/export_impact.py",
        "policy_id": m.policy_id,
        "effective_from": m.effective_from,
        "completed": r.completed,
        "stages": [
            {"name": s.name, "status": s.status.value, "detail": s.detail, "metrics": s.metrics}
            for s in r.stages
        ],
        "source_digests": r.source_digests,
        "policy_version_diff": r.policy_version_diff,
        "headline": {
            "portfolio_n": impact.total,
            "no_event_n": no_event.total,
            "no_event_impacted_rate": no_event.impacted_rate,
            "no_event_limit_delta_eok": no_event.limit_delta_sum_eok,
            "grandfathered": impact.grandfathered,
            "protected": impact.protected_by_grandfathering,
            "escalated": impact.escalated,
            "escalation_rate": impact.escalation_rate,
            "tightened": impact.tightened(),
            "loosened": impact.loosened(),
        },
        "by_region_group": [
            {"label": k, "n": v.n, "impacted_rate": v.impacted_rate,
             "grandfathered": v.grandfathered, "protected": v.protected,
             "escalation_rate": v.escalation_rate, "limit_delta_eok": v.limit_delta_sum_eok}
            for k, v in impact.by_region_group().items()
        ],
        "by_borrower": [
            {"label": k, "n": v.n, "impacted_rate": v.impacted_rate,
             "escalation_rate": v.escalation_rate}
            for k, v in impact.by_borrower().items()
        ],
        "segments_note": "경과규정 미해당 층 기준 — 전체 격자로 평균 내면 경과규정 건(3/4)이 섞여 변경 크기가 왜곡된다",
        "segments": [
            {"region_group": s.region_group, "borrower": s.borrower_label, "n": s.n,
             "impacted_rate": s.impacted_rate, "escalation_rate": s.escalation_rate,
             "ltv_before": s.avg_ltv_before, "ltv_after": s.avg_ltv_after,
             "ltv_delta": s.avg_ltv_delta, "limit_delta_eok": s.limit_delta_sum_eok,
             "top_transition": s.top_transition}
            for s in no_event.segments
        ],
        "proposals": [
            {"before": p.rule_id_before, "after": p.rule_id_after,
             "ltv_before": p.ltv_before, "ltv_after": p.ltv_after,
             "affected": p.affected, "segments": list(p.segments),
             "sources": list(p.source_policy_ids)}
            for p in r.proposals
        ],
        "escalation_reasons": impact.escalation_reasons(),
        "phases": [p.value for p in (Phase.BEFORE_DDAY, Phase.AFTER_EFFECTIVE,
                                     Phase.SEPARATE_TRIGGER)],
        "matrix": [
            {
                "area": row.area, "change": row.change,
                "evidence": [e.render() for e in row.evidence],
                "target": row.target, "deliverable": row.deliverable,
                "priority": row.priority.value, "phase": row.phase.value,
                "owner": row.owner.value, "approval": row.approval.value,
                "automation": row.automation.value, "provenance": row.provenance.value,
                "human_review_reason": row.human_review_reason,
                "metrics": row.metrics,
                "discovery": row.area.startswith("[Discovery]"),
            }
            for row in m.rows
        ],
        "report_markdown": render_report(r),
    }


if __name__ == "__main__":
    out = ROOT / "web" / "impact.json"
    payload = build()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} — {len(payload['matrix'])} matrix rows, "
          f"{len(payload['stages'])} stages, {len(payload['segments'])} segments")
