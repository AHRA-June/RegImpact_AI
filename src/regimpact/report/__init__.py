"""검증보고서(Validation Report) — 라이브 파이프라인 수치로 생성.

핵심 진입점:
    build_validation_report(generated_at?) -> str   (Markdown 검증보고서)

브리프 §18 "코어 완성의 정의"의 종착점. run_e2e·포트폴리오 회귀·골드셋·판별력을
실제로 호출해 재현 가능한 수치로 보고서를 조립한다.
"""
from .controls import bad_extraction, discrimination_pairs, e2e_control
from .validation_report import build_validation_report

__all__ = [
    "build_validation_report",
    "bad_extraction",
    "discrimination_pairs",
    "e2e_control",
]
