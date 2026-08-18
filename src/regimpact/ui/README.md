# regimpact.ui — 화면 렌더러 (Stitch 디자인 + 엔진 실제 출력)

Google Stitch 1차 목업(`docs/ui/stitch_export/`)은 **디자인은 훌륭했지만 도메인 데이터를 환각**했다
(2026-08-10 리뷰: 지역을 세종·부산·강남·분당으로, LTV 60%→50%, 경과규정 부등호 반대).
그래서 **껍데기는 보존하고 값만 갈아끼운다.**

| | Stitch 목업 | 생성 화면 |
|---|---|---|
| 디자인 토큰 | 원본 | `theme.py`가 export에서 그대로 가져옴(테스트로 고정) |
| 도메인 값 | ❌ LLM이 지어냄 | ✅ 추출기·룰엔진·회귀의 실제 출력 |
| 스타일 방식 | `cdn.tailwindcss.com` 런타임 JIT | 같은 토큰에서 만든 **정적 CSS 인라인** |
| 외부 요청 | Tailwind CDN + 아이콘 폰트 + 웹폰트 | 웹폰트 1건(실패해도 읽힘) |
| 값이 틀리면 | 사람이 눈으로 잡아야 함 | **테스트가 실패함** |

## 구조

- `theme.py` — Stitch 토큰(`TAILWIND_CONFIG`, export에서 verbatim) → `build_css()`로 정적 CSS 생성.
  셸(사이드바·헤더), `card`/`stat`/`chip`/`table`/`bar` 컴포넌트, 인라인 SVG 아이콘.
- `pages.py` — 5개 화면. **리터럴 도메인 수치를 적지 않는 것이 규칙**이다.
- `site.py` — `render_site()`(dict 반환 → 테스트가 파일 없이 검사 가능) / `write_site()`

## ★ UI grounding — 이 패키지의 존재 이유

Citation Assurance가 LLM 인용을 원문에 대조하듯, `tests/test_ui.py`는 **화면 표시값을 엔진 출력에
대조**한다. Stitch 사고를 회귀 테스트로 고정한 것이다.

- 환각 지역명(세종·부산·해운대·강남·서초·분당)이 어느 화면에도 없을 것
- 화면의 지역코드가 추출 결과 또는 실제 포트폴리오에 있을 것
- `60% → 50%` 같은 존재하지 않는 전이가 없을 것
- Rule 화면의 LTV 값이 **엔진 상수 집합 밖으로 나가지 않을 것**(하드코딩 금지 — 양방향 검사)
- 경과규정 부등호가 `<=`일 것 (`>=` 아님)
- 포트폴리오·회귀·추출 수치가 리포트 객체의 값과 문자열 단위로 일치할 것
- 추출된 항목·매트릭스 행·Human Review 사유가 하나도 누락되지 않을 것
- 임계값 미확정 지표는 지어내지 말고 `TBD`로 표시할 것

위 가드는 **변이 테스트로 방어력을 확인**했다(환각 지역명 주입 / `60%→50%` 주입 / 부등호 반전 /
값 하드코딩 / CSS 규칙 제거 / CDN 재도입 → 각각 해당 테스트가 실패).

## 실행

```bash
python examples/build_ui.py        # docs/ui/generated/ 생성 (LLM 호출 0회, 0원)
python -m pytest -k ui             # 23개
```

생성물은 `docs/ui/generated/index.html`을 브라우저로 열면 된다 — 서버·네트워크 불필요.
