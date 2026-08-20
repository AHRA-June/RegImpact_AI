"""내게 가능한 상품 찾기 — **자격 판정**이지 추천이 아니다.

고객 인터뷰·심사 어필(2026-08-20): "진단에서 끝내지 말고 어떤 상품이 되는지까지."
다만 이 기능은 취향을 예측하는 추천 엔진이 아니다 — **엔진이 이미 판정한 사실**
(규제지역 여부·주택 수·생애최초·서민실수요·경과규정)에서 **요건 충족 여부**를 되짚는다.
그래서 지어낼 여지가 없고, 금소법상 자문·권유가 아니라 정보 제공에 머문다.

세 가지 상태만 말한다:
  ELIGIBLE   원문이 "완화된 LTV 적용" 등으로 명시한 대상에 해당한다
  BLOCKED    엔진이 이미 그 경로를 막았다 (다주택 0% 등) — 상품 이전에 대출이 안 된다
  UNKNOWN    소득·자산·주택가격 등 **이 공문에 없는 요건**이라 판정하지 않는다

⚠️ UNKNOWN 을 ELIGIBLE 로 올리지 않는다. 디딤돌·보금자리론의 소득·자산 요건은 6·30
공문에 없다. 없는 근거로 "가능합니다"라고 말하는 순간 이 제품의 원칙이 무너진다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Status = Literal["ELIGIBLE", "BLOCKED", "UNKNOWN"]

# 원문이 언급한 상품군. figures 는 FAQ 표의 값을 그대로 옮긴 것이 아니라 화면이
# **인용으로** 보여주므로 여기에는 적지 않는다 — 값은 인용 안에 있다.
PRODUCTS = (
    {"id": "FIRST_HOME", "name": "생애최초 주담대", "cite": "_P_RELAXED",
     "gate": "first_home_buyer"},
    {"id": "REAL_DEMAND", "name": "서민·실수요자 주담대", "cite": "_P_RELAXED",
     "gate": "real_demand_flag"},
    {"id": "DIDIMDOL", "name": "디딤돌 대출 (정책모기지)", "cite": "_P_DIDIMDOL",
     "gate": None},
    {"id": "BOGEUMJARI", "name": "보금자리론 (정책모기지)", "cite": "_P_BOGEUM",
     "gate": None},
)


@dataclass(frozen=True)
class ProductVerdict:
    id: str
    name: str
    status: Status
    reason: str
    cite: str


def eligible_products(
    *,
    decision_status: str,
    max_ltv: Optional[float],
    grandfathered: bool,
    first_home_buyer: bool = False,
    real_demand_flag: bool = False,
    house_count: int = 0,
    regulated: bool = False,
) -> list[ProductVerdict]:
    """엔진 판정 결과에서 상품 자격을 되짚는다. 새 도메인 규칙을 만들지 않는다."""
    out: list[ProductVerdict] = []

    # 대출 자체가 막힌 경우 — 상품을 논할 단계가 아니다
    blocked_all = decision_status == "DECIDED" and max_ltv == 0
    review = decision_status not in ("DECIDED",)

    for p in PRODUCTS:
        if blocked_all:
            out.append(ProductVerdict(
                p["id"], p["name"], "BLOCKED",
                "이 조건에서는 신규 주택구입 주담대 자체가 제한돼(LTV 0%) 상품을 따질 단계가 "
                "아니에요." if house_count >= 1 else "이 조건에서는 대출이 제한됩니다.",
                p["cite"]))
            continue
        if review:
            out.append(ProductVerdict(
                p["id"], p["name"], "UNKNOWN",
                "판정에 사람 확인이 필요한 조건이라 상품 자격도 상담으로 확인해야 해요.",
                p["cite"]))
            continue

        gate = p["gate"]
        if gate == "first_home_buyer":
            if first_home_buyer:
                out.append(ProductVerdict(
                    p["id"], p["name"], "ELIGIBLE",
                    "생애최초로 체크하셨고, 원문이 생애최초 주담대를 완화 대상으로 명시합니다."
                    + (" 규제지역이어도 좌동입니다." if regulated else ""),
                    p["cite"]))
            else:
                out.append(ProductVerdict(
                    p["id"], p["name"], "UNKNOWN",
                    "생애최초 여부를 체크하지 않으셨어요. 세대 구성원 모두 주택 소유 이력이 "
                    "없어야 해당합니다.", p["cite"]))
        elif gate == "real_demand_flag":
            if real_demand_flag:
                out.append(ProductVerdict(
                    p["id"], p["name"], "ELIGIBLE",
                    "서민·실수요자 요건으로 체크하셨고, 원문이 완화 대상으로 명시합니다.",
                    p["cite"]))
            else:
                out.append(ProductVerdict(
                    p["id"], p["name"], "UNKNOWN",
                    "소득·주택가격·무주택 요건을 모두 충족해야 해당해요. 위에서 체크해 보세요.",
                    p["cite"]))
        else:
            # 정책모기지 — 확정 명세가 Discovery(수동 검토)로 분리한 경로다.
            # 소득·자산 요건이 6·30 공문에 없으므로 자격을 판정하지 않는다.
            out.append(ProductVerdict(
                p["id"], p["name"], "UNKNOWN",
                "원문에 한도는 나와 있지만 소득·자산 등 신청 자격 요건은 이 공문에 없어요. "
                "해당 여부는 상담으로 확인해야 합니다."
                + (" 경과규정 대상이면 종전 기준이 함께 검토됩니다." if grandfathered else ""),
                p["cite"]))
    return out


def summary(verdicts: list[ProductVerdict]) -> dict:
    return {
        "eligible": [v.id for v in verdicts if v.status == "ELIGIBLE"],
        "blocked": [v.id for v in verdicts if v.status == "BLOCKED"],
        "unknown": [v.id for v in verdicts if v.status == "UNKNOWN"],
    }
