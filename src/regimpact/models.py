"""RegImpact AI — 룰엔진 데이터 모델 (입력/출력 스키마).

근거: docs/05_RULE_SPEC.md §A(입력), §B(출력), §D(reason_codes).
LOCKED §4: 규칙 '값·로직'은 사람이 확정한 명세에서 온다. 이 파일은 스키마(인터페이스)다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class LoanPurpose(str, Enum):
    HOME_PURCHASE = "HOME_PURCHASE"      # 주택구입목적 (Core)
    OTHER = "OTHER"                       # 그 외 (Discovery/Out-of-scope)


class RegionStatus(str, Enum):
    REGULATED = "REGULATED"              # 규제지역
    NON_REGULATED = "NON_REGULATED"      # 비규제지역


class RegulatedType(str, Enum):
    SPECULATIVE_OVERHEATED = "SPECULATIVE_OVERHEATED"  # 투기과열지구 (DTI 40%)
    ADJUSTMENT = "ADJUSTMENT"                          # 조정대상지역 (DTI 50%)
    NONE = "NONE"


class EvaluationStatus(str, Enum):
    """판정 결과의 종류. LTV가 결정되면 DECIDED, 아니면 사유별 상태."""
    DECIDED = "DECIDED"                        # max_ltv 확정
    OUT_OF_SCOPE = "OUT_OF_SCOPE"              # 주택구입목적 아님
    DISCOVERY = "DISCOVERY"                    # 정책대출 등 수동 검토 대상
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"  # 사람 검토 필요(모호/기준 부재)


class ReasonCode(str, Enum):
    """판정 근거 라벨 (docs/05_RULE_SPEC.md §D 확정 목록)."""
    LTV_REGULATED_40 = "LTV_REGULATED_40"
    EXCEPTION_FIRST_HOME = "EXCEPTION_FIRST_HOME"
    EXCEPTION_REAL_DEMAND = "EXCEPTION_REAL_DEMAND"
    LTV_OWNER_0 = "LTV_OWNER_0"
    LTV_MULTI_HOME_0 = "LTV_MULTI_HOME_0"
    LTV_BASELINE_70 = "LTV_BASELINE_70"
    GRANDFATHERED_ACCEPTED_OR_CONTRACT = "GRANDFATHERED_ACCEPTED_OR_CONTRACT"
    GRANDFATHERED_LAND_PERMIT = "GRANDFATHERED_LAND_PERMIT"
    OWNER_BASELINE_UNKNOWN = "OWNER_BASELINE_UNKNOWN"
    OUT_OF_SCOPE_PRODUCT = "OUT_OF_SCOPE_PRODUCT"
    DISCOVERY_POLICY_LOAN = "DISCOVERY_POLICY_LOAN"


@dataclass
class MortgageApplication:
    """룰엔진 입력 (docs/05_RULE_SPEC.md §A).

    지역상태는 region_code + evaluation_date로 엔진이 해석한다(regions.resolve_region_status).
    이벤트 날짜는 date 단위(경과규정 경계가 날짜 단위, 자정까지 포함).
    """
    region_code: str
    evaluation_date: date
    house_count: int = 0
    disposal_condition_flag: bool = False     # 처분조건부 1주택 (house_count==1과 함께)
    first_home_buyer: bool = False            # 생애최초 (세대원 전원 무주택 이력)
    real_demand_flag: bool = False            # 서민·실수요자
    policy_mortgage_flag: bool = False        # 정책대출 → Discovery
    loan_purpose: LoanPurpose = LoanPurpose.HOME_PURCHASE

    # 경과규정 관련 이벤트 (nullable)
    application_accepted_at: Optional[date] = None   # 전산 접수 완료 (G1)
    contract_signed_at: Optional[date] = None        # 매매계약 체결 (G2)
    downpayment_paid_at: Optional[date] = None       # 계약금 납부 (G2)
    land_permit_target: bool = False                 # 토지거래허가 대상 물건 (G3)
    land_permit_applied_at: Optional[date] = None    # 토지거래허가 신청 접수일 (G3)

    customer_id: Optional[str] = None                # 추적용(선택)


@dataclass
class LtvDecision:
    """룰엔진 출력 (docs/05_RULE_SPEC.md §B). 코어 판정 = max_ltv."""
    status: EvaluationStatus
    max_ltv: Optional[float] = None
    applicable_rule_id: Optional[str] = None
    grandfathering_applied: bool = False
    reason_codes: list[str] = field(default_factory=list)
    source_policy_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # ReasonCode enum이 섞여 들어와도 문자열로 정규화
        self.reason_codes = [
            rc.value if isinstance(rc, ReasonCode) else str(rc) for rc in self.reason_codes
        ]
