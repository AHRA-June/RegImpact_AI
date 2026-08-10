"""경과규정(grandfathering) 판정 (docs/05_RULE_SPEC.md §F).

확정 사실(사람 확정, LOCKED §4):
- 경계 = 2026-06-30 까지 (<=, 날짜 단위, 자정 포함)
- G1 전산 접수 완료 / G2 계약+계약금(일부납부도 증빙이면 인정) / G3 토허제 신청접수
- 하나라도 만족 → 종전규정 적용
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .models import MortgageApplication, ReasonCode

CUTOFF = date(2026, 6, 30)   # 규제 효력 발생일 전일


def is_grandfathered(app: MortgageApplication) -> tuple[bool, Optional[ReasonCode]]:
    """경과규정 해당 여부와 근거 코드. 미해당이면 (False, None)."""
    # G1. 금융회사 전산 접수 완료
    if app.application_accepted_at is not None and app.application_accepted_at <= CUTOFF:
        return True, ReasonCode.GRANDFATHERED_ACCEPTED_OR_CONTRACT

    # G2. 매매계약 체결 + 계약금 납부 증명 (일부납부도 존재하면 인정)
    if (
        app.contract_signed_at is not None
        and app.contract_signed_at <= CUTOFF
        and app.downpayment_paid_at is not None
    ):
        return True, ReasonCode.GRANDFATHERED_ACCEPTED_OR_CONTRACT

    # G3. 토지거래허가 대상 주택: 허가 신청 접수 <= 6.30 → 이후 계약해도 종전규정
    if (
        app.land_permit_target
        and app.land_permit_applied_at is not None
        and app.land_permit_applied_at <= CUTOFF
    ):
        return True, ReasonCode.GRANDFATHERED_LAND_PERMIT

    return False, None


def is_owner(app: MortgageApplication) -> bool:
    """유주택자(무주택·처분조건부 1주택이 아닌 자). 다주택 포함."""
    if app.house_count >= 2:
        return True
    if app.house_count >= 1 and not app.disposal_condition_flag:
        return True
    return False
