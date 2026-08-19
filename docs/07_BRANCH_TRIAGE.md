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

## 1. ✅ P0 결함 — 해결됨 (2026-08-19)

`online-testing-plan-8k0xmx` 의 커밋 `a6e8262` 가 이렇게 말한다:

> fix(regions): 전국 241곳 지역 레지스트리 — **강남이 LTV 70%로 판정되던 오류 수정**

**재현됐고, 고쳤다.** 아래는 수정 전 상태 기록이다.

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

**해결 (2026-08-19)** — 8k0xmx 의 241곳을 이식하는 대신, 공문 원문에 답이 있었다.
MOLIT p5 **참고2 「투기과열지구 및 조정대상지역 현황」** 이 추가지정 前/後 전체 지정 현황을
지정일자까지 병기해 싣고 있어, 추정 없이 그대로 옮겼다 — 서울 25곳 + 경기 15곳.

구조도 함께 고쳤다. 미등록 지역은 이제 `NON_REGULATED` 가 아니라 **`UNKNOWN`** 이고
룰엔진 `P0d` 가 사람 검토로 보낸다. 비규제로 확인된 지역은 명시 등록한다.
전국 250여 시군구를 전부 넣을 수는 없으므로, 구조를 고치지 않으면 같은 결함이 재발한다.

곁가지로 더 큰 것이 나왔다 — **차등검증이 이 결함을 놓치고 있었다.** TC 생성기가
`SEOUL_GANGNAM` 을 "미등록 지역"의 예시로 쓰고 오라클도 같은 오해를 독립 재기입해서,
엔진과 오라클이 같은 실수를 공유한 채 일치율 100%가 나왔다. 상세는 `02_DECISION_LOG.md` 2026-08-19.

→ S-01 완료. 남은 이식 백로그는 §3.

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
| ~~S-01~~ | ~~지역 레지스트리 + UNKNOWN 에스컬레이션~~ | — | ✅ 2026-08-19 완료 (원문 참고2에서 직접 이관) |
| ~~S-02~~ | ~~판별력(negative control) + `VALIDATION_LIMITS.md`~~ | dq1gtz | ✅ 2026-08-19 완료 (문서는 main 실측으로 재작성) |
| S-03 | **해시 체인 감사로그 (audit trail)** | d2et38 | 변조 탐지. Model Risk 직무 포트폴리오에서 가장 직관적으로 먹히는 산출물 |
| ~~S-04~~ | ~~Rule Change Proposal (`proposal/`)~~ | sp37fd | ✅ 2026-08-19 완료 (실제 추출에 배선하며 빌더 결함 2건 수정) |
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
| S-16 | 인터랙티브 임팩트 플레이그라운드 | 5fow5g — ⚠ **단독 이식 불가**. 룰엔진 JS 재구현이 들어 있어 S-17의 포팅 대조 하네스와 묶어야 한다 |
| S-17 | Vercel 정적 배포 + Streamlit 검증 콘솔 | 8k0xmx |
| S-18 | 랜딩 허브 `docs/index.html` + `PORTFOLIO.md` + md→HTML 렌더러 | fmo0g8 |
| S-19 | PRD (as-built) | fmo0g8 · d2et38 |
| S-20 | `docs/features/` 기능단위 버전관리 체계 | d2et38 |
| S-21 | Ollama / OpenAI 호환 백엔드 (backends.py 확장) | sp37fd |

### 별도 트랙
| ~~S-22~~ | ~~사업계획서 v0/v1 (PSST)~~ | ✅ 2026-08-19 완료 (제품 명칭 RegImpact AI 통일 포함) |

---

## 4. 권장 순서

1. ~~**S-01** 지역 레지스트리~~ ✅ 완료
2. ~~**S-22** 사업계획서~~ ✅ 완료
3. ~~**S-04** Rule Change Proposal~~ ✅ 완료
4. ~~**S-02** 판별력~~ ✅ 완료 → **S-03 감사로그 → S-05 정책 버전 DB**
5. **S-16 + S-17** 은 묶어서 — 플레이그라운드의 JS 룰엔진은 `export_fixtures.py` +
   `verify_js_port.mjs` 대조 하네스 없이 들이면 하드코딩이 되살아난다
5. 티어 B는 검증보고서(S-06)를 축으로 필요한 것만
6. 각 항목 이식이 끝나면 **출처 브랜치 삭제**

`kus0w7` · `71qh9m` · `o2geks` 3개는 이식할 것이 없으므로 **지금 지워도 된다** (✍️ 승인 필요).
PR #3(`o2geks`)도 함께 닫으면 된다. PR #2(`sp37fd`)는 S-04·S-07·S-21 이식 후에 닫는다.

---

## 5. 이 정리가 남긴 교훈

브랜치 12개가 같은 것을 11번 다시 만든 이유는 하나다 — **세션마다 새 브랜치에서 시작했는데,
직전 세션의 결과가 기본 브랜치에 병합돼 있지 않았다.** 매번 08-10 시점에서 다시 출발한 셈이다.

앞으로는 **세션 종료 시 병합까지 끝낸다.** 병합하지 않은 브랜치는 다음 세션에게 존재하지 않는 것과 같다.
