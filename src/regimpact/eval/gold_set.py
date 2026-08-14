"""Gold Set 로더 + 엔진 회귀 + 누수 방지 규율 (브리프 §11~12).

각 문항(GoldItem)은 브리프 §11 스키마를 따른다:
    입력 / 골드 정답 / 근거 문서·위치 / 카테고리 / human escalation 기대 / 정책 버전 / rule_id.

정답(expected)은 tc_generator.oracle(독립 명세 재구현)에서 유도하고 freeze한다. rule_engine 은
이 골드에 대해 **채점 대상**이며, 오라클과 독립 코드 경로이므로 회귀가 tautology가 되지 않는다.

누수 방지(§12): LOCKED / CHALLENGE 는 sealed. `load_split` 은 unlock=True 없이는 열지 않는다.
개발 중 상시 회귀는 DEV 만 사용한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from ..models import MortgageApplication
from ..rule_engine import evaluate

GOLD_DIR = Path(__file__).resolve().parents[3] / "docs" / "eval" / "gold_set"
SPLITS = ("dev", "locked", "challenge")
SEALED_SPLITS = frozenset({"locked", "challenge"})

_DATE_FIELDS = (
    "evaluation_date",
    "application_accepted_at",
    "contract_signed_at",
    "downpayment_paid_at",
    "land_permit_applied_at",
)


@dataclass(frozen=True)
class GoldItem:
    """골드 평가셋 한 문항."""
    id: str
    category: str
    split: str
    input: dict[str, Any]                 # MortgageApplication kwargs (날짜는 ISO 문자열)
    expected: dict[str, Any]              # status·max_ltv·applicable_rule_id·grandfathering_applied·must_include_reasons
    expected_escalation: bool
    policy_version: str
    rule_id: str
    source_doc_id: str
    source_note: str

    @classmethod
    def from_dict(cls, d: dict) -> "GoldItem":
        return cls(
            id=d["id"], category=d["category"], split=d["split"],
            input=d["input"], expected=d["expected"],
            expected_escalation=d["expected_escalation"],
            policy_version=d["policy_version"], rule_id=d["rule_id"],
            source_doc_id=d["source_doc_id"], source_note=d["source_note"],
        )

    def application(self) -> MortgageApplication:
        """입력 dict → MortgageApplication (ISO 날짜 문자열 → date)."""
        kwargs = dict(self.input)
        for f in _DATE_FIELDS:
            v = kwargs.get(f)
            if isinstance(v, str):
                kwargs[f] = date.fromisoformat(v)
        return MortgageApplication(**kwargs)


def load_split(name: str, unlock: bool = False) -> list[GoldItem]:
    """split 파일을 로드한다.

    LOCKED / CHALLENGE 는 sealed — unlock=True 없이 열면 RuntimeError(누수 방지 §12).
    개발 중 상시 회귀는 load_split("dev")만 쓴다.
    """
    if name not in SPLITS:
        raise ValueError(f"알 수 없는 split: {name} (가능: {SPLITS})")
    if name in SEALED_SPLITS and not unlock:
        raise RuntimeError(
            f"'{name}' 은 sealed 평가셋이다(브리프 §12 누수 방지). 코어 완성 후 최종 1회 실행 시에만 "
            f"unlock=True 로 개봉하라. 개발 중 튜닝·상시 회귀는 DEV 만 사용한다."
        )
    path = GOLD_DIR / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [GoldItem.from_dict(x) for x in data["items"]]


def load_manifest() -> dict:
    return json.loads((GOLD_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 엔진 회귀 (엔진 출력 vs 골드 정답)
# ---------------------------------------------------------------------------
@dataclass
class ItemResult:
    item: GoldItem
    passed: bool
    mismatches: tuple[str, ...]


@dataclass
class GoldEvalReport:
    split: str
    results: list[ItemResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 1.0

    def failures(self) -> list[ItemResult]:
        return [r for r in self.results if not r.passed]

    def pass_rate_by_category(self) -> dict[str, tuple[int, int, float]]:
        out: dict[str, list[int]] = {}
        for r in self.results:
            b = out.setdefault(r.item.category, [0, 0])
            b[1] += 1
            if r.passed:
                b[0] += 1
        return {c: (p, t, (p / t if t else 1.0)) for c, (p, t) in out.items()}


def _check(item: GoldItem) -> ItemResult:
    d = evaluate(item.application())
    exp = item.expected
    mm: list[str] = []
    if d.status.value != exp["status"]:
        mm.append(f"status {d.status.value}≠{exp['status']}")
    if d.max_ltv != exp.get("max_ltv"):
        mm.append(f"max_ltv {d.max_ltv}≠{exp.get('max_ltv')}")
    exp_rule = exp.get("applicable_rule_id")
    if exp_rule is not None and d.applicable_rule_id != exp_rule:
        mm.append(f"rule_id {d.applicable_rule_id}≠{exp_rule}")
    if d.grandfathering_applied != exp.get("grandfathering_applied", False):
        mm.append(f"gf {d.grandfathering_applied}≠{exp.get('grandfathering_applied', False)}")
    for rc in exp.get("must_include_reasons", []):
        if rc not in d.reason_codes:
            mm.append(f"reason 누락:{rc}")
    escalated = d.status.value == "NEEDS_HUMAN_REVIEW"
    if escalated != item.expected_escalation:
        mm.append(f"escalation {escalated}≠{item.expected_escalation}")
    return ItemResult(item=item, passed=not mm, mismatches=tuple(mm))


def evaluate_items(items: list[GoldItem], split: str = "?") -> GoldEvalReport:
    """골드 문항들을 엔진에 넣어 정답과 대조한다."""
    return GoldEvalReport(split=split, results=[_check(it) for it in items])


def run_gold_regression(split: str = "dev", unlock: bool = False) -> GoldEvalReport:
    """지정 split에 대해 엔진 회귀를 실행한다. 기본 DEV(상시 안전)."""
    return evaluate_items(load_split(split, unlock=unlock), split=split)


def format_report(report: GoldEvalReport) -> str:
    L = [f"■ Gold Set 회귀 [{report.split}] — Pass Rate {report.pass_rate:.0%} "
         f"({report.passed}/{report.total})", "-" * 56]
    for cat, (p, t, r) in sorted(report.pass_rate_by_category().items()):
        L.append(f"  {cat:<16} {p}/{t}  ({r:.0%})")
    for f in report.failures():
        L.append(f"  ✗ {f.item.id}: {', '.join(f.mismatches)}")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# 최종 평가 (Phase 3) — LOCKED/CHALLENGE 최초·최종 개봉
# ---------------------------------------------------------------------------
FINAL_EVAL_PATH = GOLD_DIR / "FINAL_EVAL.json"

_FINAL_NOTE = (
    "LOCKED/CHALLENGE 최초·최종 개봉(브리프 §12 Phase 3). 이 결과가 공식 최종 성능이다. "
    "이후 엔진/명세를 바꿔도 동일 세트로 재튜닝·재보고하지 않는다 — 재개발 시 새 평가셋 버전이 필요하다."
)


def _split_result(split: str, unlock: bool) -> dict:
    r = run_gold_regression(split, unlock=unlock)
    return {
        "passed": r.passed, "total": r.total, "pass_rate": r.pass_rate,
        "by_category": {c: list(v) for c, v in r.pass_rate_by_category().items()},
        "failures": [{"id": f.item.id, "mismatches": list(f.mismatches)} for f in r.failures()],
    }


def run_final_evaluation(opened_date: str, save: bool = True) -> dict:
    """3개 split(DEV·LOCKED·CHALLENGE) 최종 실행. sealed는 여기서 unlock한다(공식 개봉).

    opened_date 는 개봉 일자(예: '2026-08-14') — 결정론 보장 위해 호출자가 명시한다.
    """
    splits = {
        "dev": _split_result("dev", unlock=False),
        "locked": _split_result("locked", unlock=True),
        "challenge": _split_result("challenge", unlock=True),
    }
    passed = sum(s["passed"] for s in splits.values())
    total = sum(s["total"] for s in splits.values())
    manifest = load_manifest()
    record = {
        "_meta": {
            "note": _FINAL_NOTE,
            "opened_date": opened_date,
            "gold_version": manifest["version"],
            "engine": "rule_engine (deterministic §H)",
            "expected_source": manifest["expected_source"],
        },
        "splits": splits,
        "overall": {"passed": passed, "total": total,
                    "pass_rate": (passed / total if total else 1.0)},
    }
    if save:
        FINAL_EVAL_PATH.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def load_final_eval() -> dict | None:
    """최종 평가 기록을 로드한다. 없으면 None(아직 미개봉 → sealed로 표시)."""
    if not FINAL_EVAL_PATH.exists():
        return None
    return json.loads(FINAL_EVAL_PATH.read_text(encoding="utf-8"))
