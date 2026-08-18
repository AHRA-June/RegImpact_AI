"""RegChange Extractor — 공문 → 구조화 Before/After 추출 (LLM).

설계: LLM 호출(complete)을 주입 가능하게 해 API 키·비용 없이 오프라인 테스트 가능.
실제 실행 백엔드는 `backends.py` 참조 — 기본은 **무과금 경로**(Claude Code CLI /
Gemini 무료 티어 / 수동 중계), Anthropic 종량 API는 선택 경로다.
"""
from __future__ import annotations

from .backends import (  # noqa: F401 - 하위호환 재수출
    CompletionFn,
    anthropic_completion,
    cli_completion,
    gemini_completion,
    manual_completion,
    replay_completion,
    resolve_completion,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import RegChangeExtraction


def extract_regchange(sources: dict[str, str], *, complete: CompletionFn) -> RegChangeExtraction:
    """공문 원문(dict[doc_id, text])에서 RegChange를 추출한다.

    complete는 (system, user) -> dict를 반환하는 주입된 LLM 함수.
    테스트에서는 가짜 complete를, 실행에서는 `resolve_completion(...)`을 넘긴다.
    """
    user = build_user_prompt(sources)
    raw = complete(SYSTEM_PROMPT, user)
    return RegChangeExtraction.from_dict(raw)
