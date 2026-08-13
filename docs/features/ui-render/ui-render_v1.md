# 기능단위: Impact Matrix UI 렌더 (데이터바인딩)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현 커밋 `77a0c65`.)

---

## 1. 목적·책임
`ImpactMatrix`(엔진 실제 산출)를 **self-contained HTML 페이지**로 렌더한다.
Stitch 목업(`docs/ui/stitch_export/_1`)의 **하드코딩·환각값("60%→50%", 세종·부산 등)을
실제 산출로 교체** — UI가 엔진과 항상 일치(single source of truth).

## 2. 입력/출력 인터페이스
- `render_matrix_html(matrix, scenario_title?) -> str` — 완전한 HTML 문서 문자열.
- `render_6_30(as_of_before?) -> str` — 6·30 표준 세그먼트 편의 렌더.
- 생성 스크립트: `examples/render_impact_ui.py` → `docs/ui/generated/impact_matrix.html`.

## 3. 핵심 로직·설계 결정
- **하드코딩 0:** 모든 수치·지역·시점·근거(reason_code·출처)는 matrix에서만 온다.
- **디자인 토큰:** `DESIGN.md`(Institutional Navy, Noto Sans, JetBrains Mono, 상태색)를 CSS 변수로 인라인.
- **self-contained:** 외부 스크립트 의존 없음(폰트 실패 시 시스템 폰트로 저하). 브라우저 즉시 열림.
- **정직성 노출:** REVIEW(escalation) 세그먼트를 별도 "검토 필요" 섹션에 사유와 함께 표시.
- 방향 배지 색: 강화=error, 완화=info, 동일=neutral, 검토=warn(tertiary).

## 4. 관련 파일
- `src/regimpact/impact/render_html.py`
- `tests/test_impact.py`(렌더 5건) · `examples/render_impact_ui.py`
- 산출물: `docs/ui/generated/impact_matrix.html`
- 대체 대상(보존): `docs/ui/stitch_export/_1/code.html`, 정정 프롬프트 `docs/ui/stitch_review.md`

## 5. 검증 상태
- 렌더 테스트 5건(전체 58 통과에 포함):
  실제값 존재 / **환각값(50%·세종·부산·REG-24-001) 부재 단언** / REVIEW 섹션 / meta 바인딩 / 세그먼트 수 일치.

## 6. 알려진 제약·모호성
- 현재 임팩트 매트릭스 1화면만 데이터바인딩. Rule 변경안·고객영향·Assurance 화면은 아직 Stitch 정적(후속).
- Stitch 목업은 '디자인 참고'로 보존(삭제 금지), 실데이터 페이지는 `generated/`에 생성.
