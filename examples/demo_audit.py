"""Audit Trail 데모 — 파이프라인 이벤트를 해시 체인 감사로그에 기록·검증.

실행: python examples/demo_audit.py   (repo 루트, 의존성·API 키 불필요)
출력: docs/reports/audit_6_30.jsonl(감사로그) + 콘솔(검증·변조 탐지 시연).

시연: (1) 원문→추출→영향→제안→검토→회귀→Assurance→보고 이벤트 기록,
      (2) 체인 verify OK, (3) 한 항목을 사후 변조하면 verify가 잡아냄(tamper-evident).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.assurance import build_scorecard  # noqa: E402
from regimpact.audit import Action, AuditLog  # noqa: E402
from regimpact.extractor import load_sources  # noqa: E402
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402
from regimpact.impact import DEFAULT_REGION, SIX_THIRTY_SEGMENTS, analyze_from_extraction  # noqa: E402
from regimpact.proposal import ApprovalStatus, build_proposal, record_decision  # noqa: E402
from regimpact.tc_generator import generate_grid, run_regression  # noqa: E402

GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))
EXTRACTED = json.loads((ROOT / "docs/eval/regchange_extracted_6_30.json").read_text(encoding="utf-8"))


def _fixed_clock():
    """결정론 데모용 고정 시계(초 단위 증가). 실사용은 기본 UTC 실시간."""
    n = {"t": 0}

    def clock() -> str:
        n["t"] += 1
        return f"2026-08-13T09:00:{n['t']:02d}+00:00"
    return clock


def main() -> None:
    log = AuditLog(clock=_fixed_clock())

    # [1] Source ingestion (원문 hash 기록)
    sources = load_sources()
    for doc_id, text in sources.items():
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        log.record(Action.SOURCE_INGESTED, target=doc_id, details={"sha256": h[:16], "chars": len(text)})

    # [2] Extraction
    extraction = RegChangeExtraction.from_dict(EXTRACTED)
    log.record(Action.EXTRACTION, target=extraction.policy_id,
               details={"changes": len(extraction.changes),
                        "provenance": EXTRACTED.get("_meta", {}).get("iteration", "manual")})

    # [3] Impact Matrix
    matrix = analyze_from_extraction(extraction, SIX_THIRTY_SEGMENTS, DEFAULT_REGION)
    log.record(Action.IMPACT_ANALYZED, target=matrix.region_code,
               details={"segments": len(matrix.rows), "summary": matrix.summary()})

    # [4] Proposal + [7] Human Review
    proposal = build_proposal(matrix, extraction)
    log.record(Action.PROPOSAL_CREATED, target=proposal.proposal_id,
               details={"lines": len(proposal.lines), "approval": proposal.approval.status.value})
    proposal = record_decision(proposal, ApprovalStatus.APPROVED, reviewer="심사역")
    log.record(Action.HUMAN_REVIEW, target=proposal.proposal_id, actor="human:심사역",
               details={"decision": proposal.approval.status.value})

    # [5] Regression
    reg = run_regression(generate_grid())
    log.record(Action.REGRESSION_RUN, target="rule-grid",
               details={"passed": reg.passed, "total": reg.total, "pass_rate": round(reg.pass_rate, 4)})

    # [6] Assurance
    sc = build_scorecard(extraction, sources, GOLD, reg)
    log.record(Action.ASSURANCE_SCORED, target="4-dimension",
               details={"overall": sc.overall.value})

    # [8] Report
    log.record(Action.REPORT_GENERATED, target="validation_6_30",
               details={"formats": ["md", "html", "full"]})

    # --- 출력·검증 ---
    print(f"감사로그 {len(log)}건 기록. head={log.head_hash[:16]}…\n")
    for e in log.events:
        print(f"  #{e.seq} {e.timestamp} [{e.actor}] {e.action} → {e.target}  {e.details}")

    v = log.verify()
    print(f"\n무결성 검증: {'✅ OK' if v.ok else '❌ FAIL'}")

    # 변조 탐지 시연: 저장→로드→회귀 통과율(빨강을 초록으로) 위조→verify 실패
    reloaded = AuditLog.load_jsonl(log.to_jsonl())
    lines = reloaded.to_jsonl().splitlines()
    rev_idx = next(i for i, ln in enumerate(lines) if json.loads(ln)["action"] == Action.HUMAN_REVIEW)
    d = json.loads(lines[rev_idx])
    d["details"]["decision"] = "REJECTED"              # 사후에 승인 기록을 반려로 위조
    lines[rev_idx] = json.dumps(d, ensure_ascii=False)
    tampered = AuditLog.load_jsonl("\n".join(lines))
    tv = tampered.verify()
    print(f"변조본 검증: {'✅ OK(문제!)' if tv.ok else '❌ FAIL(변조 탐지 성공)'} — {tv.problems[:2]}")

    out = ROOT / "docs" / "reports" / "audit_6_30.jsonl"
    log.write_jsonl(out)
    print(f"\n생성됨: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
