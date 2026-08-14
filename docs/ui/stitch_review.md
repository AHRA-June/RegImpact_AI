# Stitch 1차 산출물 리뷰 + 데이터 정정 프롬프트 (2026-08-10)

> **✅ 2026-08-14 업데이트 — 5개 화면 전부 엔진/평가 산출물로 대체됨.**
> 아래 화면별 데이터 정정은 더 이상 손으로 고칠 필요가 없다. `docs/ui/generated/`의 생성 HTML이
> Stitch 목업(`_1`·`_2`·`rule`·`assurance`·`_3`)을 대체한다. `python examples/render_ui.py`로 재생성.
> Stitch export는 **디자인 참고**로 보존.
>
> | 목업 | 생성 화면 | 데이터 소스 |
> |---|---|---|
> | `_2` | `regulatory_analysis.html` | RegChange gold + SOURCES + 엔진 상수 |
> | `_1` | `impact_matrix.html` | `build_impact_matrix()` |
> | `rule` | `rule_amendment.html` | rule_engine 상수·regions·경과규정·Impact Matrix |
> | `assurance` | `assurance.html` | tc 회귀(실측) + LLM 지표 '실측 대기' |
> | `_3` | `portfolio_impact.html` | 합성 포트폴리오 × rule_engine |
>
> 렌더 레이어: `src/regimpact/ui/`. 생성 화면은 **외부 CDN·웹폰트 의존 없이 오프라인 자립**
> (Tailwind 빌드 인라인 + 서브셋 아이콘 폰트 임베드). 자세한 내용은 `docs/ui/generated/README.md`.

> Stitch에서 5개 화면 생성 완료. 디자인 시스템(DESIGN.md)은 마스터 컨텍스트를 잘 반영(Institutional Navy, Noto Sans, JetBrains Mono, 상태색, 고밀도).
> **문제: Stitch가 도메인 데이터를 화면마다 다르게 환각.** 아래 정정 프롬프트로 재생성하거나 HTML 직접 수정.

## 화면별 상태

| 화면(폴더) | 디자인 | 데이터 | 조치 |
|---|---|---|---|
| 핵심 변경 분석 (`_2`) | 좋음 | ✅ 정확(화성·용인·동탄·구리, 70→40, 6.30) | 스크린샷 파일 깨짐 → 재출력 |
| 검증 Assurance (`assurance`) | 훌륭 | ✅ 스펙 일치 | 없음 |
| Rule 변경안 (`rule`) | 훌륭 | ⚠️ LTV 맞음 / 지역 틀림(세종·부산) / 경과규정 부등호 반대 | 정정 |
| 임팩트 매트릭스 (`_1`) | 훌륭 | ❌ LTV 60→50 (틀림) | 정정 |
| 고객·포트폴리오 영향 (`_3`) | 좋음 | ❌ 지역 강남·부산·분당 / Normal 60→40 / 분포차트 깨짐 | 정정 |

## ⭐ 데이터 정정 리파인 프롬프트 (모든 화면 공통 — Stitch에 붙여넣기)

```
[중요] 이 앱의 유일한 시나리오는 "2026-06-30 규제지역 추가 지정"이다.
아래 확정 사실만 사용하고, 다른 지역명·수치를 임의로 생성하지 마라.

■ 신규 규제지역 = 딱 3곳:
  구리시(GURI), 용인시 기흥구(YONGIN_GIHEUNG), 화성시 동탄(HWASEONG_DONGTAN)
  ※ 세종/부산 해운대/강남/서초/분당 등 다른 지역명 절대 금지.

■ 규제지역 주택구입목적 주담대 LTV(무주택 기준):
  표준(일반): 70% → 40%
  생애최초:   70% → 70% (좌동, 변화 없음)
  서민·실수요자: 70% → 60%
  유주택(비처분 1주택 이상): → 0%
  다주택(수도권): → 0%
  ※ "60%→50%", "60%→40%" 같은 값 금지. 표준 변경은 반드시 70%→40%.

■ 날짜:
  시행일 2026-07-01 / 경과규정 컷오프 2026-06-30
  경과규정 = 2026-06-30 "까지"(<=) 접수 또는 계약+계약금 → 종전규정(70%) 적용.
  ※ 부등호 방향: applicationDate <= "2026-06-30" (>= 아님).

■ 식별자:
  rule_id = MORTGAGE_LTV_REGULATED_REGION
  reason_code 예: LTV_REGULATED_40, EXCEPTION_FIRST_HOME, EXCEPTION_REAL_DEMAND,
                  LTV_OWNER_0, LTV_MULTI_HOME_0, GRANDFATHERED_ACCEPTED_OR_CONTRACT

■ Impacted Segments 표 정정 예시(이 데이터로 교체):
  | 지역 | 차주유형 | 기존 LTV | 변경 LTV | 경과규정 | reason_code |
  | 구리 | 다주택 | 70% | 0% | 미해당 | LTV_MULTI_HOME_0 |
  | 화성 동탄 | 생애최초 | 70% | 70% | 미해당 | EXCEPTION_FIRST_HOME |
  | 용인 기흥 | 무주택 일반 | 70% | 40% | 미해당 | LTV_REGULATED_40 |
  | 구리 | 서민·실수요 | 70% | 60% | 미해당 | EXCEPTION_REAL_DEMAND |
  | 화성 동탄 | 무주택 일반 | 70% | 70% | 해당(종전유지) | GRANDFATHERED_ACCEPTED_OR_CONTRACT |
```

## 화면별 추가 지시(렌더 버그)
- **임팩트 매트릭스(_1):** 첫 행 "60% → 50% 하향조정"을 "70% → 40% 하향조정"으로. 근거칩은 [FAQ Q2].
- **Rule 변경안(rule):** AFTER 코드의 `regulatedRegions = [..., "SEJONG", "BUSAN_HAEUNDAE"]`를
  `["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"]`로. 경과규정 라인 `applicationDate >= "2026-06-30"` → `<= "2026-06-30"`.
  영향분석 요약의 "(세종, 부산 해운대)" → "(구리, 용인 기흥, 화성 동탄)".
- **고객영향(_3):** "Before/After LTV Distribution"을 산점도 말고 **그룹 막대차트**로:
  Before(70%) vs After(40%/0%) 두 그룹. Impacted Segments 지역을 위 표로 교체.
- **핵심 변경 분석(_2):** 내용은 정확하나 screen.png가 깨짐 → Stitch에서 재출력(re-export).

## 잘된 점(유지)
- Assurance 화면: 지표 카드·임계값·Escalation·"검증 기준 고정됨(v2.1)" 배지 = LOCKED TEST 개념까지 반영. 그대로.
- Rule 변경안: "LLM은 실행 코드를 직접 수정하지 않습니다" 배너 + 승인 스텝퍼 = 거버넌스 서사 완벽.
- 임팩트 매트릭스: Phase 탭 + Discovery 하단 분리 = 핵심 차별점 시각화 성공.
