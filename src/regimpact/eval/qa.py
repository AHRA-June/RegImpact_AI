"""골드셋 QA 평가 하네스 — 문항을 실제 숫자로 바꾼다.

골드셋만으로는 아무것도 측정되지 않는다. 이 모듈이 공문 원문 + 질문을 LLM에 태우고,
답변을 골드와 대조해 `metrics_spec`의 DEEP dimension ①②③을 산출한다.

채점은 **LLM 심판을 쓰지 않는다.** gold_facts 부분문자열 매칭 + 인용의 원문 verbatim 대조 —
둘 다 결정적이다. LLM이 LLM을 채점하면 그 채점의 신뢰도를 다시 검증해야 하고, 그 회귀는 끝나지 않는다.
대가는 표현이 달라 놓치는 false negative이며, 그래서 gold_facts를 짧은 원자 문자열로 둔다.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional

from .schema import Category, GoldItem

CompletionFn = Callable[[str, str], dict]

QA_SYSTEM_PROMPT = """당신은 금융 규제 문서 질의응답 보조 도구다. 제공된 공식 공문 원문만을 근거로
질문에 답한다.

절대 규칙:
1. 제공된 원문에 있는 내용만으로 답한다. 일반 상식·기억·추론으로 채우지 마라.
2. 각 답변의 citation.quote는 원문에서 **그대로 복사한 문장(부분)** 이어야 한다. 요약·의역 금지.
3. **원문에 답이 없으면 지어내지 말고** needs_human_review=true로 표시하고,
   answer에는 "원문에 답이 없다"는 사실과 그 이유(어떤 단서가 범위를 한정하는지)를 쓴다.
4. 표에는 적용범위 단서(주1) 무주택자 기준, "아파트 限" 등)가 붙어 있다. 단서를 무시하고
   값을 옮기지 마라. 단서 때문에 답할 수 없으면 3번을 따른다.
5. 비슷하지만 다른 값에 주의하라(수도권 vs 수도권 外, 7.1 vs 7.5, 조정 50% vs 투기과열 40%).
6. 열거를 축약하지 마라. 한 문서가 "A, B 등"으로 줄여 쓰고 다른 문서가 전부 나열하면
   **전부 나열한 쪽**을 기준으로 답한다.

각 질문에 대해 answer(한국어 서술) · citations(1개 이상) · needs_human_review 를 낸다."""

QA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "answer": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_doc_id": {"type": "string"},
                                "quote": {"type": "string"},
                            },
                            "required": ["source_doc_id", "quote"],
                            "additionalProperties": False,
                        },
                    },
                    "needs_human_review": {"type": "boolean"},
                },
                "required": ["id", "answer", "citations", "needs_human_review"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}


QA_JSON_INSTRUCTION = """
[출력 형식 — 반드시 지킬 것]
설명·머리말·코드펜스 없이 **JSON 객체 하나만** 출력하라. 최상위 키는 "answers" 하나다.
  "answers": 객체 배열. 각 원소의 키는 정확히
      "id"(질문에 주어진 id 그대로),
      "answer"(string, 한국어 서술),
      "citations": [{"source_doc_id": string, "quote": string}]  ← 1개 이상, quote는 원문 verbatim
      "needs_human_review"(boolean)
질문 하나당 원소 하나. 빠뜨리지 마라.
"""


def validate_qa_response(obj: dict) -> list:
    """QA 응답 형식 검증 — `backends.with_schema_retry`에 주입한다."""
    errs: list[str] = []
    answers = obj.get("answers")
    if not isinstance(answers, list):
        return ["필수 키 누락 또는 형식 오류: answers(배열)"]
    if not answers:
        errs.append("answers가 비어 있음")
    for i, a in enumerate(answers):
        if not isinstance(a, dict):
            errs.append(f"answers[{i}]는 객체여야 함")
            continue
        if not isinstance(a.get("id"), str) or not a.get("id"):
            errs.append(f"answers[{i}].id 누락")
        if not isinstance(a.get("answer"), str) or not a.get("answer"):
            errs.append(f"answers[{i}].answer 누락")
        if not isinstance(a.get("needs_human_review"), bool):
            errs.append(f"answers[{i}].needs_human_review는 boolean이어야 함")
        cits = a.get("citations")
        if not isinstance(cits, list) or not cits:
            errs.append(f"answers[{i}].citations 누락(1개 이상)")
            continue
        for j, c in enumerate(cits):
            if not isinstance(c, dict) or not c.get("source_doc_id") or not c.get("quote"):
                errs.append(f"answers[{i}].citations[{j}] 불완전")
    return errs


def build_qa_prompt(sources: dict[str, str], items: list[GoldItem]) -> str:
    parts = ["다음은 공식 공문 원문이다. 각 문서는 <doc id=...> 태그로 구분된다.\n"]
    for doc_id, text in sources.items():
        parts += [f"<doc id={doc_id}>", text.strip(), "</doc>\n"]
    parts.append("아래 질문들에 각각 답하라. id를 그대로 실어 answers 배열로 낸다.\n")
    for it in items:
        parts.append(f"- id={it.id}: {it.question}")
    return "\n".join(parts)


@dataclass(frozen=True)
class QAResponse:
    item_id: str
    answer: str
    citations: tuple[tuple[str, str], ...]   # (source_doc_id, quote)
    needs_human_review: bool


def answer_questions(
    items: list[GoldItem], sources: dict[str, str], *,
    complete: CompletionFn, batch_size: int = 5,
    on_batch: Optional[Callable[[int, int], None]] = None,
) -> dict[str, QAResponse]:
    """문항을 batch_size씩 묶어 LLM에 태운다.

    묶는 이유는 호출 비용이고, 그 대가는 **한 배치 안의 질문끼리 서로 힌트가 될 수 있다**는 것이다.
    배치가 작을수록 오염이 적고 호출이 늘어난다. 이 값은 평가 설계 파라미터로 리포트에 기록한다.
    """
    out: dict[str, QAResponse] = {}
    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]
    for n, batch in enumerate(batches, 1):
        if on_batch:
            on_batch(n, len(batches))
        raw = complete(QA_SYSTEM_PROMPT, build_qa_prompt(sources, batch))
        for a in raw.get("answers", []):
            out[a["id"]] = QAResponse(
                item_id=a["id"],
                answer=a.get("answer", ""),
                citations=tuple(
                    (c["source_doc_id"], c["quote"]) for c in a.get("citations", [])
                ),
                needs_human_review=bool(a.get("needs_human_review", False)),
            )
    return out


# ---------------------------------------------------------------- 채점 정규화
#
# gold_facts는 **내용 재현**을 보는 앵커지 표현을 보는 앵커가 아니다. 첫 실측(2026-08-18)에서
# 실패 12건이 전부 표현 차이였다 — "25.9.7" vs "2025년 9월 7일", "증액 없는" vs "증액없는",
# "규제지역 여부와 무관" vs "규제지역인지 여부와 관계없이". 여기서 프롬프트를 고쳤다면
# 채점기에 맞춰 모델을 훈련시킨 셈이 된다. 그래서 **모델이 아니라 채점기를 고쳤다.**
#
# 다만 채점기를 느슨하게 만드는 것은 지표를 망가뜨리는 가장 흔한 경로이므로 두 가지만 허용한다:
#   1) 의미를 바꾸지 않는 표면 정규화 — 공백 제거, 날짜 표기 통일, 따옴표·중점 통일
#   2) `|`로 명시한 동의 표현 — 골드 파일에 남아 사람이 감사할 수 있다
# 동의어를 자동 추론하거나 LLM 심판을 쓰지는 않는다.

_DATE_KR = re.compile(r"(\d{2,4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_DATE_DOT = re.compile(r"[’'‘]?(\d{2,4})\s*[.]\s*(\d{1,2})\s*[.]\s*(\d{1,2})\s*[.]?")


def _canon_dates(s: str) -> str:
    """'2025년 9월 7일' · '’25.9.7' · '2025.09.07' → '25.9.7' 로 통일."""
    def _fmt(y: str, m: str, d: str) -> str:
        return f"{int(y) % 100}.{int(m)}.{int(d)}"
    s = _DATE_KR.sub(lambda m: _fmt(*m.groups()), s)
    return _DATE_DOT.sub(lambda m: _fmt(*m.groups()), s)


def _norm(s: str) -> str:
    """비교용 정규화 — 의미를 바꾸지 않는 표면 차이만 제거한다."""
    s = _canon_dates(s.lower())
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("·", "").replace("‧", "").replace("․", "")
    return re.sub(r"\s+", "", s)


def fact_matches(fact: str, answer: str) -> bool:
    """gold_fact가 답변에 담겼는가. `|`로 구분된 동의 표현 중 하나만 맞아도 통과."""
    hay = _norm(answer)
    return any(_norm(alt) in hay for alt in fact.split("|") if alt.strip())


def _rate(hit: int, total: int) -> Optional[float]:
    """0건 중 0건은 100% 가 아니다 — 대조할 것이 없으면 값을 내지 않는다.

    이 저장소가 2026-08-21 에 추출 지표에서 잡은 것과 같은 결함이다. `x / total if total
    else 1.0` 은 **아무것도 대조하지 않은 실행을 만점으로 보고**하고, 그 만점은 하한
    임계를 그대로 통과한다. 미측정은 통과가 아니다(`assurance/scorecard.py` 와 같은 규율).
    """
    return hit / total if total else None


@dataclass
class ItemScore:
    item_id: str
    category: str
    facts_total: int
    facts_hit: int
    missed_facts: list[str]
    citations_total: int
    citations_grounded: int
    escalation_expected: bool
    escalation_given: bool

    @property
    def fact_coverage(self) -> Optional[float]:
        """담아낸 골드 사실 비율. **대조할 사실이 0건이면 값을 내지 않는다.**

        escalation 형 문항은 "원문에 답이 없다"가 정답이라 gold_facts 가 비어 있다.
        그걸 100% 로 세면 답을 안 한 문항이 만점으로 집계에 들어간다.
        """
        return _rate(self.facts_hit, self.facts_total)

    @property
    def exact(self) -> bool:
        """모든 gold_fact를 담았고 escalation 판단도 맞았는가.

        사실이 0건인 문항은 `escalation_ok` 하나로 갈린다 — 담을 사실이 없는 것이지
        비율이 100% 인 것이 아니다(그래서 `fact_coverage` 와 판단 근거가 다르다).
        """
        return self.facts_hit == self.facts_total and self.escalation_ok

    @property
    def escalation_ok(self) -> bool:
        return self.escalation_expected == self.escalation_given


@dataclass
class QAReport:
    scores: list[ItemScore] = field(default_factory=list)
    unanswered: list[str] = field(default_factory=list)
    batch_size: int = 0
    provider: str = ""
    model: str = ""

    @property
    def total(self) -> int:
        return len(self.scores)

    @property
    def fact_coverage(self) -> Optional[float]:
        """골드 사실 중 답변이 담아낸 비율 — Change/Exception Completeness 계열.

        대조할 사실이 0건이면 **0% 가 아니라 미측정**이다. 0% 는 "전부 놓쳤다"는 주장이고,
        그건 사실이 하나도 없는 실행에 대해 참일 수 없다.
        """
        return _rate(sum(s.facts_hit for s in self.scores),
                     sum(s.facts_total for s in self.scores))

    @property
    def exact_rate(self) -> Optional[float]:
        """채점한 문항이 0건이면 0% 가 아니라 미측정이다."""
        return _rate(sum(s.exact for s in self.scores), self.total)

    @property
    def citation_correctness(self) -> Optional[float]:
        """인용이 원문에 verbatim 실재하는 비율.

        **대조할 인용이 0건이면 값을 내지 않는다.** 인용을 하나도 달지 않은 실행이
        "인용 정확성 100%" 로 보고되는 것이 이 함정의 가장 나쁜 모양이다 —
        근거를 대지 않을수록 점수가 좋아진다.
        """
        return _rate(sum(s.citations_grounded for s in self.scores),
                     sum(s.citations_total for s in self.scores))

    @property
    def unsupported_claim_rate(self) -> Optional[float]:
        cc = self.citation_correctness
        return None if cc is None else 1.0 - cc

    @property
    def items_without_citation(self) -> int:
        return sum(1 for s in self.scores if s.citations_total == 0)

    # --- escalation (metrics_spec §4) ---
    @property
    def escalation_precision(self) -> Optional[float]:
        """올린 것 중 실제로 올려야 했던 비율 — 낮으면 과잉 escalation.

        **하나도 올리지 않았으면 미측정이다.** 아무것도 안 올린 실행을 "올린 것 중
        100% 가 옳았다"로 세면, 절대 escalation 하지 않는 모델이 만점을 받는다.
        """
        given = [s for s in self.scores if s.escalation_given]
        return _rate(sum(s.escalation_expected for s in given), len(given))

    @property
    def escalation_recall(self) -> Optional[float]:
        """올려야 했던 것 중 올린 비율 — 낮으면 **원문에 없는 답을 지어냈다**는 뜻.

        올려야 할 문항이 0건이면 미측정이다 — 시험에 그 문제가 안 나온 것이지
        만점을 받은 것이 아니다.
        """
        need = [s for s in self.scores if s.escalation_expected]
        return _rate(sum(s.escalation_given for s in need), len(need))

    def by_category(self) -> dict[str, tuple[int, Optional[float], Optional[float]]]:
        """카테고리 → (문항수, fact_coverage, exact_rate). 비율은 미측정이면 None."""
        out = {}
        for cat in {s.category for s in self.scores}:
            subset = [s for s in self.scores if s.category == cat]
            out[cat] = (
                len(subset),
                _rate(sum(s.facts_hit for s in subset),
                      sum(s.facts_total for s in subset)),
                _rate(sum(s.exact for s in subset), len(subset)),
            )
        return dict(sorted(out.items()))

    @property
    def worst_items(self) -> list[ItemScore]:
        """나쁜 것부터. 사실이 0건인 문항은 **비율로 줄 세울 수 없으므로** 뒤로 보낸다 —
        여기 들어왔다면 이유는 escalation 판단이지 사실 누락이 아니다."""
        return sorted(
            [s for s in self.scores if not s.exact],
            key=lambda s: (1.0 if s.fact_coverage is None else s.fact_coverage,
                           s.escalation_ok),
        )

    def failure_modes(self) -> dict[str, int]:
        """실패를 원인별로 센다 — 무엇을 고쳐야 하는지는 총점이 아니라 여기서 나온다."""
        c: Counter = Counter()
        for s in self.scores:
            if s.escalation_expected and not s.escalation_given:
                c["원문에 없는 답을 지어냄(escalation 누락)"] += 1
            if s.escalation_given and not s.escalation_expected:
                c["과잉 escalation(답이 있는데 못 찾음)"] += 1
            if s.facts_hit < s.facts_total:
                c["골드 사실 누락"] += 1
            if s.citations_total and s.citations_grounded < s.citations_total:
                c["인용 환각(원문에 없는 인용)"] += 1
            if not s.citations_total:
                c["근거 인용 없음"] += 1
        return dict(c.most_common())


def score_qa(
    items: list[GoldItem], responses: dict[str, QAResponse], sources: dict[str, str],
    **meta,
) -> QAReport:
    """골드와 대조해 채점한다. 결정적 — 같은 입력이면 같은 점수."""
    norm_sources = {k: _norm(v) for k, v in sources.items()}
    rep = QAReport(**meta)

    for item in items:
        resp = responses.get(item.id)
        if resp is None:
            rep.unanswered.append(item.id)
            continue

        missed = [f for f in item.gold_facts if not fact_matches(f, resp.answer)]

        grounded = 0
        for doc_id, quote in resp.citations:
            src = norm_sources.get(doc_id)
            if src is not None and _norm(quote) and _norm(quote) in src:
                grounded += 1

        rep.scores.append(ItemScore(
            item_id=item.id,
            category=item.category.value,
            facts_total=len(item.gold_facts),
            facts_hit=len(item.gold_facts) - len(missed),
            missed_facts=missed,
            citations_total=len(resp.citations),
            citations_grounded=grounded,
            escalation_expected=item.expect_escalation,
            escalation_given=resp.needs_human_review,
        ))
    return rep


def _cell(v: Optional[float]) -> str:
    return "     —" if v is None else f"{v:>6.0%}"


def _fmt(v: Optional[float], why: str) -> str:
    """미측정을 빈칸으로 흘리지 않는다 — **왜** 못 쟀는지까지 같은 줄에 적는다.

    빈칸은 읽는 사람이 각자 해석하게 되고, 대개 "괜찮은가 보다"로 읽힌다.
    """
    return f"{v:>7.1%}" if v is not None else f"      —   미측정 — {why}"


def format_qa_report(rep: QAReport) -> str:
    n_facts = sum(s.facts_total for s in rep.scores)
    n_cites = sum(s.citations_total for s in rep.scores)
    n_given = sum(1 for s in rep.scores if s.escalation_given)
    n_need = sum(1 for s in rep.scores if s.escalation_expected)
    L = [
        f"QA 평가 — {rep.total}문항 (provider={rep.provider} model={rep.model} "
        f"batch_size={rep.batch_size})",
        "",
        f"  Fact Coverage         {_fmt(rep.fact_coverage, '대조할 골드 사실이 0건')}",
        f"  Exact Rate            {_fmt(rep.exact_rate, '채점된 문항이 0건')}"
        + ("   (골드 사실 전부 + escalation 판단 일치)" if rep.exact_rate is not None else ""),
        f"  Citation Correctness  {_fmt(rep.citation_correctness, '대조할 인용이 0건')}",
        f"  Unsupported Claim Rate{_fmt(rep.unsupported_claim_rate, '대조할 인용이 0건')}",
        f"  Escalation Precision  {_fmt(rep.escalation_precision, 'escalation 한 문항이 0건')}",
        f"  Escalation Recall     {_fmt(rep.escalation_recall, 'escalation 해야 할 문항이 0건')}"
        + ("   (낮으면 없는 답을 지어냄)" if rep.escalation_recall is not None else ""),
        "",
        f"  대조 재료: 골드 사실 {n_facts} · 인용 {n_cites} · "
        f"escalation 한 {n_given} / 해야 할 {n_need}",
    ]
    if rep.items_without_citation:
        L.append(f"  ⚠ 근거 인용이 없는 답변 {rep.items_without_citation}건")
    if rep.unanswered:
        L.append(f"  ⚠ 미응답 {len(rep.unanswered)}건: {', '.join(rep.unanswered[:5])}")

    L += ["", "  카테고리별 (문항 / fact_coverage / exact):"]
    for cat, (n, fc, ex) in rep.by_category().items():
        L.append(f"    {cat:<16} {n:>3}   {_cell(fc)}   {_cell(ex)}")

    modes = rep.failure_modes()
    if modes:
        L += ["", "  실패 유형:"]
        for name, n in modes.items():
            L.append(f"    {name}: {n}건")
    return "\n".join(L)
