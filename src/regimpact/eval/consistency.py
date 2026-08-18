"""골드 ⟷ 확정 명세 정합성 검사.

골드셋과 룰엔진은 서로 다른 경로로 만들어진다 — 골드는 공문 원문에서, 룰엔진은 사람이 확정한
명세(05_RULE_SPEC)에서. 둘이 어긋나면 어느 쪽이 틀렸든 그 위의 모든 수치가 의미를 잃는데,
어긋남은 조용하다: 골드 채점도 통과하고 룰 회귀도 통과한다.

**왜 이렇게 좁은가.** 처음에는 "명세 값이 언급된 문맥에 나타나야 한다"는 넓은 규칙으로 만들었고
115문항에서 13건을 잡았는데 **10건이 오탐**이었다(유주택 0%를 다루는 문항에 40%가 없다고 잡는 식).
오탐이 압도적인 검사는 무시당하므로 규칙이 아니라 검사를 버렸다. 대신 **실제로 관측된 결함
유형 두 가지**만 높은 정밀도로 잡는다.

두 결함 모두 원인이 같다: FAQ Q2 표가 HWP→텍스트 변환에서 **LTV 열과 DTI 열이 뭉개진다.**
평탄화된 텍스트만 보면 "일반 차주 60%"가 LTV로 읽히지만, 확정 명세(사용자가 원본 이미지로 확정)에서
그 60%는 DTI다. 원문 텍스트만 보고 작성하면 반드시 재발한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import rule_engine as R
from .schema import GoldItem

# "원문에 답이 없다"고 말하는 문항은 값을 주장하는 것이 아니다
_HEDGES = ("답이 없", "단정할 수 없", "확인할 수 없", "말하지 않")
# "수도권 外" 값을 인용하며 전용 불가라고 말하는 문항도 주장이 아니다
_OUT_OF_CAPITAL = ("수도권 외", "수도권 外", "수도권에 한정")


def _asserts_value(text: str) -> bool:
    return not any(h in text for h in _HEDGES) and not any(o in text for o in _OUT_OF_CAPITAL)


@dataclass
class ConsistencyReport:
    conflicts: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not self.conflicts

    def summary(self) -> str:
        return (f"{self.checked}문항 대조 — "
                f"{'✅ 명세와 정합' if self.ok else f'❌ 충돌 {len(self.conflicts)}건'}")


def _check_baseline(item: GoldItem, text: str, pcts: set[str]) -> str | None:
    """결함 유형 ①: 非규제(수도권) 기준선 LTV를 명세와 다른 값으로 주장."""
    if not re.search(r"[非비]규제", text):
        return None
    if not re.search(r"(수도권\)|수도권에서|수도권 지역|이전|기준선|였)", text):
        return None
    expected = f"{R.LTV_BASELINE:.0%}"
    if expected in pcts or not pcts:
        return None
    return (f"[{item.id}] 非규제(수도권) 기준선을 {sorted(pcts)}로 주장 — 확정 명세는 {expected}. "
            f"FAQ Q2 표의 DTI 열을 LTV로 읽었을 가능성")


def _check_regulated_by_type(item: GoldItem, text: str, pcts: set[str]) -> str | None:
    """결함 유형 ②: 규제지역 LTV가 지역 종류별로 다르다고 주장.

    확정 명세에서 LTV는 투기과열·조정 모두 동일(40%)이고, 종류별로 갈리는 것은 **DTI**다
    (투기과열 40 / 조정 50). 두 지역 종류와 서로 다른 값이 함께 나오면 그 혼동 신호다.
    """
    if not ("투기과열" in text and "조정대상" in text):
        return None
    expected = f"{R.LTV_REGULATED_STANDARD:.0%}"
    others = pcts - {expected}
    if not others:
        return None
    return (f"[{item.id}] 규제지역 LTV가 지역 종류별로 다르다고 주장({sorted(pcts)}) — "
            f"확정 명세는 투기과열·조정 모두 {expected}이고, 종류별로 갈리는 것은 DTI다")


def check_gold_against_spec(items: list[GoldItem]) -> ConsistencyReport:
    """골드 문항이 확정 명세의 LTV 값과 모순되는지 본다 (LTV를 명시적으로 말하는 문항만)."""
    rep = ConsistencyReport(checked=len(items))
    for item in items:
        text = f"{item.question} {item.gold_answer}"
        if "ltv" not in text.lower() and "담보인정비율" not in text:
            continue
        if not _asserts_value(text):
            continue
        pcts = set(re.findall(r"\d{1,3}%", text))
        for check in (_check_baseline, _check_regulated_by_type):
            msg = check(item, text, pcts)
            if msg:
                rep.conflicts.append(msg)
                break
    return rep
