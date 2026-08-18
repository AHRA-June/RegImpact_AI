# regimpact.impact — Impact Analyzer (임팩트 매트릭스)

규제 변경 1건을 **"누가 무엇을 언제까지 해야 하는가"** 로 전개한다. 브리프 §3(실제 업무 흐름)에서
행을 도출하고 §10의 공통 열을 그대로 쓴다.

## 이 모듈이 지키는 원칙

1. **값을 지어내지 않는다.** 모든 행의 수치·근거는 다른 컴포넌트의 실제 출력에서 온다.
   Stitch 목업의 하드코딩 값을 대체하는 것이 목적이다.
   | 행 | 출처 |
   |---|---|
   | 변경 내용·근거 인용 | RegChange Extractor + Citation Assurance |
   | 고객 영향 수치 | deterministic 룰엔진의 before/after 포트폴리오 평가 |
   | 룰 diff | `rule_engine` 상수(=사람 확정 명세) — LLM 생성 아님(LOCKED §4) |
   | 테스트 행 | TC Generator + Rule-Regression 실제 Pass Rate |
2. **Phase(시간축)를 삭제하지 않는다** (LOCKED §0-7). 일은 두 물결로 온다:
   `D-day 전` / `시행 후` / `별도 트리거`. Phase가 없으면 그냥 체크리스트다.
3. **자동/사람 경계를 강제로 명시한다.** `automatable=False`인데 `human_review_reason`이 없으면
   `ImpactRow`가 생성 시점에 `ValueError`를 던진다. 자동화율을 자랑하는 문서가 아니라
   **경계를 고정하는 문서**이기 때문이다.
4. **Discovery Scope는 표시하되 자동판정하지 않는다** (브리프 §24-12). 추출된 `SCOPE_LIMIT`
   항목(전세·신용·중도금·사업자대출 제한)은 별도 행으로 뜨지만 코어 룰엔진에 들어가지 않는다.

## 구조

- `schema.py` — `Phase`(★LOCKED) / `Priority` / `Owner` / `ApprovalStatus` / `Evidence` / `ImpactRow` / `ImpactMatrix`
- `portfolio.py` — 층화 합성 포트폴리오. 비율을 모듈 상수로 노출(조성이 시드에 숨지 않게), 결정적
- `customer.py` — 같은 신청건을 6.30 / 7.1 두 시점으로 룰엔진에 태워 차이 집계 → `Segment`별 분류
- `builder.py` — §10 행/열 조립 + `derive_rule_diff()`
- `report.py` — 마크다운(Phase별 섹션) / 터미널 렌더러

## 실행

```bash
python examples/demo_impact_e2e.py            # E2E 관통 (LLM 호출 0회, 저장본 재생)
python examples/demo_impact_e2e.py --write    # docs/eval/impact_matrix_6_30.md 갱신
python -m pytest -k impact                    # 27개
```

## 합성 포트폴리오에 대한 정직한 표시

브리프 §0-8에 따라 실제 고객데이터를 쓰지 않으므로 포트폴리오는 **모의 데이터**다.
따라서 "총 한도 감소 1,549억원" 같은 수치는 **실제 시장 추정치가 아니라**
"이 조성의 포트폴리오에 확정 규칙을 적용하면 이렇게 된다"는 계산 결과다.
층화 비율(`P_HOUSE_COUNT` 등)은 통계가 아니라 명시된 가정이며, 시드와 함께
매트릭스의 `generated_from`에 기록돼 재현 가능하다.
