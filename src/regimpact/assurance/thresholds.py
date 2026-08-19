"""Assurance 임계값 — `docs/metrics_spec.md` 의 코드 표현.

**임계값은 "우리가 받은 점수"가 아니라 "이 실패가 얼마나 위험한가"에서 정한다.**
실측치는 그 임계가 달성 가능함을 보이는 증거일 뿐, 임계의 근거가 아니다 —
달성치를 그대로 임계로 삼으면 곡선에 맞춰 채점하는 것이 된다.

그래서 각 임계는 `rationale` 없이 등록할 수 없다. 근거를 못 쓰겠으면 그 임계는
아직 정할 준비가 안 된 것이다.

측정할 수 없는 지표에는 임계를 적지 않는다(`threshold=None`). 미측정은 **통과가 아니라
미측정으로** 보고된다 — 모르는 것을 통과로 처리하면 R-01 과 같은 실패다.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Dimension(str, Enum):
    """브리프 §13 의 4 DEEP dimension."""
    HALLUCINATION = "① Hallucination · Grounding"
    REGCHANGE = "② RegChange 추출 완전성"
    POLICY_VERSION = "③ 시점·정책 버전 일관성"
    RULE_TEST = "④ Rule · Test 회귀"


class Direction(str, Enum):
    AT_LEAST = "≥"      # 클수록 좋다
    AT_MOST = "≤"       # 작을수록 좋다


@dataclass(frozen=True)
class Threshold:
    metric: str
    dimension: Dimension
    threshold: Optional[float]      # None = 측정 불가라 임계를 정하지 않음
    direction: Direction
    rationale: str
    high_risk: bool = False

    def __post_init__(self) -> None:
        if self.threshold is not None and not 0.0 <= self.threshold <= 1.0:
            raise ValueError(f"{self.metric}: 임계는 비율(0~1)이어야 한다")
        if not self.rationale.strip():
            raise ValueError(
                f"{self.metric}: 근거 없는 임계는 등록할 수 없다 — "
                "근거를 못 쓰겠으면 아직 정할 준비가 안 된 것이다")

    def passes(self, value: Optional[float]) -> Optional[bool]:
        """통과 여부. 임계가 없거나 값이 없으면 None(미측정)."""
        if self.threshold is None or value is None:
            return None
        return (value >= self.threshold if self.direction is Direction.AT_LEAST
                else value <= self.threshold)

    @property
    def display(self) -> str:
        if self.threshold is None:
            return "—"
        return f"{self.direction.value} {self.threshold:.0%}"


THRESHOLDS: tuple[Threshold, ...] = (
    # ① Hallucination · Grounding
    Threshold(
        "Citation Correctness", Dimension.HALLUCINATION, 0.98, Direction.AT_LEAST,
        "인용 무결성은 검증보고서 전체의 기반이다. 다만 원문 추출 아티팩트로 인한 오차 여지를 "
        "2% 둔다 — 실제로 공백 정규화 문제로 오판정이 있었다(D-03).",
    ),
    Threshold(
        "Unsupported Claim Rate", Dimension.HALLUCINATION, 0.02, Direction.AT_MOST,
        "원문 근거 없는 주장은 이 시스템의 1순위 실패다. 0%를 요구하지 않는 이유는 "
        "Citation Correctness 와 같다(추출 아티팩트 여지).",
    ),
    # ② RegChange 추출
    Threshold(
        "Change Completeness", Dimension.REGCHANGE, 0.95, Direction.AT_LEAST,
        "100%를 요구하지 않는 이유: 변경 항목은 열거의 경계가 해석에 따라 달라진다"
        "(무엇을 한 건으로 셀 것인가). 다만 놓친 항목은 반드시 목록으로 보고한다.",
    ),
    Threshold(
        "Exception Recall", Dimension.REGCHANGE, 1.0, Direction.AT_LEAST,
        "예외를 놓치면 규제 적용을 과대·과소 판정한다. 여신 심사에서 고객에게 직접 손해가 "
        "가는 오류라 타협 구간이 없다. D-02 에서 50%가 나왔고 구조를 바꿔 100%를 만들었다 — "
        "달성 가능한 요구임이 확인됐다.",
        high_risk=True,
    ),
    Threshold(
        "Effective-date Accuracy", Dimension.REGCHANGE, 1.0, Direction.AT_LEAST,
        "시행일 하나가 틀리면 그 위의 판정이 전부 틀린다. 경과규정 컷오프도 시행일에서 "
        "유도되므로 오차가 두 배로 전파된다.",
        high_risk=True,
    ),
    Threshold(
        "Region Accuracy", Dimension.REGCHANGE, 1.0, Direction.AT_LEAST,
        "지역을 잘못 잡으면 규제 대상 자체가 달라진다. 미등록 지역을 비규제로 흘리던 결함이 "
        "실제로 있었다(R-01).",
        high_risk=True,
    ),
    # ③ 시점 · 정책 버전
    Threshold(
        "Policy Baseline Consistency", Dimension.POLICY_VERSION, 1.0, Direction.AT_LEAST,
        "정책 DB 와 엔진 지역 기준선이 갈라지면 판정과 감사 기록이 어긋난다. "
        "한쪽만 고쳐도 다른 테스트는 전부 통과하므로 이 검사가 유일한 방어선이다.",
        high_risk=True,
    ),
    Threshold(
        "Policy-version Consistency", Dimension.POLICY_VERSION, None, Direction.AT_LEAST,
        "시점 질의 골드가 🤖 초안(TEMPORAL 12문항, 사람 검수 전)이라 아직 확정 수치로 "
        "측정할 수 없다. 측정할 수 없는 지표에 임계를 먼저 적지 않는다 — "
        "검수 완료 후 측정을 가동하며 임계를 정한다(2026-08-19 결정).",
    ),
    # ④ Rule · Test
    Threshold(
        "Rule-regression Pass Rate", Dimension.RULE_TEST, 1.0, Direction.AT_LEAST,
        "엔진이 확정 명세의 구현이라는 주장 자체가 여기 걸려 있다. 한 건이라도 어긋나면 "
        "구현이 명세와 다르다는 뜻이므로 타협 구간이 없다.",
        high_risk=True,
    ),
    Threshold(
        "Boundary-case Pass Rate", Dimension.RULE_TEST, 1.0, Direction.AT_LEAST,
        "경계(컷오프 당일·시행 전일)는 실무에서 분쟁이 나는 지점이다. 하루 차이로 고객의 "
        "한도가 달라지므로 경계에서 틀리면 곧바로 민원과 소급 정정으로 이어진다.",
        high_risk=True,
    ),
    Threshold(
        "Conflict-case Pass Rate", Dimension.RULE_TEST, 1.0, Direction.AT_LEAST,
        "조건이 충돌할 때 임의로 하나를 고르지 않고 명세 우선순위대로 판정하거나 "
        "escalate 하는지를 본다.",
        high_risk=True,
    ),
    Threshold(
        "JS Port Agreement", Dimension.RULE_TEST, 1.0, Direction.AT_LEAST,
        "화면의 JS 포팅본이 Python 엔진과 갈라지면 화면만 조용히 거짓말을 한다. "
        "두 번째 구현을 두는 대가로 100% 일치를 요구한다.",
        high_risk=True,
    ),
)

BY_METRIC = {t.metric: t for t in THRESHOLDS}
