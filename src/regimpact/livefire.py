"""라이브파이어 하네스 (Live Fire) — 브리프 §19.

목적:
  **실제 신규 부동산·가계대출 대책이 발표되면 그날 전 파이프라인을 돌려**, 사후 조작이
  불가능하도록 증거 패키지(원문 해시 + 분석 timestamp + git commit + 시스템 버전 + 산출물)를
  저장소에 남긴다. "시연이 아니라 실적"을 남기는 것이 핵심(브리프 §19 핵심 메시지).

이 모듈이 하는 일 = **턴키 러너 + 증거 매니페스트**:
  공문(스냅샷·해시) → 추출 → 정규화 → Impact Matrix → 여력 → 민감도 → 룰 변경안 →
  Assurance(grounding/gold/rule-regression) → HTML 리포트 → **EvidenceManifest(무결성 고정).**

⚠️ **정직성(라이브파이어의 생명):**
  - `mode="LIVE"` 는 **실제 신규 정책을 발표 당일 처리**한 실적일 때만 쓴다.
  - `mode="REHEARSAL"` 은 **예행연습**이다. 6·30 같은 과거·골드셋 수록 사건으로 하네스가
    턴키로 도는지 검증할 뿐, **실제 라이브파이어가 아니다.** 매니페스트·리포트에 그대로 표기한다.
  - 매니페스트의 `system_commit` 은 **분석을 산출한 코드 버전(생성 시 HEAD)**이다. 이 매니페스트
    자체는 그 다음 커밋으로 저장되므로, commit 은 보통 저장 커밋의 부모를 가리킨다(정상).
  - 브리프 §19: "복잡한 사후 조작 불가 시스템을 별도 구현하지 않는다." 해시+timestamp+commit 로 충분.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from .extractor import check_citation_grounding, score_against_gold
from .impact import (
    build_response_table,
    compute_exposure,
    impact_from_extraction,
    sensitivity_bands,
)
from .report import render_report
from .rule_proposal import build_proposal
from .tc_generator import generate_portfolio, run_regression

SYSTEM_NAME = "regimpact"
SYSTEM_VERSION = "0.1.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_head() -> str:
    """현재 HEAD 커밋(분석을 산출한 코드 버전). 실패 시 '(unknown)'."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "(unknown)"
    except Exception:
        return "(unknown)"


@dataclass
class SourceRef:
    doc_id: str
    filename: str
    sha256: str
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id, "filename": self.filename,
                "sha256": self.sha256, "bytes": self.bytes}


@dataclass
class EvidenceManifest:
    """라이브파이어 증거 매니페스트 (사후 조작 불가 고정점)."""
    kind: str
    mode: str                         # "LIVE" | "REHEARSAL"
    label: str
    policy_id: str
    analysis_timestamp: str
    system_name: str
    system_version: str
    system_commit: str
    sources: list[SourceRef] = field(default_factory=list)
    extraction_sha256: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    assurance: dict[str, Any] = field(default_factory=dict)
    headline: dict[str, Any] = field(default_factory=dict)
    honesty: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "mode": self.mode,
            "label": self.label,
            "policy_id": self.policy_id,
            "analysis_timestamp": self.analysis_timestamp,
            "system_name": self.system_name,
            "system_version": self.system_version,
            "system_commit": self.system_commit,
            "sources": [s.to_dict() for s in self.sources],
            "extraction_sha256": self.extraction_sha256,
            "artifacts": self.artifacts,
            "assurance": self.assurance,
            "headline": self.headline,
            "honesty": self.honesty,
        }


def _honesty_notes(mode: str, has_gold: bool) -> list[str]:
    notes: list[str] = []
    if mode == "REHEARSAL":
        notes.append("이것은 예행연습(REHEARSAL)이다 — 6·30 등 과거·골드셋 수록 사건으로 "
                     "하네스가 턴키로 도는지 검증할 뿐, 실제 라이브파이어(발표 당일 신규 처리)가 아니다.")
    else:
        notes.append("LIVE — 실제 신규 정책을 발표 후 처리한 실적. 원문 해시·timestamp·commit 로 무결성 고정.")
    notes.append("LTV 판정은 사람이 확정한 결정적 룰엔진 출력이다(AI가 규칙을 만들지 않음, LOCKED §4). "
                 "추출·변경요약만 AI 초안이며 인용으로 grounding 검증한다.")
    notes.append("여력 금액·민감도는 문서화된 가정(담보가격 분포·비중) 기반이며 실행액이 아니다. "
                 "가격대별 최대한도 상한(6/4/2억) 미적용(상한 성격).")
    if not has_gold:
        notes.append("골드셋 미비: 신규 정책은 아직 골드 정답지가 없어 Change/Exception recall 은 산정하지 않는다"
                     "(grounding·rule-regression 등 정답 불필요 지표만 보고).")
    notes.append("system_commit 은 분석 산출 시 HEAD(이 매니페스트는 다음 커밋으로 저장되므로 보통 부모 커밋).")
    return notes


def run_livefire(
    extraction: Any,
    extraction_dict: dict[str, Any],
    sources: dict[str, str],
    source_files: list[tuple[str, Path]],
    out_dir: Path,
    *,
    mode: str = "LIVE",
    label: str = "",
    gold: Optional[dict] = None,
    generated_on: Optional[date] = None,
    analysis_timestamp: Optional[str] = None,
    system_commit: Optional[str] = None,
    report_title: str = "규제 변경 영향분석 리포트",
) -> EvidenceManifest:
    """라이브파이어 1회 실행 — 파이프라인 + 증거 패키지를 out_dir 에 남긴다.

    - extraction: 파이프라인 입력(추출 객체). 신규 정책이면 LLM 추출 결과, 리허설이면 저장 추출.
    - extraction_dict: 그 추출의 원본 dict(해시·아티팩트 저장용).
    - sources: doc_id→원문 텍스트(grounding 용). source_files: (doc_id, 원본경로)(해시용).
    - gold: 이 정책의 골드 정답지(신규면 None → recall 미산정).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = analysis_timestamp or datetime.now().astimezone().isoformat(timespec="seconds")
    commit = system_commit or git_head()

    # --- 원문 스냅샷 해시(무결성 고정) ---
    src_refs = [
        SourceRef(doc_id=doc_id, filename=p.name, sha256=sha256_file(p), bytes=p.stat().st_size)
        for doc_id, p in source_files
    ]

    # --- 파이프라인 ---
    policy_impact = impact_from_extraction(extraction)
    matrix = policy_impact.matrix
    exposure = compute_exposure([r.segment for r in matrix.rows])
    sens = sensitivity_bands(build_response_table(), n=3000, seed=42)
    proposal = build_proposal(extraction, generated_on=generated_on)
    grounding = check_citation_grounding(extraction, sources)
    gold_report = score_against_gold(extraction, gold) if gold is not None else None
    regression = run_regression(generate_portfolio())

    # --- Assurance 요약 ---
    assurance: dict[str, Any] = {
        "citation_correctness": round(grounding.citation_correctness, 4),
        "unsupported_claim_rate": round(grounding.unsupported_claim_rate, 4),
        "citations": f"{grounding.grounded}/{grounding.total}",
        "rule_regression": f"{regression.passed}/{regression.total}",
        "rule_regression_pass_rate": round(regression.pass_rate, 4),
    }
    if gold_report is not None:
        assurance.update({
            "change_completeness": round(gold_report.change_completeness, 4),
            "exception_recall": round(gold_report.exception_recall, 4),
            "effective_date_correct": bool(gold_report.effective_date_correct),
            "regions_correct": bool(gold_report.regions_correct),
        })

    # --- 헤드라인 ---
    counts = matrix.count_by_direction()
    ds = matrix.direction_weight_share()
    p5, _p50, p95 = sens.bands["exposure_pct_reduction"]
    pc = proposal.counts()
    headline: dict[str, Any] = {
        "regions": policy_impact.regions,
        "unmapped_regions": policy_impact.unmapped_regions,
        "rows": len(matrix.rows),
        "direction_counts": counts,
        "direction_weight_share": {k: round(v, 4) for k, v in ds.items()},
        "review_weight_share": round(matrix.review_weight_share(), 4),
        "exposure_pct_reduction": round(exposure.pct_reduction, 4) if exposure.pct_reduction else None,
        "exposure_per_unit_delta_eok": round(exposure.per_unit_delta(), 4) if exposure.per_unit_delta() else None,
        "exposure_undetermined_share": round(exposure.undetermined_share, 4),
        "sensitivity_pct_reduction_band": [round(p5, 4), round(p95, 4)],
        "sensitivity_robustness": {k: round(v, 4) for k, v in sens.robustness.items()},
        "proposal": {"mapped_consistent": pc["MAPPED_CONSISTENT"], "out_of_scope": pc["OUT_OF_SCOPE"],
                     "review": pc["MAPPED_DIVERGENT"] + pc["NEEDS_REVIEW"],
                     "approval_status": proposal.approval_status},
    }

    # --- 아티팩트 저장 ---
    html = render_report(
        policy_impact, extraction=extraction, grounding=grounding, gold=gold_report,
        proposal=proposal, exposure=exposure, sensitivity=sens,
        generated_on=generated_on, title=report_title,
    )
    (out_dir / "report.html").write_text(html, encoding="utf-8")
    (out_dir / "extraction.json").write_text(
        json.dumps(extraction_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "impact_summary.json").write_text(
        json.dumps(headline, ensure_ascii=False, indent=2), encoding="utf-8")

    extraction_hash = sha256_text(json.dumps(extraction_dict, ensure_ascii=False, sort_keys=True))

    manifest = EvidenceManifest(
        kind="livefire-evidence",
        mode=mode,
        label=label,
        policy_id=getattr(extraction, "policy_id", "(unknown)"),
        analysis_timestamp=ts,
        system_name=SYSTEM_NAME,
        system_version=SYSTEM_VERSION,
        system_commit=commit,
        sources=src_refs,
        extraction_sha256=extraction_hash,
        artifacts={"report": "report.html", "extraction": "extraction.json",
                   "impact_summary": "impact_summary.json", "record": "README.md"},
        assurance=assurance,
        headline=headline,
        honesty=_honesty_notes(mode, gold is not None),
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "README.md").write_text(render_evidence_record(manifest), encoding="utf-8")
    return manifest


def render_evidence_record(m: EvidenceManifest) -> str:
    """증거 패키지의 사람이 읽는 기록(브리프 §19 표기 양식)."""
    tag = "Live Fire" if m.mode == "LIVE" else "Live Fire REHEARSAL(예행연습)"
    L: list[str] = []
    L.append(f"# {tag} — {m.label or m.policy_id}")
    L.append("")
    if m.mode != "LIVE":
        L.append("> ⚠️ **예행연습이다. 실제 라이브파이어(신규 정책 발표 당일 처리)가 아니다.** "
                 "과거·골드셋 수록 사건으로 하네스가 턴키로 도는지 검증한 기록.")
        L.append("")
    L.append("## 증거 (evidence package)")
    L.append("")
    L.append(f"- **정책:** `{m.policy_id}`")
    L.append(f"- **분석 시각:** {m.analysis_timestamp}")
    L.append(f"- **시스템:** {m.system_name} {m.system_version}")
    L.append(f"- **시스템 커밋:** `{m.system_commit}`")
    L.append("- **원문 해시(sha256):**")
    for s in m.sources:
        L.append(f"  - `{s.doc_id}` — {s.filename} · `{s.sha256}` ({s.bytes:,} bytes)")
    L.append(f"- **추출 해시:** `{m.extraction_sha256}`")
    L.append(f"- **산출물:** " + ", ".join(f"`{v}`" for v in m.artifacts.values()))
    L.append("")
    L.append("## Assurance")
    L.append("")
    a = m.assurance
    L.append(f"- Citation 정확도 {a.get('citation_correctness', 0):.0%} ({a.get('citations','-')}) · "
             f"환각률 {a.get('unsupported_claim_rate', 0):.0%}")
    if "exception_recall" in a:
        L.append(f"- 변경 완전성 {a['change_completeness']:.0%} · 예외 재현율 {a['exception_recall']:.0%} · "
                 f"시행일 {'OK' if a['effective_date_correct'] else 'MISS'} · "
                 f"지역 {'OK' if a['regions_correct'] else 'MISS'}")
    else:
        L.append("- 변경 완전성/예외 재현율: 골드셋 미비(신규 정책) — 미산정")
    L.append(f"- 룰-회귀 {a.get('rule_regression','-')} ({a.get('rule_regression_pass_rate',0):.0%})")
    L.append("")
    L.append("## 헤드라인")
    L.append("")
    h = m.headline
    L.append(f"- 대상지역: {', '.join(h.get('regions', [])) or '—'} · 임팩트 {h.get('rows','-')}행")
    dws = h.get("direction_weight_share", {})
    if dws:
        L.append(f"- 방향(비중): 강화 {dws.get('TIGHTENED',0):.0%} · 유지 {dws.get('UNCHANGED',0):.0%} · "
                 f"검토 {dws.get('NEEDS_REVIEW',0):.0%} · 사람검토 {h.get('review_weight_share',0):.0%}")
    if h.get("exposure_pct_reduction") is not None:
        band = h.get("sensitivity_pct_reduction_band", [None, None])
        L.append(f"- 여력 감소율 {h['exposure_pct_reduction']:.1%} "
                 f"(민감도 밴드 [{band[0]:.1%}, {band[1]:.1%}]) · "
                 f"1인당 Δ {h.get('exposure_per_unit_delta_eok', 0):+.2f}억")
    pr = h.get("proposal", {})
    if pr:
        L.append(f"- 룰 변경안: 반영 {pr.get('mapped_consistent',0)} · 코어밖 {pr.get('out_of_scope',0)} · "
                 f"검토 {pr.get('review',0)} · 승인 {pr.get('approval_status','-')}")
    L.append("")
    L.append("## 정직성 고지")
    L.append("")
    for n in m.honesty:
        L.append(f"- {n}")
    L.append("")
    return "\n".join(L)
