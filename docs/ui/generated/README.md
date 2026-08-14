# Generated UI — 엔진/평가 산출물로 렌더된 화면

이 폴더의 HTML은 **손으로 쓴 목업이 아니라** `regimpact` 엔진·평가 출력에서 자동 생성된다.
Stitch 목업(`../stitch_export/`)은 **디자인 참고**로 보존하고, 데이터가 들어가는 화면은
여기서 실제 판정·집계로 대체한다.

| 파일 | 화면 | 대체 대상 | 데이터 소스 |
|---|---|---|---|
| `regulatory_analysis.html` | 규제 변경 분석 | `stitch_export/_2` | RegChange gold(`docs/eval/regchange_gold_6_30.json`) + SOURCES + 엔진 상수 |
| `impact_matrix.html` | 임팩트 매트릭스 | `stitch_export/_1` | `build_impact_matrix()` (룰엔진 Before/After) |
| `rule_amendment.html` | Rule 변경안 | `stitch_export/rule` | rule_engine 상수 + regions + 경과규정 cutoff + Impact Matrix |
| `assurance.html` | 검증 (Assurance) | `stitch_export/assurance` | tc_generator 회귀(실측) + LLM 지표 '실측 대기' |
| `portfolio_impact.html` | 고객·포트폴리오 영향 | `stitch_export/_3` | 합성 포트폴리오 × 룰엔진 집계 |
| `index.html` | 화면 인덱스 | — | 위 5개 링크 허브 |

## 왜 생성하나 (하드코딩 금지)

Stitch 목업은 도메인 데이터를 화면마다 다르게 환각했다(예: 지역을 세종·부산·강남으로,
"LTV 60%→50%", 가짜 "AI CONFIDENCE 98.5%", 가상 담당자·"약 1,240건"). 생성 화면은 값을
화면에 적지 않고 엔진/평가 출력으로 표를 채운다. 규제 명세가 바뀌면(엔진/regions/gold 갱신)
`render_ui.py`만 다시 돌리면 화면이 따라 바뀐다. → **환각 재발 불가.**

각 화면은 **정직성**을 명시적으로 노출한다:
- 임팩트/포트폴리오: 非규제 유주택 기준선은 원문에 없어 `명세부재→신규 제한`(70→0 지어내지 않음).
- 검증: Rule-regression만 지금 실측, LLM 의존 지표는 `실측 대기`(가짜 수치 없음).
- 포트폴리오: `합성(synthetic) — 실데이터 아님` 배너 + 각 차주 LTV는 엔진 실제 판정.

디자인 시스템(색·타이포·사이드바·헤더)은 `src/regimpact/ui/templates/*.html`에 기존 Stitch
export에서 추출해 보존하며, 사이드바 활성 항목만 화면별로 바뀐다(`ui/chrome.py`).

## 렌더 방법

```bash
python examples/render_ui.py    # 5개 화면 + index 생성
```

또는 코드에서:

```python
from regimpact.ui import render_all
render_all()   # docs/ui/generated/ 에 기록
```

## 보는 방법

`index.html`을 브라우저로 연다. 스타일은 Tailwind CDN·Google Fonts를 로드하므로(기존 Stitch
export와 동일) **네트워크 연결이 있는 브라우저**에서 열어야 디자인이 보인다. 오프라인/샌드박스
에서는 데이터·막대 폭(인라인)은 정확하나 색·폰트가 적용되지 않는다.
