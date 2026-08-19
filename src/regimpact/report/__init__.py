"""검증보고서 — 라이브 파이프라인 수치로 조립한다 (브리프 §18).

손으로 쓴 정적 문서가 아니다. `collect()` 이 파이프라인을 실제로 관통 실행하고,
`render()` 는 그 결과에서만 값을 읽는다. 시스템이 바뀌면 보고서도 바뀐다.

    from regimpact.report import collect, render
    print(render(collect()))

재현: `python examples/build_validation_report.py`
"""
from .evidence import ValidationEvidence, collect
from .validation_report import render

__all__ = ["collect", "render", "ValidationEvidence"]
