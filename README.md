# RegImpact AI

> **생성형 AI 기반 주택담보대출 규제 변경 영향분석 · 검증 시스템**
> RegChange Impact & Assurance — 챗봇이 아니라 **검증 가능한 의사결정 지원 시스템**

정부의 가계대출 규제가 바뀌었을 때, 공식 공문에서 **무엇이 달라졌는지**를 AI가 초안하고,
그 변경이 **여신 룰 · 고객 영향 · 내규 · 테스트**로 어떻게 전파되는지를 **사람이 확정한 결정적
룰엔진** 위에서 산출하며, 모든 주장을 **검증 가능한(auditable) 방식으로 증명**한다.

> **"규제가 바뀌면 무엇을 고쳐야 하는지 AI가 제안하고, 그 제안이 틀리지 않았음을 검증 가능하게 증명한다."**

- **핵심 원칙:** LLM은 **초안**만. LTV 판정·규칙 값은 **사람이 확정한 명세**에서 온다(자동 규칙 생성 없음).
- **정직성:** 모르는 것(명세 여백)은 임의값 대신 **사람 검토로 표면화**. 근거 없는 인용은 **환각으로 탐지**.
- **용도:** 이직 포트폴리오 — 금융권 **Model Risk / 모델검증 / AI Governance / AI Assurance / AI Evaluation** 직무.

시나리오(seed): **2026-06-30 규제지역 추가 지정(구리·용인 기흥·화성 동탄)** = "6·30".

---

## 핵심 결과 (6·30 실측 — 모두 실제 파이프라인 출력, 하드코딩 없음)

| 영역 | 지표 | 결과 |
|---|---|---|
| **추출 신뢰(Assurance)** | Citation 정확도 · 환각률 | **100%** (12/12) · **0%** |
| | 변경 완전성 · 예외 재현율 | **100%** · **100%** |
| **룰엔진 검증** | 독립 오라클 차등검증 | **178/178 (100%)** + 몬테카를로 **5,000/5,000** |
| **고객 영향** | 가중 방향(강화·유지·검토) | **58% · 24% · 18%** (가중평균 Δ −20pp) |
| **영향 금액** | 1인당 대출 여력 | **7.08억 → 5.06억 (−28.6%)** · 민감도 밴드 [22.9%, 33.8%] |
| **룰 변경안** | 엔진 대조(반영·코어밖·검토·불일치) | **7 · 4 · 1 · 0** (승인 PENDING) |
| **내규 영향도** | 모의 내규 13건 매핑 | 수정필요 **9** · 검토 1 · 간접 1 · **무관 2**(과잉플래그 없음) |
| **스트레스** | 차등 퍼징 · 대규모 부하 | 5,000건 크래시 **0**·불일치 **0** / 50,000건 불일치 **0** |
| **품질** | 테스트 · 런타임 의존성 | **162 통과** · **0 (stdlib only)** |

> 견고성(정직한 한계): "여력 축소"는 가정 섭동에서 **100% 견고**(구조적), "강화 과반"은 85% 표본에서만
> 성립(모집단 가정에 취약) — 시스템이 **뒤집히는 경계까지 수치로** 보고한다.

---

## 이 프로젝트가 보여주는 역량

| 직무 역량 | 이 저장소에서의 근거 |
|---|---|
| **모델검증 / Model Risk** | 독립 명세 오라클 **차등검증**(자기채점 아님) · **mutation test** 방어력 · 위험차등 **임계값 정책(하드게이트)** · **error taxonomy(E1~E9)** · **검증보고서 5축** · **스트레스/역스트레스** |
| **AI Assurance / Evaluation** | Citation **grounding**(환각 탐지) · 층화 골드셋 **178건 + DEV/LOCKED/CHALLENGE 3분할** · 지표 **정의·분모·임계** 명세 · 측정 아티팩트 탐지·수정(채점기 결함 67%→100%) |
| **AI Governance** | **AI초안 → 사람확정**(승인 PENDING, 자동 반영 없음) · 명세 여백 **escalation** · **감사추적**(라이브파이어 증거: 원문 해시·timestamp·commit) · 한계·가정 **정직 표기** |
| **금융 도메인** | 주담대 **LTV 규제(6·30)** 룰엔진 · 경과규정·예외·지역 시점해석 · **여신 룰·내규 영향** 전파 |

---

## 바로 보기 (산출물)

브라우저에서 열면 됩니다 — 모든 값은 실제 엔진/추출 출력에서 주입(자체완결 HTML, 라이트/다크).

| 산출물 | 파일 | 내용 |
|---|---|---|
| **① 프론트도어(허브)** | [`docs/index.html`](docs/index.html) | 1분 요약 — 지표 타일 + 파이프라인 + 산출물 링크 |
| **② 임팩트 리포트** | [`docs/ui/report_6_30.html`](docs/ui/report_6_30.html) | 6·30 관통 리포트 + 차트 3종(임팩트·여력·민감도) + 내규 영향도 |
| **③ 시스템 검증보고서** | [`docs/validation/VALIDATION_REPORT.html`](docs/validation/VALIDATION_REPORT.html) | 독립 검증 5축 종합(~17쪽) — 조건부 적합 |
| **④ 라이브파이어 증거** | [`docs/livefire/rehearsal_6_30/`](docs/livefire/rehearsal_6_30/) | 발표 당일 처리용 증거 패키지(6·30 예행) |
| **⑤ 포트폴리오 커버** | [`docs/PORTFOLIO.md`](docs/PORTFOLIO.md) | 제출용 1~2쪽 요약(HTML: `docs/PORTFOLIO.html`) |

---

## 빠르게 실행 (의존성 0 — Python 표준 라이브러리만)

```bash
python -m pytest                       # 테스트 162개
python examples/gen_report.py          # 6·30 임팩트 리포트 재생성
python examples/gen_index.py           # 프론트도어 재생성

# 개별 데모(각 컴포넌트 관통)
python examples/demo_6_30.py           # 룰엔진 6·30
python examples/demo_tc_regression.py  # 독립 오라클 차등검증
python examples/demo_portfolio.py      # 층화 골드셋 178 + 3분할
python examples/demo_impact_matrix.py  # Impact Matrix
python examples/demo_exposure.py       # 여력 영향 금액
python examples/demo_sensitivity.py    # 민감도·견고성
python examples/demo_rule_catalog.py   # 내규 영향도 맵
python examples/demo_stress.py         # 스트레스 테스트
```

> Extractor 실측 재현만 LLM API 키가 필요합니다(`examples/run_extractor.py`, Google AI Studio).
> 그 외 전 파이프라인은 저장된 추출로 **오프라인 재현**됩니다.

---

## 아키텍처 한눈에

```
[AI 초안]           →   [사람이 확정한 결정적 규칙]   →   [검증층이 감시]
 Extractor              Rule Engine                   Assurance
"뭐가 바뀜?"            "그래서 LTV 얼마?"             "그 말 진짜야?"
```

**파이프라인:** 공문(해시) → 추출 → 인용검증 → 지역정규화 → 룰엔진(전/후) → 임팩트 매트릭스 →
여력 금액 → 민감도 → 룰 변경안 → **내규 영향도** → 리포트/증거.

처음 보신다면 **[`docs/06_WALKTHROUGH.md`](docs/06_WALKTHROUGH.md)**(사람 말 설명서)부터 읽으세요.

---

## 정직성 · 범위 (Non-goals)

- **초안화지 자동화 아님** — 여신 최종 결정은 사람 승인을 거친다(승인 상태 항상 PENDING).
- **단일 정책 seed(6·30)** — 성과 지표는 한 사건 기준(독립 3자 벤치마크 아님). 라이브파이어로 확대 준비됨.
- **합성 데이터** — 모집단 비중·담보가격은 **문서화된 가정**(실측 아님, LOCKED §8: 공개자료만 사용).
  절대 금액은 가정에 종속 — 민감도로 결론의 견고성을 정량화.
- **미확정 사실은 만들지 않는다** — 규제 원문 permalink 등은 임의 생성하지 않고 공란 유지(citation integrity).

---

## 문서 지도

| 파일 | 역할 |
|---|---|
| `docs/06_WALKTHROUGH.md` | **사람 말 설명서** — "이게 뭘 하는 시스템인지" (처음 보면 여기부터) |
| `docs/PORTFOLIO.md` | **포트폴리오 커버**(제출용 요약) |
| `docs/00_BRIEF.md` | 프로젝트 브리프 v2 — 정체성·범위·LOCKED 원칙 (원본 보존) |
| `docs/prd/PRD.md` | 정식 PRD(as-built) — 사용자·데이터·컴포넌트·평가·배포 |
| `docs/validation/VALIDATION_REPORT.md` | 시스템 검증보고서 — 5축 종합, 조건부 적합 |
| `docs/metrics_spec.md` | 평가지표 정의·분모·임계값·high-risk 정의 |
| `docs/regulatory_facts.md` | 6·30 규제 사실 + 인용 (단일 기준점) |
| `docs/05_RULE_SPEC.md` | 룰엔진 규칙 명세 (LOCKED §4) |
| `docs/eval/` | 골드 정답지 · 포트폴리오 매니페스트 · 실측 리포트(추출·여력·민감도·내규·스트레스) |
| `src/regimpact/` | 룰엔진 · Extractor · Impact · rule_proposal · rule_catalog · livefire · stress · report |
| `tests/` | 테스트 하네스 (pytest, 162개) |

---

## 개발 · 인계 노트 (기여자용)

> 이 프로젝트는 개발 도중 세션/계정이 교체됩니다. **모든 상태는 저장소 안에만** 존재합니다.
> 이어받을 때: `docs/06_WALKTHROUGH.md` → `docs/01_PROJECT_STATE.md`(살아있는 상태판) →
> `docs/02_DECISION_LOG.md` → `docs/03_OPEN_QUESTIONS.md` 순. 작업 종료 시 `01_PROJECT_STATE.md` 갱신이 규칙.
