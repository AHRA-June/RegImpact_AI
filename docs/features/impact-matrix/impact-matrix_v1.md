# 기능단위: Impact Matrix (시행 전/후 영향)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현 커밋 `3112ef6`.)

---

## 1. 목적·책임
규제 변경의 **임팩트**를 세그먼트별로 산출한다. Walking Skeleton(04_PLAN Phase 1)의
**Before/After → Impact Matrix 노드.** 임팩트 = 같은 고객 프로필을 **시행 전/후 두 시점으로
판정한 차이(temporal diff).**

## 2. 입력/출력 인터페이스
- `analyze_impact(segments, region_code, before_date, after_date, policy_id?) -> ImpactMatrix`
- `analyze_from_extraction(extraction, segments, region_code, after_gap_days=2) -> ImpactMatrix`
  — Extractor `effective_from`에서 before=효력일-1, after=효력일+2 유도(E2E 연결).
- `Segment(segment_id, label, profile)` — 비시점·비지역 프로필 템플릿.
- `ImpactRow` — before/after `LtvDecision`, `direction`, `delta_ltv`, `note`.
- `ImpactMatrix` — rows + 시점 메타 + `summary()` + `review_required`.
- `format_matrix(matrix) -> str` (텍스트 리포트).

## 3. 핵심 로직·설계 결정
- **temporal diff:** 룰엔진(`evaluate`)을 두 시점으로 실행. **규칙값 자체 미보유 → LOCKED §4 준수.**
- **방향 분류:** after<before=TIGHTENED, >LOOSENED, ==UNCHANGED.
- **정직성(브리프 §12):** 한쪽이라도 DECIDED가 아니면(escalation/discovery/scope) 델타를
  억지로 만들지 않고 **REVIEW**로 표면화 + 사유(note). 예: 非규제 유주택 기준값 부재.
- **6·30 산출:** 무주택 70→40(강화), 생애최초 70→70(예외 보호=동일), 서민실수요 70→60,
  처분조건부 70→40, 유주택(비처분1주택·다주택) → REVIEW.

## 4. 관련 파일
- `src/regimpact/impact/` — `matrix.py` `segments.py` `report.py` (`render_html.py`는 `ui-render` 기능단위)
- `tests/test_impact.py` · `examples/demo_impact_matrix.py`

## 5. 검증 상태
- `tests/test_impact.py` — 코어/E2E 14건(+ UI 렌더 5건 = 19건, 전체 58 통과에 포함).
- 룰엔진 일치 검증(자체 규칙값 미보유 확인), 효력일 경계, extraction 시점 유도 커버.

## 6. 알려진 제약·모호성
- 세그먼트 = 6·30 표준 6종(신규 신청 관점, 경과규정 이벤트일 미포함).
- **후속:** 고객영향 행(가격구간·대출한도) 추가, 층화 포트폴리오 연동.
- 유주택 REVIEW는 명세 공백(非규제 유주택 기준선) 때문 — Q6/규제사실 확정 시 해소 가능.
