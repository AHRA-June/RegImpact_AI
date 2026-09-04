# RegImpact AI

> **금융 규제가 바뀌면, 무엇을 고쳐야 하는지 증명까지 함께 낸다.**
> Financial Regulation Impact & Assurance Platform

**🔗 [실행 화면 · 검증 산출물 보기](https://ahra-june.github.io/RegImpact_AI/)** — 서버·API 키 없이 열립니다.

---

주택담보대출 규제 변경(공문)을 읽어 **무엇이 달라졌는지** 추출하고, 그 변경이
**여신 룰 · 고객 영향 · 테스트케이스**로 어떻게 전파되는지 산출한 뒤,
**각 단계 산출물을 독립 기준과 대조**합니다.

**LLM 을 규제 판정에 쓰는 시스템이 아닙니다.** LLM 은 인용 근거가 붙은 **사실만** 추출하고,
판정은 사람이 확정한 명세를 구현한 **결정적 엔진**이 합니다. 그 경계 덕분에 엔진이
LLM 출력의 **검증 기준**이 될 수 있습니다. 반대 방향이면 순환입니다.

용도: 이직 포트폴리오 (금융권 Model Risk / 모델검증 / AI Governance / AI Assurance).

## 이 프로젝트에서 봐야 할 것

숫자가 좋은 것보다, **틀렸을 때 드러나는 구조**가 있는지가 요점입니다.

| | |
|---|---|
| **차등 검증** | 룰엔진 출력을 스스로 채점하지 않습니다. 명세를 **독립 재구현한 오라클**과 대조합니다(오라클은 엔진을 import 하지 않습니다) |
| **판별력(negative control)** | 정상 데이터의 100% 는 하니스가 둔감해도 나옵니다. 오류를 주입하고 지표가 실제로 떨어지는지 잽니다 |
| **추정 금지** | 원문에 값이 없는 구간을 메우지 않습니다. 대가로 커버리지에 상한이 생기고, 그 상한을 숨기지 않습니다 |
| **미측정 ≠ 통과** | 못 잰 지표는 통과로 세지 않습니다. 미등록 지역을 비규제로 흘리던 결함(R-01)이 같은 실패 양상이었습니다 |
| **자체 발견 결함 10건** | 검증보고서 §12 에 심각도·조치와 함께 기록돼 있습니다. **차등검증이 결함을 놓친 사례**도 포함입니다 |

## 검증 산출물

| | |
|---|---|
| [시스템 검증보고서](https://ahra-june.github.io/RegImpact_AI/validation_report.html) | 개념적 건전성 · 구현 정확성 · 성과 검증 · 거버넌스 · 한계 · 발견사항 |
| [Model & System Card](https://ahra-june.github.io/RegImpact_AI/model_system_card.html) | 사용 목적과 **범위 외 · 오용 방지** |
| [AI Risk Register](https://ahra-june.github.io/RegImpact_AI/ai_risk_register.html) | 리스크 18건 / 5범주 — 통제가 실재하는 코드를 가리키는지 테스트가 강제 |
| [판정 플레이그라운드](https://ahra-june.github.io/RegImpact_AI/playground.html) | 차주 조건을 바꾸면 즉시 판정 + **어느 규칙에서 멈췄는지** |

이 문서들은 **손으로 쓰지 않습니다.** 파이프라인을 실행하고 그 결과로 생성합니다 —
시스템이 바뀌면 문서도 바뀝니다.

## 실행 (LLM 호출 0회 · 0원)

```bash
pip install -e ".[dev]"

python -m pytest -q                          # 테스트 전량
python examples/demo_impact_e2e.py           # 파이프라인 11단계 관통
python examples/demo_discrimination.py       # 판별력 실측 (오류 주입 후 재측정)
python examples/build_validation_report.py   # 검증보고서 재생성
python tools/build_site.py                   # 사이트 빌드 → site/
```

기본 provider 가 `replay` 라 **실제 LLM 실행 기록을 재생**합니다. API 키 없이 같은 수치가 나옵니다.
유료 키 없이 실측하는 방법은 `docs/06_LLM_PROVIDER.md`.

## 구조

```
공문 원문 (해시 고정)
  → RegChange Extractor (LLM · 인용 필수)
  → Citation Assurance   (결정적 verbatim 대조)
  → Temporal Policy Resolver (직전 정책 대비 diff)
  → Rule Engine          (확정 명세의 결정적 구현)  ←→  TC Generator / 독립 오라클
  → Impact Matrix        (고객·업무영역 영향)
  → Rule Change Proposal (DRAFT → 엔진 교차검증 → 사람 승인)
  → Assurance Scorecard  (확정 임계와 대조 판정)
  → Audit Trail          (해시 체인)
```

| 모듈 | 역할 |
|---|---|
| `src/regimpact/rule_engine.py` | LTV 판정 — 확정 명세(§H)의 구현, 검증 기준점 |
| `src/regimpact/extractor/` | 공문 → 구조화 변경 사실 + 인용 검증 · 무과금 provider 레이어 |
| `src/regimpact/tc_generator/` | 독립 명세 오라클 · 차등 검증 |
| `src/regimpact/policy/` | 정책 버전 DB + 시점 해석 · 기준선 드리프트 탐지 |
| `src/regimpact/proposal/` | 룰 변경안 조립 + 엔진 교차검증 |
| `src/regimpact/impact/` | 포트폴리오 영향 · 임팩트 매트릭스 |
| `src/regimpact/assurance/` | 임계값 · 스코어카드 |
| `src/regimpact/discrimination.py` | 판별력(negative control) |
| `src/regimpact/audit/` | 해시 체인 감사로그 |
| `src/regimpact/governance/` | Model/System Card · AI Risk Register |
| `src/regimpact/report/` | 검증보고서 생성 |
| `src/regimpact/ui/` | 화면 5종 · 문서 렌더러 · 랜딩 · 플레이그라운드 |

---

## 작업을 이어받는 경우 (새 세션 · 새 계정)

> ⚠️ 이 프로젝트는 개발 도중 Claude 계정이 교체됩니다.
> **모든 상태는 이 저장소 안에만** 존재합니다. 대화 메모리에 의존하지 마세요.
> 매 작업 종료 시 `docs/01_PROJECT_STATE.md` 를 갱신하고, **세션 종료 시 병합까지 끝냅니다**
> (병합하지 않은 브랜치는 다음 세션에게 존재하지 않는 것과 같습니다 — `docs/07_BRANCH_TRIAGE.md` §5).

**읽는 순서:**

1. **`docs/01_PROJECT_STATE.md`** — 지금 어디까지 왔는지, 다음 액션 (가장 먼저)
2. `docs/00_BRIEF.md` — 철학·범위·LOCKED 원칙 (정체성 문서, 원본 보존)
3. `docs/02_DECISION_LOG.md` — 결정과 그 이유
4. `docs/07_BRANCH_TRIAGE.md` — 브랜치 정리·이식 백로그
5. `docs/08_RELEASE_PLAN.md` — 배포 계획
6. `docs/03_OPEN_QUESTIONS.md` — ✍️ 사용자 확인 대기
7. `docs/05_RULE_SPEC.md` · `docs/regulatory_facts.md` — 규칙·사실의 단일 기준점
8. `docs/metrics_spec.md` · `docs/eval/VALIDATION_LIMITS.md` — 지표 정의와 그 한계

## 문서 지도

| 파일 | 역할 |
|---|---|
| `docs/00_BRIEF.md` | 브리프 v2 — 정체성·범위·LOCKED 원칙 (임의 수정 금지) |
| `docs/01_PROJECT_STATE.md` | **살아있는 상태판** — 현재 위치·다음 액션·블로커 |
| `docs/02_DECISION_LOG.md` | 의사결정 이력 |
| `docs/03_OPEN_QUESTIONS.md` | ✍️ 사용자 확인 대기 항목 |
| `docs/04_PLAN.md` | 실행 계획 |
| `docs/05_RULE_SPEC.md` | 룰엔진 명세 (LOCKED §4) |
| `docs/06_LLM_PROVIDER.md` | 무과금 실행 정책 (provider 표) |
| `docs/07_BRANCH_TRIAGE.md` | 브랜치 분류 + 이식 백로그 |
| `docs/08_RELEASE_PLAN.md` | 3일 배포 계획 |
| `docs/regulatory_facts.md` | 규제 사실 + 인용 (단일 기준점, C01~C16) |
| `docs/metrics_spec.md` | 지표 정의·분모·임계값 |
| `docs/eval/VALIDATION_LIMITS.md` | **검증의 한계** — "왜 계속 100%인가" |
| `docs/eval/gold/` | 골드 평가셋 115문항 (DEV 40 / 🔒LOCKED 40 / 🔒CHALLENGE 35) + 봉인 규율 |
| `docs/validation/` · `docs/governance/` | 생성된 검증보고서 · 카드 · 리스크 레지스터 |
| `docs/policies/` | 정책 버전 DB (git 이력이 곧 승인 기록) |
| `docs/sources/` | 공문 원본 스냅샷 + 추출 텍스트 + sha256 |
| `docs/business/` | 사업계획서 (별도 트랙) |

## 개발 브랜치

`claude/anthropic-api-key-issue-itk27f` → 기본 브랜치 `main`
