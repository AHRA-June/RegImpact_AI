"""BM25 색인 — 표준 라이브러리만으로, JS 포팅이 쉬운 형태로.

한국어 형태소 분석기는 외부 의존이라 쓰지 않는다. 대신 **한글 연속 구간을 문자
2-gram 으로** 쪼갠다 — 조사·어미 변화("규제지역이/규제지역은")에 어휘 매칭이
깨지지 않게 하는, 사전 없는 한국어 검색의 표준적인 타협이다.

이 토크나이저·점수식은 `ui/static/search.js` 에 그대로 포팅된다. 두 구현이
갈라지면 화면이 조용히 다른 결과를 보여주므로, 룰엔진 JS 포팅과 같은 방식으로
`tools/verify_search_port.mjs` 가 전 프로브 질의를 대조하고 CI 가 배포를 막는다.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ..regions import REGION_ALIASES, REGION_LABELS
from .chunker import Chunk

K1 = 1.5
B = 0.75

_RUN = re.compile(r"[0-9a-z]+|[가-힣]+")


def tokenize(text: str) -> list[str]:
    """소문자화 → 숫자·영문 연속은 그대로, 한글 연속은 2-gram (1글자 구간은 그대로)."""
    out: list[str] = []
    for run in _RUN.findall(text.lower()):
        if run[0] < "가":            # 숫자·영문
            out.append(run)
        elif len(run) == 1:
            out.append(run)
        else:
            out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


# 지역 코드 → 그 지역을 부르는 모든 이름 (별칭 테이블 + 표준 라벨)
_REGION_NAMES: dict[str, list[str]] = {}
for _alias, _code in REGION_ALIASES.items():
    _REGION_NAMES.setdefault(_code, []).append(_alias)
for _code, _label in REGION_LABELS.items():
    names = _REGION_NAMES.setdefault(_code, [])
    if _label not in names:
        names.append(_label)


def expand_query(query: str) -> str:
    """질의에 지역 이름이 있으면 같은 지역의 다른 표기를 덧붙인다.

    "동탄 LTV" 가 원문의 "화성시 동탄구"와 어휘로 만나게 하는 **결정적** 확장이다 —
    D-01(지역 어휘 불일치)을 해결한 별칭 테이블을 검색에서 재사용한다. LLM 확장이
    아니므로 없는 지역이 생기지 않는다.
    """
    extra: list[str] = []
    for code, names in sorted(_REGION_NAMES.items()):
        if any(name in query for name in names):
            extra.extend(n for n in names if n not in query)
    return query if not extra else query + " " + " ".join(sorted(set(extra)))


@dataclass
class Scored:
    chunk: Chunk
    score: float


class BM25Index:
    def __init__(self, chunks: list[Chunk], *, k1: float = K1, b: float = B):
        self.chunks = list(chunks)
        self.k1, self.b = k1, b
        self._tf: list[dict[str, int]] = []
        df: dict[str, int] = {}
        for c in self.chunks:
            tf: dict[str, int] = {}
            for t in tokenize(c.text):
                tf[t] = tf.get(t, 0) + 1
            self._tf.append(tf)
            for t in tf:
                df[t] = df.get(t, 0) + 1
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = (sum(self._len) / n) if n else 0.0

    def search(self, query: str, k: int = 5, *, expand: bool = False) -> list[Scored]:
        if expand:
            query = expand_query(query)
        q_terms = sorted(set(tokenize(query)))
        scored: list[Scored] = []
        for i, c in enumerate(self.chunks):
            tf, dl = self._tf[i], self._len[i]
            s = 0.0
            for t in q_terms:
                f = tf.get(t)
                if not f:
                    continue
                idf = self._idf.get(t, 0.0)
                s += idf * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self._avg))
            if s > 0:
                scored.append(Scored(chunk=c, score=s))
        scored.sort(key=lambda x: (-x.score, x.chunk.id))
        return scored[:k]

    def export(self) -> dict:
        """JS 포팅본이 같은 색인을 재구축할 수 있는 원재료 (청크 원문만 — 파생값은 재계산)."""
        return {
            "params": {"k1": self.k1, "b": self.b},
            "chunks": [c.to_dict() for c in self.chunks],
            "region_names": {k: sorted(v) for k, v in sorted(_REGION_NAMES.items())},
        }
