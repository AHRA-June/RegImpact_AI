# UI 렌더 레이어 (화면 = 엔진/평가 산출물)

Stitch 목업(`docs/ui/stitch_export/`)이 화면마다 환각한 도메인 데이터를 **엔진/평가 실제 출력**
으로 대체하는 프레젠테이션 레이어. 값을 화면에 적지 않으므로 환각이 재발할 수 없다(엔진=단일 진실).

## 화면 → 데이터 소스

| 렌더러 | data-path | 화면 | 데이터 |
|---|---|---|---|
| `regchange.render()` | regulatory-analysis | 규제 변경 분석 | RegChange gold + SOURCES + 엔진 상수 |
| `impact_matrix.render()` | impact-matrix | 임팩트 매트릭스 | `build_impact_matrix()` |
| `rule_proposal.render()` | rule-amendments | Rule 변경안 | rule_engine 상수·regions·경과규정·Impact Matrix |
| `assurance.render()` | verification-assurance | 검증 | tc_generator 회귀(실측) + LLM 지표 '실측 대기' |
| `portfolio.render()` | portfolio-impact | 고객·포트폴리오 영향 | 합성 포트폴리오 × rule_engine |

## 구조

- **`chrome.py`** — 공용 디자인 셸. `page(active_path, main_html)`가 사이드바·헤더를 감싸고
  활성 nav만 화면별로 바꾼다. 디자인 시스템은 `templates/head_open.html`·`head_after_nav.html`·
  `foot.html`(기존 Stitch export에서 추출)로 보존. 공용 헬퍼(`provenance_strip`·`title_block`·
  `mono_chip`·`card`)도 여기에.
- **각 화면 모듈** — `_main(...)`으로 콘텐츠 HTML을 만들고 `page(...)`로 감싼다.
- **`render_all.py`** — 5개 화면 + `index.html`을 `docs/ui/generated/`에 기록.

## 정직성 (LOCKED §4)

각 화면은 '모르는 값'을 지어내지 않고 표기한다:
- 非규제 유주택 기준선 명세부재 → `명세부재 → 신규 제한`(70→0 금지).
- LLM 의존 Assurance 지표 → `실측 대기`(가짜 98% 금지).
- 포트폴리오 → `합성 — 실데이터 아님` 배너(LOCKED §8).

각 화면 상단의 **provenance 스트립**(엔진 라벨·입력·카운트)이 '실제 산출물'임을 못박는다.

## 사용

```bash
python examples/render_ui.py
```
```python
from regimpact.ui import render_all
render_all()
```

테스트: `tests/test_ui.py` (자기완결·활성 nav 1개·환각 문자열 부재·화면별 실제 값).
