"""골드셋 로더 + **누수 방지 봉인 장치** (브리프 §12).

브리프 §12의 규율은 문서에만 적으면 지켜지지 않는다. 개발 중 무심코 LOCKED/CHALLENGE를
열어보는 것이 누수의 실제 경로이므로, **코드가 거부하게** 만든다.

    load_split(Split.DEV)                    # 자유롭게 사용
    load_split(Split.LOCKED)                 # → SealedSplitError
    load_split(Split.LOCKED, unseal_reason="코어 완성 후 최종 성능평가 1회 (2026-XX-XX)")
                                             # → 열리고, 접근 기록이 남는다

봉인을 푸는 것 자체는 막지 않는다(언젠가는 열어야 하므로). 대신 **이유를 요구하고 기록을
남긴다** — 사고를 막는 것이 아니라 사고가 조용히 지나가지 못하게 하는 통제다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from .schema import HIGH_RISK_CATEGORIES as HIGH_RISK
from .schema import Category, GoldItem, Split, ValidationReport

GOLD_DIR = Path(__file__).resolve().parents[3] / "docs" / "eval" / "gold"
ACCESS_LOG = GOLD_DIR / "SEAL_ACCESS_LOG.md"

SEALED = frozenset({Split.LOCKED, Split.CHALLENGE})
_FILES = {Split.DEV: "dev.json", Split.LOCKED: "locked.json", Split.CHALLENGE: "challenge.json"}

MIN_REASON_CHARS = 20   # "test" 같은 형식적 사유로 봉인이 열리지 않게


class SealedSplitError(RuntimeError):
    """봉인된 split을 사유 없이 열려고 했을 때."""


def split_path(split: Split, gold_dir: Optional[Path] = None) -> Path:
    return Path(gold_dir or GOLD_DIR) / _FILES[split]


def load_split(
    split: Split,
    *,
    unseal_reason: Optional[str] = None,
    gold_dir: Optional[Path] = None,
    log_path: Optional[Path] = None,
) -> list[GoldItem]:
    """split의 문항을 읽는다. LOCKED/CHALLENGE는 `unseal_reason` 없이는 열리지 않는다."""
    if split in SEALED:
        if not unseal_reason or len(unseal_reason.strip()) < MIN_REASON_CHARS:
            raise SealedSplitError(
                f"{split.value}는 봉인된 셋입니다 (브리프 §12). 개발 중 튜닝에 쓰지 마세요.\n"
                f"정당한 사유가 있다면 unseal_reason=... 로 최소 {MIN_REASON_CHARS}자 이상 "
                "구체적으로 남기세요. 접근은 SEAL_ACCESS_LOG.md에 기록됩니다."
            )
        _record_access(split, unseal_reason.strip(), log_path)

    path = split_path(split, gold_dir)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [GoldItem.from_dict(d) for d in raw["items"]]


def split_stats(split: Split, gold_dir: Optional[Path] = None) -> dict:
    """**정답을 보지 않고** split의 구성만 본다 — 봉인을 열지 않는다.

    커버리지 점검·리포트 같은 일상 작업이 봉인 해제를 요구하면, 사람은 결국 습관적으로
    봉인을 열게 된다. 통제는 정당한 작업을 방해하지 않아야 지켜진다.
    문항 수·카테고리 분포·high-risk 비중만 돌려주고 question/gold_answer/citations는 넣지 않는다.
    """
    path = split_path(split, gold_dir)
    if not path.exists():
        return {"split": split.value, "count": 0, "categories": {}, "high_risk_ratio": 0.0}
    raw = json.loads(path.read_text(encoding="utf-8"))
    cats: dict[str, int] = {}
    high = 0
    for d in raw["items"]:
        cats[d["category"]] = cats.get(d["category"], 0) + 1
        if Category(d["category"]) in HIGH_RISK:
            high += 1
    n = len(raw["items"])
    return {
        "split": split.value,
        "count": n,
        "categories": cats,
        "high_risk_ratio": high / n if n else 0.0,
        "authored_by": sorted({d.get("authored_by", "ai_draft") for d in raw["items"]}),
    }


def _record_access(split: Split, reason: str, log_path: Optional[Path]) -> None:
    """봉인 해제를 append-only로 기록한다. 지우면 diff에 남는다.

    같은 날 · 같은 split · 같은 사유가 반복되면 새 행을 쌓는 대신 **횟수만 올린다**.
    테스트 스위트가 매 실행마다 정합성 검사로 LOCKED/CHALLENGE 를 열기 때문에, 행을
    그대로 쌓으면 수십 행이 금방 붙어 정작 사람이 튜닝 목적으로 연 기록이 파묻힌다.
    감사로그의 값어치는 이상한 접근이 **눈에 띄는 것**에 있으므로, 반복은 접고 종류는 남긴다.
    (횟수는 유지되므로 '몇 번 열었나'는 그대로 추적된다.)
    """
    path = Path(log_path or ACCESS_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "# 봉인 해제 기록 (append-only)\n\n"
            "> LOCKED / CHALLENGE 셋을 연 이력. 브리프 §12 규율의 증빙이다.\n"
            "> 이 파일이 비어 있는 동안에는 두 셋이 튜닝에 쓰이지 않았다는 뜻이다.\n"
            "> 같은 날·같은 split·같은 사유의 반복 접근은 마지막 행의 횟수(×N)로 접힌다.\n\n"
            "| 날짜 | split | 사유 | 횟수 |\n|---|---|---|---|\n",
            encoding="utf-8",
        )

    today = date.today().isoformat()
    prefix = f"| {today} | {split.value} | {reason} |"
    lines = path.read_text(encoding="utf-8").splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if not lines[i].startswith(f"| {today} |"):
            break                                # 오늘 기록 구간을 벗어남
        if lines[i].startswith(prefix):          # 오늘 같은 사유가 이미 있음 → 횟수만 증가
            tail = lines[i][len(prefix):].strip(" |")
            count = int(tail[1:]) if tail.startswith("×") else 1
            lines[i] = f"{prefix} ×{count + 1} |"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return

    with path.open("a", encoding="utf-8") as f:
        f.write(f"{prefix} ×1 |\n")


def save_split(items: list[GoldItem], split: Split, gold_dir: Optional[Path] = None) -> Path:
    """문항을 split 파일로 쓴다(작성 도구용). 저장은 봉인과 무관하다."""
    path = split_path(split, gold_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_note": (
            f"{split.value} split — docs/00_BRIEF.md §11/§12. "
            "authored_by=ai_draft는 사람 확정 대기(🤖), human_confirmed는 확정(✅)."
        ),
        "split": split.value,
        "count": len(items),
        "items": [i.to_dict() for i in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def category_counts(items: list[GoldItem]) -> dict[str, int]:
    counts = {c.value: 0 for c in Category}
    for i in items:
        counts[i.category.value] += 1
    return {k: v for k, v in counts.items() if v}


def coverage_report(items: list[GoldItem]) -> ValidationReport:
    """건수가 아니라 **실패모드 카테고리 커버리지**를 본다 (metrics_spec §0-A)."""
    rep = ValidationReport(checked=len(items))
    missing = [c.value for c in Category if not any(i.category == c for i in items)]
    if missing:
        rep.warnings.append(f"미커버 카테고리: {', '.join(missing)}")
    if items:
        high = sum(i.is_high_risk for i in items) / len(items)
        if high < 0.4:
            rep.warnings.append(
                f"high-risk 카테고리 비중 {high:.0%} — 브리프 §11은 예외·경과규정·시행일·충돌 가중을 요구"
            )
    return rep
