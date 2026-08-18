"""임팩트 매트릭스 스키마 (docs/00_BRIEF.md §10).

행은 사용자의 실제 업무 흐름(§3)에서 도출됐고, 열은 §10 "공통 열"을 그대로 따른다.

**LOCKED §0-7: 시간축(Phase)은 이 매트릭스의 핵심 차별점이므로 삭제하지 않는다.**
일은 두 물결로 온다 — 시행일 전 필수(룰·전산·테스트·공지) / 시행 후(전략·모니터링) /
별도 트리거(대외보고 집계기준). Phase가 없으면 이 매트릭스는 그냥 체크리스트가 된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    """기한 축 — LOCKED. 삭제 금지."""
    D_MINUS = "D-day 전"              # 시행일 전 반드시 끝나야 하는 일
    POST = "시행 후"                   # 시행 후 별도로 도는 일
    SEPARATE_TRIGGER = "별도 트리거"    # 감독당국 요청 등 나중에 도착하는 일


class Priority(str, Enum):
    REQUIRED = "필수"
    REVIEW = "검토"
    REGRESSION = "회귀"


class Owner(str, Enum):
    POLICY = "정책"
    IT = "IT"
    COMMITTEE = "위원회"
    BUSINESS = "현업"


class ApprovalStatus(str, Enum):
    DRAFT = "초안"                     # AI가 만든 초안, 사람 미검토
    PENDING_REVIEW = "검토 대기"
    PENDING_APPROVAL = "승인 대기"      # 위원회 등
    NOT_STARTED = "미착수"


@dataclass(frozen=True)
class Evidence:
    """근거 인용 — 반드시 원문에서 온다.

    `grounded`는 Citation Assurance(원문 verbatim 대조) 결과다. False면 그 근거는
    사람이 원문을 직접 확인해야 한다(환각 가능). None = 미검증.
    """
    source_doc_id: str
    quote: str
    grounded: Optional[bool] = None

    def short(self, n: int = 70) -> str:
        # 원문은 PDF/HWP 추출본이라 문장 중간에 개행이 섞여 있다. 표 셀이 깨지지 않도록 접는다.
        flat = " ".join(self.quote.split())
        q = flat if len(flat) <= n else flat[: n - 1] + "…"
        mark = "" if self.grounded is None else ("✓" if self.grounded else "⚠")
        return f"{mark}[{self.source_doc_id}] \"{q}\""


@dataclass
class ImpactRow:
    """매트릭스 1행 — §10 "공통 열"."""
    area: str                                   # 업무영역
    change: str                                 # 변경 내용
    evidence: list[Evidence] = field(default_factory=list)   # 근거 문서
    affected: str = ""                          # 영향 대상
    deliverable: str = ""                       # 산출물
    priority: Priority = Priority.REVIEW        # 우선순위
    phase: Phase = Phase.D_MINUS                # 기한 ★LOCKED
    owner: Owner = Owner.POLICY                 # 담당
    approval_status: ApprovalStatus = ApprovalStatus.NOT_STARTED
    automatable: bool = False                   # 자동처리 가능 여부
    human_review_reason: Optional[str] = None   # Human Review 필요 사유
    metrics: dict = field(default_factory=dict) # 이 행을 뒷받침하는 실제 수치

    def __post_init__(self) -> None:
        # 자동처리 불가인데 사유가 없으면 매트릭스가 "왜 사람이 봐야 하는지"를 잃는다.
        if not self.automatable and not self.human_review_reason:
            raise ValueError(f"자동처리 불가 행은 사유가 필요하다: {self.area!r}")


@dataclass
class ImpactMatrix:
    """6·30 같은 정책 변경 1건에 대한 전체 임팩트 매트릭스."""
    policy_id: str
    effective_from: Optional[str]
    target_regions: list[str] = field(default_factory=list)
    rows: list[ImpactRow] = field(default_factory=list)
    generated_from: dict = field(default_factory=dict)   # 어떤 입력에서 나왔는지(추적)

    def by_phase(self, phase: Phase) -> list[ImpactRow]:
        return [r for r in self.rows if r.phase == phase]

    @property
    def d_minus_required(self) -> list[ImpactRow]:
        """시행일 전에 반드시 끝나야 하는 일 — 시간 압축 병목의 실체(§3-1)."""
        return [
            r for r in self.rows
            if r.phase == Phase.D_MINUS and r.priority == Priority.REQUIRED
        ]

    @property
    def human_review_rows(self) -> list[ImpactRow]:
        return [r for r in self.rows if not r.automatable]

    @property
    def automation_rate(self) -> float:
        """자동처리 가능 행 비율 — "AI가 어디까지 했는가"의 정직한 표시."""
        return sum(r.automatable for r in self.rows) / len(self.rows) if self.rows else 0.0
