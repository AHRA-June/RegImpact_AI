"""Impact Matrix 대표 고객 세그먼트(페르소나).

Impact Matrix의 각 행 = "이 규제가 이 유형의 고객에게 어떤 영향을 주는가"다.
페르소나는 룰엔진 입력(MortgageApplication)의 '고정된 프로필'이며, 지역·시점만
바꿔 before/after 두 시점으로 평가한다(matrix.build_impact_matrix).

LOCKED §4: 페르소나는 '입력 프로필'일 뿐, LTV 값은 룰엔진(확정 명세)이 정한다.
여기서 값을 하드코딩하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..models import LoanPurpose, MortgageApplication


@dataclass(frozen=True)
class Persona:
    """Impact Matrix 한 행의 고객 프로필. flags 조합만 다르다."""
    persona_id: str
    label: str
    house_count: int = 0
    disposal_condition_flag: bool = False
    first_home_buyer: bool = False
    real_demand_flag: bool = False
    loan_purpose: LoanPurpose = LoanPurpose.HOME_PURCHASE

    def application(self, region_code: str, evaluation_date: date) -> MortgageApplication:
        """이 페르소나를 특정 지역·시점의 룰엔진 입력으로 변환한다."""
        return MortgageApplication(
            region_code=region_code,
            evaluation_date=evaluation_date,
            house_count=self.house_count,
            disposal_condition_flag=self.disposal_condition_flag,
            first_home_buyer=self.first_home_buyer,
            real_demand_flag=self.real_demand_flag,
            loan_purpose=self.loan_purpose,
            customer_id=self.persona_id,
        )


# 6·30 시나리오 대표 세그먼트 (Walking Skeleton 앵커 행).
# 무주택 기준 예외 계층 + 유주택/다주택(escalation 노출)까지 커버.
SIX_THIRTY_PERSONAS: list[Persona] = [
    Persona("P-NOHOME-GENERAL", "무주택 일반", house_count=0),
    Persona("P-FIRST-HOME", "생애최초", house_count=0, first_home_buyer=True),
    Persona("P-REAL-DEMAND", "서민·실수요자", house_count=0, real_demand_flag=True),
    Persona("P-OWNER-DISPOSAL", "처분조건부 1주택", house_count=1, disposal_condition_flag=True),
    Persona("P-OWNER-1", "비처분 1주택", house_count=1),
    Persona("P-MULTI", "다주택", house_count=2),
]
