# 07. 브랜치 정리 — 살릴 것 / 버릴 것

작성: 2026-08-18 · 상태: 🤖 분류 완료, ✍️ 사용자 결정 대기

---

## 0. 결론 먼저

원격 브랜치 12개가 **전부 2026-08-10 같은 지점에서 갈라져 나온 병렬 초안**이었다.
서로 병합할 수 있는 "기능 브랜치"가 아니라, **같은 프로젝트를 11번 다시 만든 것**에 가깝다.

- `impact/` 는 11개 중 **9개 브랜치**가 각자 다른 파일명으로 재구현
  (`analyzer.py` / `matrix.py` / `pipeline.py` / `customer_impact.py` / `segments.py` / `personas.py`)
- 골드셋도 4가지 레이아웃 (`eval/goldset.py`, `eval/gold_set.py`, `goldset/`, `eval/loader.py`)
- **자동 병합되는 브랜치는 하나도 없다** (아래 §2 충돌 표)

따라서 정리 방침은 **브랜치 병합이 아니라 기능 단위 이식**이다.
main(=`claude/portfolio-project-planning-9sip11`)에 PR #4가 병합되어 현재 가장 성숙한 기준선이 되었고,
나머지 브랜치에서는 **main에 없는 능력만** 뽑아온다.

**브랜치는 아직 하나도 삭제하지 않았다.** 이식이 끝난 브랜치부터 삭제한다.

---

## 1. 🔴 P0 — 먼저 확인해야 할 결함 1건

`online-testing-plan-8k0xmx` 의 커밋 `a6e8262` 가 이렇게 말한다:

> fix(regions): 전국 241곳 지역 레지스트리 — **강남이 LTV 70%로 판정되던 오류 수정**

**현재 main에서 재현된다.**

```
강남구 -> code=SEOUL_GANGNAM  status=NON_REGULATED
서초구 -> code=SEOUL_SEOCHO   status=NON_REGULATED
송파구 -> code=SEOUL_SONGPA   status=NON_REGULATED
용산구 -> code=SEOUL_YONGSAN  status=NON_REGULATED
구리시 -> code=GURI           status=REGULATED  ← 6·30 신규 지정분만 등록돼 있음
```

`REGION_VERSIONS` 에 **6·30으로 새로 지정된 3곳(구리·용인기흥·화성동탄)만** 들어 있다.
기존 규제지역(강남4구·용산 등)이 통째로 빠져 있어, 무주택 차주가 강남에서 LTV 70%를 받는다.

내가 지금 고치지 않은 이유: 어느 지역이 언제부터 어떤 유형으로 규제지역인지는
§4 룰 로직에 해당해서 **사람 확정이 필요한 규제 사실**이다. 추정으로 채우면 안 된다.

✍️ **내일 첫 작업**: 지역 레지스트리를 어느 범위까지 채울지 결정
 - (a) 6·30 시나리오에 필요한 최소 집합만 (강남4구·용산 + 6·30 신규 3곳)
 - (b) 8k0xmx 의 241곳 전국 레지스트리를 검수해서 이식
 - (c) 미등록 지역을 `NON_REGULATED` 로 조용히 처리하지 말고 **UNKNOWN 으로 에스컬레이션**

내 권장은 **(a) + (c)** 다. (c)가 본질이다 — 지금 구조는 "모르는 지역"과 "비규제 지역"을
구분하지 못해서, 데이터가 빠지면 조용히 관대한 판정을 내린다. 이건 규제 시스템에서 가장 나쁜 실패 방향이다.

---

## 2. 브랜치별 처분

| 브랜치 | 커밋 | 자동병합 | 처분 | 이유 |
|---|---|---|---|---|
| `work-in-progress-fmo0g8` | 26 | ❌ 48 | **살림(대)** | 이식할 기능이 가장 많음 |
| `work-in-progress-d2et38` | 19 | ❌ 32 | **살림(대)** | 감사로그·RAG·거버넌스 산출물 |
| `online-testing-plan-8k0xmx` | 12 | ❌ 45 | **살림(대)** | P0 결함 수정 + 정책 버전 DB + 배포 |
| `work-start-dq1gtz` | 7 | ❌ 21 | **살림(중)** | 판별력(negative control) |
| `work-start-sp37fd` (PR #2) | 7 | ❌ 31 | **살림(중)** | proposal/ · assurance/ |
| `workflow-progress-testing-5fow5g` | 6 | ❌ 1 | **살림(소)** | 인터랙티브 화면, 파일 2개뿐 |
| `business-plan-draft-e1daou` | 3 | ❌ 1 | **별도 유지** | 사업계획서 — 코드 트랙 무관 |
| `proceed-4ujipo` | 10 | ❌ 51 | **부분 살림** | 골드셋은 main이 더 성숙 |
| `regimpact-ai-project-kus0w7` | 14 | ❌ 78 | **버림** | 대부분 main에 더 성숙한 형태로 존재 |
| `start-work-71qh9m` (PR #1 closed) | 3 | ❌ 15 | **버림** | 후속 브랜치에 흡수됨 |
| `continue-session-o2geks` (PR #3) | 2 | ❌ 12 | **버림** | 71qh9m 의 확장판 |

---

## 3. 이식 백로그 — main에 **없는** 능력만

main 현재 보유: `extractor/`(backends·merge·postprocess·evaluate) · `impact/`(schema·portfolio·customer·builder·report)
· `ui/`(theme·pages·site) · `eval/`(schema·goldset·validate·qa·consistency·confirmation) · `regions` · `rule_engine` · `tc_generator`

없는 것 → 아래가 전부다.

### 티어 A — 이 프로젝트의 성격상 가장 값어치 있는 것

| # | 능력 | 출처 | 왜 |
|---|---|---|---|
| S-01 | **지역 레지스트리 + UNKNOWN 에스컬레이션** | 8k0xmx | §1의 P0 결함 |
| S-02 | **판별력(negative control) + `VALIDATION_LIMITS.md`** | dq1gtz | "왜 계속 100%인가"에 답하는 문서. 지표를 믿지 말라는 이 프로젝트의 핵심 태도와 정확히 같은 것 |
| S-03 | **해시 체인 감사로그 (audit trail)** | d2et38 | 변조 탐지. Model Risk 직무 포트폴리오에서 가장 직관적으로 먹히는 산출물 |
| S-04 | **Rule Change Proposal (`proposal/`)** | sp37fd (6개 브랜치에 존재) | main에 통째로 없다. 추출→영향→**"그래서 내규를 어떻게 고치나"** 의 마지막 칸 |
| S-05 | **Policy Version DB + Temporal Policy Resolver** | 8k0xmx | 정책의 시간축을 데이터로 관리 (§0-7 Phase 시간축 원칙과 직결) |

### 티어 B — 완성도·설득력

| # | 능력 | 출처 |
|---|---|---|
| S-06 | 검증보고서 15~20p (`docs/validation/`) — 4개 브랜치에 각각 버전 존재, 가장 나은 것 고를 것 | fmo0g8 / d2et38 / 4ujipo / dq1gtz |
| S-07 | Assurance 스코어카드 4 dimension + 임계값 | d2et38 · sp37fd |
| S-08 | Model/System Card + AI Risk Register | d2et38 |
| S-09 | 스트레스 테스트 (극단·경계·대량·적대적 입력) | fmo0g8 |
| S-10 | 내규 영향도 맵 (`rule_catalog`) | fmo0g8 |
| S-11 | 민감도(sensitivity)·익스포저(exposure) 분석 | fmo0g8 |
| S-12 | 라이브파이어 예행연습 + 증거 패키지 | fmo0g8 |
| S-13 | RAG/retrieval (BM25 + recall@k) | d2et38 |
| S-14 | 입력 무결성 게이트 (`validation.py`) | 8k0xmx |
| S-15 | TC Generator 조합 격자 3,200건 + Proposal→TC 연결 | d2et38 · sp37fd |

### 티어 C — 보여주기

| # | 능력 | 출처 |
|---|---|---|
| S-16 | 인터랙티브 임팩트 플레이그라운드 (`docs/ui/impact_playground.html`) | 5fow5g — 파일 2개, 즉시 이식 가능 |
| S-17 | Vercel 정적 배포 + Streamlit 검증 콘솔 | 8k0xmx |
| S-18 | 랜딩 허브 `docs/index.html` + `PORTFOLIO.md` + md→HTML 렌더러 | fmo0g8 |
| S-19 | PRD (as-built) | fmo0g8 · d2et38 |
| S-20 | `docs/features/` 기능단위 버전관리 체계 | d2et38 |
| S-21 | Ollama / OpenAI 호환 백엔드 (backends.py 확장) | sp37fd |

### 별도 트랙
| S-22 | 사업계획서 v0/v1 (PSST) | e1daou — 코드와 무관, 충돌은 `01_PROJECT_STATE.md` 한 곳뿐 |

---

## 4. 권장 순서

1. **S-01** 지역 레지스트리 (결함이라 먼저)
2. **S-22** 사업계획서 이식 (충돌 1곳, 5분)
3. **S-16** 플레이그라운드 (파일 2개)
4. **S-04 → S-02 → S-03 → S-05** 티어 A 나머지
5. 티어 B는 검증보고서(S-06)를 축으로 필요한 것만
6. 각 항목 이식이 끝나면 **출처 브랜치 삭제**

`kus0w7` · `71qh9m` · `o2geks` 3개는 이식할 것이 없으므로 **지금 지워도 된다** (✍️ 승인 필요).
PR #3(`o2geks`)도 함께 닫으면 된다. PR #2(`sp37fd`)는 S-04·S-07·S-21 이식 후에 닫는다.

---

## 5. 이 정리가 남긴 교훈

브랜치 12개가 같은 것을 11번 다시 만든 이유는 하나다 — **세션마다 새 브랜치에서 시작했는데,
직전 세션의 결과가 기본 브랜치에 병합돼 있지 않았다.** 매번 08-10 시점에서 다시 출발한 셈이다.

앞으로는 **세션 종료 시 병합까지 끝낸다.** 병합하지 않은 브랜치는 다음 세션에게 존재하지 않는 것과 같다.
