# Generated UI — 엔진 산출물로 렌더된 화면

이 폴더의 HTML은 **손으로 쓴 목업이 아니라** `regimpact.impact` 엔진 출력에서
자동 생성된다. Stitch 목업(`../stitch_export/`)은 **디자인 참고**로 보존하고,
데이터가 들어가는 화면은 여기서 엔진 실제 판정으로 대체한다.

| 파일 | 대체 대상 | 생성 명령 |
|---|---|---|
| `impact_matrix.html` | `stitch_export/_1` (임팩트 매트릭스) | `python examples/render_impact_ui.py` |

## 왜 생성하나 (하드코딩 금지)

Stitch 목업(`_1`)은 도메인 데이터를 환각했다(예: "LTV 60%→50% 하향", 가상의 담당자·기한).
이 화면은 값을 화면에 적지 않고 `build_impact_matrix()`가 룰엔진을 **시행 전(2026-06-30)/
후(2026-07-02)** 두 시점에 실행한 결과로 표를 채운다. 규제 명세가 바뀌면(엔진/regions/
regulatory_facts 갱신) 이 명령만 다시 돌리면 화면이 따라 바뀐다. → 환각 재발 불가.

디자인 시스템(색·타이포·사이드바·헤더)은 `src/regimpact/impact/templates/chrome_*.html`에
기존 Stitch export에서 추출해 그대로 보존한다.

## 렌더 방법

```bash
python examples/render_impact_ui.py
# → docs/ui/generated/impact_matrix.html
```

또는 코드에서:

```python
from regimpact.impact import build_impact_matrix, write_impact_matrix_html
write_impact_matrix_html("docs/ui/generated/impact_matrix.html", build_impact_matrix())
```

## 보는 방법

브라우저로 `impact_matrix.html`을 연다. 스타일은 Tailwind CDN·Google Fonts를 로드하므로
(기존 Stitch export와 동일) **네트워크 연결이 있는 브라우저**에서 열어야 디자인이 보인다.
오프라인/샌드박스에서는 데이터는 정확하나 스타일이 적용되지 않는다.
