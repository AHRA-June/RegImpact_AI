"""AI Risk Register — 리스크 식별·평가·통제 (사람 작성 판단 + 코드 참조).

리스크의 발생가능성·영향은 **측정값이 아니라 판단**이라 여기에 사람이 적는다.
대신 통제(control)는 말로 끝나지 않게 **실재하는 코드·테스트를 가리키게** 강제한다
(`tests/test_governance.py` 가 참조 경로의 존재를 확인한다). 통제를 "운영 중"이라고
적어 놓고 근거가 없는 것이 리스크 레지스터가 무력해지는 가장 흔한 경로다.

척도: Likelihood 1~5 × Impact 1~5 = Rating.
  Low 1–4 · Medium 5–9 · High 10–15 · Critical 16–25.
잔여위험은 통제 후 **정직하게** 매긴다 — 0으로 만들지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ControlState(str, Enum):
    OPERATING = "운영"        # 구현·검증됨. evidence 경로가 실재해야 한다.
    PARTIAL = "부분"          # 일부만 구현
    PLANNED = "계획"          # 미구현


class Band(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


def band(rating: int) -> Band:
    if rating <= 4:
        return Band.LOW
    if rating <= 9:
        return Band.MEDIUM
    if rating <= 15:
        return Band.HIGH
    return Band.CRITICAL


@dataclass(frozen=True)
class Control:
    kind: str                 # 검증 | 설계 | 프로세스
    description: str
    state: ControlState
    evidence: tuple[str, ...] = ()     # 저장소 상대 경로 (실재해야 한다)


@dataclass(frozen=True)
class Risk:
    risk_id: str
    category: str
    title: str
    description: str
    inherent_likelihood: int
    inherent_impact: int
    residual_likelihood: int
    residual_impact: int
    controls: tuple[Control, ...]
    owner: str = "시스템"
    accepted_reason: str = ""          # 잔여위험을 수용한다면 근거를 남긴다
    realized_as: str = ""              # 실제로 발생한 적이 있으면 발견사항 ID

    def __post_init__(self) -> None:
        for v in (self.inherent_likelihood, self.inherent_impact,
                  self.residual_likelihood, self.residual_impact):
            if not 1 <= v <= 5:
                raise ValueError(f"{self.risk_id}: 척도는 1~5 여야 한다 (got {v})")
        if self.residual > self.inherent:
            raise ValueError(
                f"{self.risk_id}: 잔여위험({self.residual})이 고유위험({self.inherent})보다 클 수 없다")
        if not self.controls:
            raise ValueError(f"{self.risk_id}: 통제 없는 리스크는 등록할 수 없다")

    @property
    def inherent(self) -> int:
        return self.inherent_likelihood * self.inherent_impact

    @property
    def residual(self) -> int:
        return self.residual_likelihood * self.residual_impact

    @property
    def inherent_band(self) -> Band:
        return band(self.inherent)

    @property
    def residual_band(self) -> Band:
        return band(self.residual)

    @property
    def reduction(self) -> int:
        return self.inherent - self.residual


# ---------------------------------------------------------------------------
# 레지스터 — 사람 작성 판단
# ---------------------------------------------------------------------------
RISKS: tuple[Risk, ...] = (
    # --- AI / LLM 고유 ---
    Risk(
        "R-AI-01", "AI/LLM", "환각 — 원문에 없는 규제 사실 생성",
        "LLM 이 공문에 없는 LTV·시행일·지역을 그럴듯하게 만들어 내고, 그것이 여신 판정으로 전파된다.",
        inherent_likelihood=4, inherent_impact=5,
        residual_likelihood=2, residual_impact=4,
        controls=(
            Control("검증", "인용이 원문에 verbatim 존재하는지 결정적 대조 (LLM 자기판단 아님)",
                    ControlState.OPERATING,
                    ("src/regimpact/extractor/evaluate.py", "tests/test_extractor.py")),
            Control("검증", "판별력 실측 — 환각을 주입하면 지표가 떨어지는지 확인",
                    ControlState.OPERATING,
                    ("src/regimpact/discrimination.py", "tests/test_discrimination.py")),
            Control("설계", "추출은 룰엔진을 수정하지 않는다 — 변경안(DRAFT)으로만 조립",
                    ControlState.OPERATING, ("src/regimpact/proposal/",)),
        ),
        accepted_reason="인용의 **적절성**(원문 아무 문장이나 붙이는 경우)은 미검증이라 "
                        "잔여위험을 0으로 낮추지 않는다.",
    ),
    Risk(
        "R-AI-02", "AI/LLM", "누락 — 변경 사항을 빠뜨림",
        "여러 문서에 흩어진 예외·경과규정을 일부만 추출해, 반영해야 할 변경이 누락된다.",
        inherent_likelihood=4, inherent_impact=4,
        residual_likelihood=2, residual_impact=3,
        controls=(
            Control("검증", "사람 확정 골드 대조 — Change Completeness / Exception Recall",
                    ControlState.OPERATING, ("docs/eval/regchange_gold_6_30.json",)),
            Control("설계", "문서별 추출 후 문서 간 병합 — 문서 간 열거가 서로를 가리는 문제 제거",
                    ControlState.OPERATING, ("src/regimpact/extractor/merge.py",)),
        ),
        accepted_reason="Completeness 는 recall 이지 precision 이 아니다 — 골드에 없는 변경은 측정 밖.",
        realized_as="D-02",
    ),
    Risk(
        "R-AI-03", "AI/LLM", "모델·프롬프트 변경에 따른 드리프트",
        "provider·모델을 교체하면 추출 품질이 조용히 달라지는데, 회귀 없이 배포되면 알 수 없다.",
        inherent_likelihood=4, inherent_impact=3,
        residual_likelihood=2, residual_impact=3,
        controls=(
            Control("설계", "provider 주입 — 동일 입력으로 교체 비교 가능",
                    ControlState.OPERATING, ("src/regimpact/extractor/backends.py",)),
            Control("검증", "봉인된 평가셋(LOCKED/CHALLENGE)으로 교체 시 재측정",
                    ControlState.PARTIAL, ("docs/eval/gold/",)),
        ),
        accepted_reason="LOCKED/CHALLENGE 는 코어 완성 시 1회만 열기로 해 상시 회귀 게이트가 아니다.",
    ),
    Risk(
        "R-AI-04", "AI/LLM", "프롬프트 인젝션 — 원문에 심긴 지시",
        "공문 형식의 입력에 '이전 지시를 무시하라' 류 문구가 섞이면 추출이 조작될 수 있다.",
        inherent_likelihood=2, inherent_impact=4,
        residual_likelihood=2, residual_impact=3,
        controls=(
            Control("설계", "입력은 공개 공문 스냅샷으로 한정 + 해시 고정",
                    ControlState.OPERATING, ("docs/sources/SOURCES.md",)),
            Control("검증", "출력이 룰을 바꾸지 못한다 — 변경안은 사람 승인 전 registry 미반영",
                    ControlState.OPERATING, ("src/regimpact/proposal/consistency.py",)),
            Control("검증", "인젝션 탐지 필터", ControlState.PLANNED, ()),
        ),
        accepted_reason="조작에 성공해도 룰엔진을 직접 바꿀 수 없는 구조라 영향이 제한된다.",
    ),
    Risk(
        "R-AI-05", "AI/LLM", "자동화 편향 — 사람이 AI 산출을 그대로 승인",
        "검토자가 DRAFT 를 형식적으로 승인해 사실상 자동 반영이 된다.",
        inherent_likelihood=3, inherent_impact=4,
        residual_likelihood=3, residual_impact=2,
        controls=(
            Control("설계", "미통과 항목을 사유와 함께 표면화 — 무엇을 봐야 하는지 지정",
                    ControlState.OPERATING, ("src/regimpact/proposal/consistency.py",)),
            Control("설계", "자동처리 불가 행은 사유 없이 생성 불가 (스키마가 거부)",
                    ControlState.OPERATING, ("src/regimpact/impact/schema.py",)),
            Control("프로세스", "승인 이력을 감사로그에 기록",
                    ControlState.OPERATING, ("src/regimpact/audit/",)),
        ),
        accepted_reason="사람의 주의력은 시스템이 통제할 수 없다 — 잔여위험을 Low 로 낮추지 않는다.",
    ),

    # --- 규칙·판정 ---
    Risk(
        "R-RUL-01", "규칙·판정", "룰엔진 구현이 확정 명세와 어긋남",
        "명세는 맞는데 코드가 다르게 동작해 판정이 틀린다.",
        inherent_likelihood=3, inherent_impact=5,
        residual_likelihood=1, residual_impact=4,
        controls=(
            Control("검증", "차등 검증 — 명세를 독립 재구현한 오라클과 전 케이스 대조",
                    ControlState.OPERATING,
                    ("src/regimpact/tc_generator/oracle.py", "tests/test_tc_generator.py")),
            Control("검증", "변이 테스트 — 상수를 변조하면 회귀가 잡는지 확인",
                    ControlState.OPERATING, ("tests/test_discrimination.py",)),
        ),
    ),
    Risk(
        "R-RUL-02", "규칙·판정", "명세 자체가 원문을 오독",
        "엔진과 오라클이 **같은** 오독을 공유하면 일치율 100% 로도 잡히지 않는다.",
        inherent_likelihood=3, inherent_impact=5,
        residual_likelihood=2, residual_impact=5,
        controls=(
            Control("프로세스", "규칙 값은 사람이 원문 대조로 확정 (LOCKED §4)",
                    ControlState.OPERATING, ("docs/regulatory_facts.md", "docs/05_RULE_SPEC.md")),
            Control("검증", "골드 확정 지문 — 확정 후 수정 시 재검수 필요로 드러남",
                    ControlState.OPERATING, ("src/regimpact/eval/confirmation.py",)),
        ),
        accepted_reason="차등검증으로 잡을 수 없는 범주다. 실제로 R-01 이 이 경로로 발생했고, "
                        "지표가 아니라 원문 재독해로 발견됐다. 잔여위험을 High 로 유지한다.",
        realized_as="R-01, R-01b",
    ),
    Risk(
        "R-RUL-03", "규칙·판정", "지역 데이터 누락이 관대한 판정으로 전파",
        "레지스트리에 없는 지역을 비규제로 간주하면, 데이터 공백이 완화된 LTV 로 새어나간다.",
        inherent_likelihood=4, inherent_impact=5,
        residual_likelihood=1, residual_impact=4,
        controls=(
            Control("설계", "미등록 지역은 UNKNOWN → 사람 검토 (P0d). 비규제로 간주하지 않는다",
                    ControlState.OPERATING,
                    ("src/regimpact/regions.py", "tests/test_regions.py")),
            Control("검증", "정책 DB ↔ 기준선 양방향 드리프트 검사",
                    ControlState.OPERATING, ("src/regimpact/policy/consistency.py",)),
        ),
        realized_as="R-01",
    ),
    Risk(
        "R-RUL-04", "규칙·판정", "원문에 값이 없는 구간을 추정으로 메움",
        "기준값이 없는 세그먼트에 그럴듯한 값을 넣으면 근거 없는 판정이 만들어진다.",
        inherent_likelihood=3, inherent_impact=5,
        residual_likelihood=1, residual_impact=3,
        controls=(
            Control("설계", "기준값 부재는 escalate — 추정 금지 (LOCKED §4)",
                    ControlState.OPERATING, ("src/regimpact/rule_engine.py",)),
            Control("설계", "세그먼트 값 충돌 시 동률이면 아무것도 고르지 않는다",
                    ControlState.OPERATING, ("src/regimpact/proposal/builder.py",)),
        ),
        accepted_reason="대가로 영향 측정 커버리지에 상한이 생긴다 — 이는 의도된 트레이드오프다.",
        realized_as="P-01, P-02",
    ),

    # --- 데이터 ---
    Risk(
        "R-DAT-01", "데이터", "원문 스냅샷 변조·교체",
        "검증 근거가 된 원문이 사후에 바뀌면 모든 인용 검증이 무의미해진다.",
        inherent_likelihood=2, inherent_impact=5,
        residual_likelihood=1, residual_impact=4,
        controls=(
            Control("프로세스", "원문 sha256 고정 + 저장소 보관",
                    ControlState.OPERATING, ("docs/sources/SOURCES.md",)),
            Control("검증", "해시 체인 감사로그로 파이프라인 이벤트 고정",
                    ControlState.OPERATING, ("src/regimpact/audit/", "tests/test_audit.py")),
        ),
        accepted_reason="해시 체인은 끝에서 잘라낸 로그를 혼자 잡지 못한다 — head 해시를 "
                        "검증보고서에 외부 앵커로 남긴다.",
    ),
    Risk(
        "R-DAT-02", "데이터", "합성 포트폴리오로 성능을 주장",
        "합성 데이터에서 나온 수치를 실제 성능처럼 제시하면 순환 논증이 된다.",
        inherent_likelihood=3, inherent_impact=3,
        residual_likelihood=1, residual_impact=2,
        controls=(
            Control("프로세스", "합성 포트폴리오는 커버리지 측정 전용 — 정확도 주장 금지",
                    ControlState.OPERATING, ("src/regimpact/impact/portfolio.py",)),
            Control("프로세스", "검증보고서 한계 절에 명시 (L4)",
                    ControlState.OPERATING, ("docs/eval/VALIDATION_LIMITS.md",)),
        ),
    ),
    Risk(
        "R-DAT-03", "데이터", "실제 고객 데이터 유입",
        "개인정보가 저장소·프롬프트에 들어가면 되돌릴 수 없다.",
        inherent_likelihood=2, inherent_impact=5,
        residual_likelihood=1, residual_impact=4,
        controls=(
            Control("설계", "합성 데이터만 사용 — 실 고객 데이터 경로 없음 (LOCKED §0-8)",
                    ControlState.OPERATING, ("src/regimpact/impact/portfolio.py",)),
            Control("프로세스", "입력은 공개 보도자료·FAQ 로 한정",
                    ControlState.OPERATING, ("docs/sources/SOURCES.md",)),
        ),
    ),
    Risk(
        "R-DAT-04", "데이터", "평가셋 오염 — 골드를 보고 모델을 맞춤",
        "골드를 반복해서 보며 프롬프트를 조정하면 측정이 성능이 아니라 암기가 된다.",
        inherent_likelihood=4, inherent_impact=3,
        residual_likelihood=2, residual_impact=3,
        controls=(
            Control("설계", "DEV / LOCKED / CHALLENGE 분리 + 봉인을 코드로 강제 "
                            "(20자 이상 사유 없이는 로드 거부)",
                    ControlState.OPERATING,
                    ("src/regimpact/eval/goldset.py", "tests/test_goldset.py")),
            Control("프로세스", "봉인 접근을 append-only 로그에 기록",
                    ControlState.OPERATING, ("docs/eval/gold/SEAL_ACCESS_LOG.md",)),
        ),
        accepted_reason="DEV 셋은 반복 사용하므로 그 성능은 낙관적으로 읽어야 한다.",
        realized_as="G-01",
    ),

    # --- 거버넌스 ---
    Risk(
        "R-GOV-01", "거버넌스", "변경 이력·승인 근거 부재",
        "무엇이 언제 왜 바뀌었는지 재구성할 수 없으면 검증 결과를 신뢰할 수 없다.",
        inherent_likelihood=3, inherent_impact=4,
        residual_likelihood=1, residual_impact=3,
        controls=(
            Control("검증", "해시 체인 감사로그 — 변조·재정렬·중간삭제 탐지",
                    ControlState.OPERATING, ("src/regimpact/audit/log.py", "tests/test_audit.py")),
            Control("프로세스", "정책 버전을 git 안 JSON 으로 관리 — 이력이 곧 승인 기록",
                    ControlState.OPERATING, ("docs/policies/",)),
            Control("프로세스", "의사결정 로그", ControlState.OPERATING, ("docs/02_DECISION_LOG.md",)),
        ),
    ),
    Risk(
        "R-GOV-02", "거버넌스", "AI 초안이 확정 없이 판정에 사용됨",
        "DRAFT 상태의 정책·변경안이 사람 승인 없이 실제 판정 경로에 들어간다.",
        inherent_likelihood=3, inherent_impact=5,
        residual_likelihood=1, residual_impact=4,
        controls=(
            Control("설계", "CONFIRMED 만 지역 상태에 반영 — DRAFT 는 미리보기만",
                    ControlState.OPERATING,
                    ("src/regimpact/policy/resolver.py", "tests/test_policy.py")),
            Control("설계", "변경안은 항상 DRAFT 로 생성 — APPROVED 로 태어나지 않는다",
                    ControlState.OPERATING, ("src/regimpact/proposal/builder.py",)),
        ),
    ),
    Risk(
        "R-GOV-03", "거버넌스", "검증 하니스가 오류에 둔감해짐",
        "지표가 항상 100% 인데 실은 아무것도 잡지 못하는 상태가 될 수 있다.",
        inherent_likelihood=3, inherent_impact=4,
        residual_likelihood=2, residual_impact=3,
        controls=(
            Control("검증", "판별력(negative control) — 오류 주입 후 지표 반응 측정",
                    ControlState.OPERATING,
                    ("src/regimpact/discrimination.py", "tests/test_discrimination.py")),
            Control("검증", "집계 지표의 둔감성을 테스트로 고정 — 성질이 바뀌면 문서도 고치라고 실패",
                    ControlState.OPERATING, ("docs/eval/VALIDATION_LIMITS.md",)),
        ),
        accepted_reason="집계 비율은 단건 오류에 둔감하다는 성질 자체는 제거할 수 없다.",
    ),

    # --- 운영 ---
    Risk(
        "R-OPS-01", "운영", "비용·자격증명 문제로 재현 불가",
        "리뷰어가 API 키가 없어 결과를 재현하지 못하면 검증 주장이 확인되지 않는다.",
        inherent_likelihood=4, inherent_impact=2,
        residual_likelihood=1, residual_impact=2,
        controls=(
            Control("설계", "replay provider — 실제 실행 기록 재생, LLM 호출 0회",
                    ControlState.OPERATING, ("src/regimpact/extractor/backends.py",)),
            Control("설계", "무과금 경로 우선 (cli → gemini → anthropic → manual)",
                    ControlState.OPERATING, ("docs/06_LLM_PROVIDER.md",)),
        ),
    ),
    Risk(
        "R-OPS-02", "운영", "검증보고서가 코드보다 낡아짐",
        "손으로 쓴 수치가 시스템 변경 후에도 남아 조용히 거짓말이 된다.",
        inherent_likelihood=4, inherent_impact=3,
        residual_likelihood=1, residual_impact=2,
        controls=(
            Control("설계", "보고서를 라이브 실행 결과에서 생성",
                    ControlState.OPERATING, ("src/regimpact/report/evidence.py",)),
            Control("검증", "실측 절에 수치 리터럴 금지 — 테스트가 강제",
                    ControlState.OPERATING, ("tests/test_validation_report.py",)),
        ),
    ),
)


def by_category() -> dict[str, list[Risk]]:
    out: dict[str, list[Risk]] = {}
    for r in RISKS:
        out.setdefault(r.category, []).append(r)
    return out


def heatmap(residual: bool = True) -> dict[tuple[int, int], list[str]]:
    """(likelihood, impact) → 리스크 ID 목록."""
    out: dict[tuple[int, int], list[str]] = {}
    for r in RISKS:
        key = ((r.residual_likelihood, r.residual_impact) if residual
               else (r.inherent_likelihood, r.inherent_impact))
        out.setdefault(key, []).append(r.risk_id)
    return out


def summary() -> dict:
    return {
        "total": len(RISKS),
        "categories": len(by_category()),
        "inherent_bands": _band_counts(residual=False),
        "residual_bands": _band_counts(residual=True),
        "realized": [r.risk_id for r in RISKS if r.realized_as],
        "planned_controls": [
            (r.risk_id, c.description) for r in RISKS for c in r.controls
            if c.state is ControlState.PLANNED
        ],
    }


def _band_counts(*, residual: bool) -> dict[str, int]:
    counts: dict[str, int] = {b.value: 0 for b in Band}
    for r in RISKS:
        counts[(r.residual_band if residual else r.inherent_band).value] += 1
    return counts
