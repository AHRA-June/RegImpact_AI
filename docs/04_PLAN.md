# 04 — PLAN (실행 계획: 수직 슬라이스 우선 재배열)

> 브리프 §18의 "레이어별 완성" 순서를 **"6·30 1건이 볼품없어도 먼저 E2E로 관통되게"**로 재배열한 실행 계획.
> 원본 §18은 `docs/00_BRIEF.md`에 보존되어 있고, 이 문서가 **현재 유효한 실행 순서**다.
>
> - 확정일: 2026-08-10 (Q3)
> - **총 기간: 9~10주** (코어 ~8주 + 스트레치 ~2주). 2026-08-10 결정. 브리프 원안(6+2=8주)에서 확장.
> - 근거: 최대 리스크는 "E2E 관통 실패". 각 레이어를 순차 완성하려다 관통 전에 시간이 끝나는 것을 방지. 기간 확장으로 심화 단계에 여유 확보.

---

## ⚠️ LOCKED §0-5 정합성 (반드시 읽을 것)

LOCKED §0-5: **"평가셋을 개발보다 먼저 만들고, DEV / LOCKED TEST / CHALLENGE를 분리한다."**

이 재배열은 §0-5를 **위반하지 않는다.** 정합성 근거:

1. **골드셋 설계·freeze는 여전히 실제 튜닝보다 먼저** 한다 (Phase 0~1에서 설계·앵커 작성, Phase 2 실제 extractor 튜닝 시작 전에 100~120 freeze 완료).
2. **Walking Skeleton(Phase 1)은 "성능 튜닝"이 아니라 "배관 연결 스모크 테스트"** 다.
   - 사용하는 데이터는 **6·30 수기 정답 앵커 1건**(어차피 §18-1주차에 먼저 작성)뿐.
   - 각 노드는 stub/하드코딩이어도 됨. 목표는 파이프라인이 끝까지 연결되는지 확인.
3. **LOCKED TEST / CHALLENGE는 마지막(Phase 3)까지 절대 열지 않는다.** 누수 방지 원칙(브리프 §12) 그대로.

> 만약 이 해석에 이견이 있으면(= 브리프 원문대로 골드셋 100~120 전체를 먼저 완성한 뒤에만 코드를 시작하고 싶으면) 사용자가 알려주면 원 순서로 되돌린다. 현재는 위 정합성 해석을 채택.

---

## 재배열된 계획

### Phase 0 — 기준선 (W1)
목표: 검증의 기준점(단일 진실)을 먼저 못박는다.
- `regulatory_facts.md` 확정 — 6·30 사실 claim 검수 (사용자 도메인 검토)
- `metrics_spec.md` 확정 — 깊은 4 dimension 지표 공식·임계·high-risk 정의
- **룰엔진 규칙 명세 v0** — 사용자 본인 작성 (LOCKED §4)
- **6·30 수기 Impact 정답(앵커)** — 사용자 확인 (§24-4). Walking Skeleton의 유일한 E2E 테스트 케이스.
- Temporal Policy / Region 최소 스키마

### Phase 1 — Walking Skeleton (W2~W3) ★핵심 리스크 해소 — **✅ 관통 완료 (2026-08-18)**
목표: **6·30 1건이 끝까지 관통.** 각 노드 stub 허용.
```
Source Snapshot(1건, 수동)
 → Policy Version(수동 입력)
 → Before/After(간이 또는 수동 추출)
 → Impact Matrix(1~2행)
 → Rule Change Proposal(고정 스키마 1개)
 → Test Cases(3개)
 → Deterministic Rule Engine(핵심 LTV 경로만)
 → Regression(앵커 대조)
 → Assurance 1개 체크(Citation/Source grounding)
 → Report stub
```
- 골드셋: **DEV 일부(약 20~30)** 만 먼저 작성해 튜닝 착수 가능하게. (전체 freeze는 Phase 2 초입)
- 산출: "관통되는 파이프라인" — 이후는 개선 게임.
- **✅ 달성:** `examples/demo_impact_e2e.py`가 10단계를 전부 관통. 다만 각 노드가 stub이 아니라
  실제 구현이다(룰엔진·Extractor·TC Generator·Impact Matrix 모두 정식 구현). 최대 리스크였던
  "E2E 관통 실패"는 해소됐고, 남은 것은 각 노드의 심화(Phase 2)와 명세 공백 해소(Q10).

### Phase 2 — 노드 심화 (W4~W6)
- **골드셋 100~120 완성 + DEV/LOCKED/CHALLENGE freeze** (split: DEV 40 / LOCKED 40 / CHALLENGE 35) — 실제 extractor 튜닝 전 완료.
- RegChange Extractor 정식 + Temporal Policy Resolver 정식
- Impact Analyzer + 고객영향 행 + 구조화 Rule Change Proposal 정식
- 층화 합성 포트폴리오 2,000~5,000 + TC Generator + Rule regression 정식

### Phase 3 — Assurance 심화 + 검증 (W7~W8) ★코어 완성선
- 깊은 4 dimension Assurance 정량 측정 (나머지는 로드맵/인프라, `metrics_spec.md`)
- **LOCKED TEST / CHALLENGE 최초 실행** (튜닝 종료 후 1회)
- 검증보고서 15~20쪽
- → 코어 완성 정의(브리프 §18) 충족

### W9~W10 — Stretch (브리프 §18 그대로, 밀리면 삭제 가능)
정책 버전 타임라인 / 최소 대시보드 / Model·System Card / AI Risk Register / 배포·README·데모·공개글 / Live Fire 준비.
(9주로 압축 시 W9 한 주에 최소 스트레치만, 10주면 W9~W10 활용.)

---

## 자르기 우선순위 (밀릴 때 — 브리프 §18 유지)
- **자를 것:** 화려한 UI, 대시보드 고도화, 웹 배포, 추가 정책 사례, Model/System Card 일부, 공개 글.
- **자르면 안 되는 것:** 평가셋 split, Temporal Policy Resolver, Rule Engine, Test Case Generator, Assurance Layer, 검증보고서.

## 코어 완성의 정의 (LOCKED, 브리프 §18)
6·30 시나리오 1건이 Source Snapshot → Policy Version Resolution → Before/After → Impact Matrix → Customer Impact → Structured Rule Proposal → Test Cases → Deterministic Rule Regression → Assurance Evaluation → Human Review → Validation Report 로 End-to-End 완결.
