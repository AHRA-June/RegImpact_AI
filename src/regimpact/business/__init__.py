"""사업·제안 문서 렌더러 — 파이프라인 실측에서 조립한다.

제출 문서에 손으로 적은 숫자가 들어가면 시간이 지나며 조용히 거짓말이 된다(2026-08-21
지원서 점검에서 실제로 그랬다). 그래서 이 패키지의 문서는 `ValidationEvidence` 만 읽는다.
"""
from .ops_description import render as render_ops_description

__all__ = ["render_ops_description"]
