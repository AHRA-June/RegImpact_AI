# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 **이 파일부터** 읽는다.
> 규칙: "지금 어디 / 다음 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-18 (세션 종료 · 인계 정리)
- **개발 브랜치:** `claude/anthropic-api-key-issue-itk27f` (원격 푸시됨, PR 미생성)
- **전체 단계:** 🟢 **Phase 2 진행 중** — Walking Skeleton 관통 완료, 골드셋 구축·추출 튜닝 완료
- **테스트:** 217개 통과 · **비용: 0원** (유료 API 키 미사용)

---

## 다음 작업 (2026-08-19 기준)

✅ **R-01 지역 레지스트리 결함 해결** — 강남·서초·송파·용산이 비규제로 판정되던 문제.
   MOLIT p5 참고2 현황표에서 서울 25곳 + 경기 15곳 전량 이관(C16), 미등록 지역은 UNKNOWN →
   룰엔진 P0d 로 사람 검토. 곁가지로 **차등검증이 이 결함을 공유하고 있던 것**을 발견해 오라클도 정정.
   상세: `02_DECISION_LOG.md` 2026-08-19.

**다음**: `docs/07_BRANCH_TRIAGE.md` §4 순서대로 브랜치 이식.
   S-22 사업계획서(충돌 1곳) → S-16 플레이그라운드(파일 2개) → S-04 Rule Change Proposal →
   S-02 판별력(negative control) → S-03 감사로그 → S-05 정책 버전 DB.
   ✍️ `kus0w7`·`71qh9m`·`o2geks` 3개는 이식할 것이 없어 **삭제 승인만** 받으면 된다(PR #3 동반 종료).

## 🚀 새 세션 시작 절차 (2분)

```bash
python -m pytest -q                  # 217 passed 여야 한다
python examples/validate_goldset.py  # 골드셋 무결성 + 명세 정합 + 확정 지문
python examples/demo_impact_e2e.py   # E2E 10단계 전부 ✅ (LLM 호출 0회)
```

의존성은 **SessionStart 훅이 자동 설치**한다(`.claude/hooks/session-start.sh` — 웹 세션 한정).
수동으로 하려면 `pip install -e ".[dev]"`. 런타임 의존성은 없다(표준 라이브러리만).
UI 스크린샷 검증이 필요하면 `pip install -e ".[ui]"`(브라우저는 환경에 이미 있음).

세 개가 다 통과하면 환경이 정상이다. 전부 **LLM 호출 없이** 돌아간다(저장된 실행 기록 재생).
실제 LLM이 필요하면 `--provider cli`(Claude Code 구독, 유료 키 불필요) → `docs/06_LLM_PROVIDER.md`.

읽는 순서: **이 파일 → `00_BRIEF.md`(정체성·LOCKED) → `02_DECISION_LOG.md`(왜 그렇게 했는지)**.

---

## 지금 어디까지 왔나 — 컴포넌트별

| 컴포넌트 | 상태 | 진입점 | 실측 |
|---|---|---|---|
| **LLM Provider 레이어** | ✅ | `extractor/backends.py` | `cli`/`gemini`/`manual`/`replay`/`anthropic`. 무과금 우선 |
| **RegChange Extractor** | ✅ | `extractor/`, `examples/run_extractor.py --per-document` | Completeness **100%** · Exception Recall **100%** · Citation **100%** |
| **Deterministic 룰엔진** | ✅ | `rule_engine.py`, `05_RULE_SPEC.md` §H | 알고리즘 P0~P7 + P0c |
| **TC Generator · 회귀** | ✅ | `tc_generator/`, `examples/demo_tc_regression.py` | 34케이스 **Pass 100%** (독립 오라클) |
| **Impact Matrix** | ✅ | `impact/`, `examples/demo_impact_e2e.py` | 30행(코어 12+Discovery 18) · 코어 자동처리 67% |
| **고객 영향 분석** | ✅ | `impact/customer.py` | 심사 판정 **91.4%** / 영향 측정 **74.1%** |
| **UI 5화면** | ✅ | `ui/`, `examples/build_ui.py` | 자기완결 HTML, `docs/ui/generated/index.html` |
| **추출 골드** | ✅ **사람 확정** | `docs/eval/regchange_gold_6_30.json` | 16+4항목, 지문 `098cd126` |
| **QA 골드 115문항** | 🤖 초안 | `docs/eval/gold/`, `examples/run_goldset_eval.py` | DEV 40 / 🔒LOCKED 40 / 🔒CHALLENGE 35 |
| **QA 평가 하네스** | ✅ | `eval/qa.py` | DEV 실측: Fact 95.0% · Exact 92.5% · **Escalation Recall 100%** |
| **metrics_spec 임계값** | 🤖 제안 | `docs/metrics_spec.md` | TBD 1개만 남음(측정 불가한 것) |
| 검증보고서 | ⬜ 미착수 | — | Phase 3 |

---

## 다음 작업 (순서대로)

### 1. ✍️ metrics_spec 임계값 확정 — **사용자 판단 필요, 다른 작업의 전제**
- 파일: `docs/metrics_spec.md` §1·§2 (🤖 제안 상태, 근거 함께 기재)
- 요지: 임계는 **점수가 아니라 위험**에서 정했다. 예외·시행일·경과규정·escalation 누락 = 100%,
  Completeness 95% / Citation 98% / Escalation Precision 70%.
- 확정하면 표의 🤖를 ✅로 바꾸고 `02_DECISION_LOG.md`에 기록.

### 2. ✍️ QA 골드 DEV 40 검수
- 검수표 생성: `python tools/build_gold_review.py` (현재는 추출 골드만 다룸 → **DEV 40으로 확장 필요**)
- 확정되면 `tools/gold_dev.py`에서 `authored_by="human_confirmed"` 지정 후 재생성.
- 확정 후에야 QA 지표(Fact Coverage 95.0% 등)가 절대값이 된다. 지금은 상대 비교용.

### 3. Phase 3 — LOCKED / CHALLENGE 최초 실행
- **코어 완성 후 1회만.** 지금 열지 말 것(브리프 §12).
- 실행: `python examples/run_goldset_eval.py --split LOCKED --unseal-reason "..."`
  → 20자 이상 사유 필요, `docs/eval/gold/SEAL_ACCESS_LOG.md`에 기록됨.
- 결과가 나쁘더라도 **그 셋에 맞춰 재튜닝한 성능을 같은 '최종 성능'으로 재보고하지 않는다**(§12-7).

### 4. 검증보고서 15~20쪽 (Phase 3 코어 완성선)
- 재료는 이미 다 있다: `EXTRACTOR_RUN_REPORT.md`, `GOLDSET_EVAL_REPORT.md`,
  `impact_matrix_6_30.md`, `GOLD_REVIEW.md`, `02_DECISION_LOG.md`.
- 브리프 §12 한계 명시 문구를 반드시 포함(독립 벤치마크가 아님).

---

## ✍️ 사용자 결정 대기

| 항목 | 위치 | 영향 |
|---|---|---|
| metrics_spec 임계값 확정 | `metrics_spec.md` §1·§2 | 합격/불합격 판정 기준 |
| QA 골드 DEV 40 검수 | `docs/eval/gold/dev.json` | QA 지표의 절대값 신뢰도 |
| 非규제(수도권) 비처분 1주택 LTV | Q10 (해결됨·현행 유지 결정) | 원문에 없음 → escalation 유지 중 |

---

## ⚠️ 새 세션이 반드시 알아야 할 것 (비싸게 배운 것들)

1. **지표가 나쁘면 모델보다 측정기를 먼저 의심한다.** 이 프로젝트에서 두 번 겪었다 —
   "haiku 인용 환각 25%"(D-03)와 QA 첫 채점 실패 12건이 **전부 채점기 결함**이었다.
   원인은 PDF/HWP 추출본이 단어 중간에서 줄을 바꾼다는 것. → `EXTRACTOR_RUN_REPORT.md` §2
2. **FAQ Q2 표를 원문 텍스트에서 읽지 마라.** HWP→텍스트 변환에서 LTV 열과 DTI 열이 뭉개져
   40/50/60이 전부 LTV처럼 보인다. 확정값은 `05_RULE_SPEC` §C(사용자가 원본 이미지로 확정)뿐이다.
   골드가 이걸 어기면 `check_gold_against_spec()`이 잡는다.
3. **지표 통과는 채택 근거로 충분하지 않다.** 유사도 병합은 골드 100%를 받았는데 실제로는
   서로 다른 차주 유형·요건 임계값을 합치고 있었다. **무엇이 바뀌는지 직접 열어 봐야 한다.**
4. **분모를 조심하라.** "자동판정 불가 22.4%"도 "자동화율 50%→27%"도 분모가 잘못된 것이었다.
   개선했는데 지표가 나빠지면 분모를 먼저 본다.
5. **LOCKED/CHALLENGE는 코드가 막는다.** 사유 없이 열리지 않고 접근은 기록된다.
   구성만 볼 때는 `split_stats()`(정답 없이 개수·분포만).
6. **확정 골드를 손대면 지문이 어긋난다.** 재검수 요구가 뜬다. 그게 정상 동작이다.
7. **LOCKED §4:** 룰 값·도메인 정답은 LLM이 만들지 않는다. AI는 🤖 초안까지, 확정은 ✍️ 사람.

---

## 블로커 / 리스크

- **최대 리스크였던 "E2E 관통 실패"는 해소됨** (Phase 1 완료).
- 남은 리스크: 단일 정책(6·30) 코퍼스 — Temporal/Policy-version Consistency를 측정할 수 없다.
  정책 사례가 늘어야 그 계열 지표가 살아난다.
- **계정 교체 대비:** 모든 상태는 저장소에 있다. 대화 메모리에 의존하지 말 것.
- 골드셋 한계: 작성자=개발자이므로 독립 벤치마크가 아니다(브리프 §12, 보고서에 명시할 것).

---

## 작업 로그 (append-only, 최신이 위)

- **2026-08-18(4)** — 사업계획서 v1.2: **산출물 2층 구조** 반영 — 규제 층(전 기관 공통, 한 번 만들어 N번 재판매, 한계비용≈0)과 기관 층(룰 명세 온보딩, 락인) 분리. 표준 리포트 구독(Tier 1b, 연 300~500만원 저가·lead-gen) 신설, 플랫폼화를 기관 층 온보딩과 통합, 공통 리포트 복제·무단 유통 리스크 추가. 팀 전제 확정: 솔로프리너(코호트는 지분·고용 없는 피드백 그룹).

- **2026-08-18(3)** — 사업계획서 v1.1: 창업자 공수 실측치 반영(규제 1건당 3인×3일≈9인일, 관여 3명, 연 ~5건, 수작업 테스트 ~3일). 연 45인일 규모라 "공수 절감"만으로는 가격 정당화가 안 됨을 문서에 명시하고, 가치 근거를 시간 압축 대응+사고 예방+증빙으로 재정렬. §3.1 가격 근거 문구도 동기화.

- **2026-08-18(2)** — 📄 **사업계획서 v1 전면 재작성** (`docs/business/BUSINESS_PLAN_v1.md`, v0 보존). 명칭 **RegImpact AI**로 통일(Regulation+Impact, 사용자 확정 — "RegChange"는 컴포넌트명으로 강등). 6·30 사건 서사 도입부, 가치 제안을 구매자 언어("사고 예방+증빙")로, 쐐기 상품 "규제 1건 대응 패키지" 정의, 수익모델 단일 경로(건당 패키지→연간 약정→상시 구독) 커밋(3안 비교는 부록 C), Live Fire를 증거 전략으로 승격, 재무는 근거 병기 보수 추정, 창업자 1차 데이터 기입란(✍️) 신설. **후속 TODO:** ①✍️ 공수 수치 본인 기입 ②경쟁사 실명 데스크리서치 ③README·브리프의 영문 부제 RegImpact 통일 여부는 사용자 결정 대기.

- **2026-08-18** — 📄 **사업계획서 초안 v0 작성** (`docs/business/BUSINESS_PLAN_v0.md`). 사업화 멘토링용. PSST(정부지원사업) 형식, 수익모델 3안(B2B SaaS / 컨설팅+솔루션 / AI Assurance 검증) 병렬 제시, 전업 창업 전제. 미검증 가정은 `[가정]`/`[검증필요]` 명시, 멘토 질문 10개 포함. 기존 포트폴리오 트랙(브리프·LOCKED 원칙·구현 실적)은 변경 없이 승계.

- **2026-08-18 (14차 · 세션 종료)** — 📦 **인계 정리.** 상태판을 세션별 12개 블록에서
  **컴포넌트별 표 + 다음 작업 + 함정 목록**으로 재구성(362→216줄, append-only 로그는 보존).
  새 세션 시작 절차(3개 명령)와 `.claude/hooks/session-start.sh`(pytest 자동 설치, 웹 한정) 추가.
  `pyproject`에 `[build-system]`·`[project.optional-dependencies].ui` 추가 —
  editable 설치로 `import regimpact`가 어디서든 된다. 검수 산출물 파일명을 내용(v3)에 맞춰
  `GOLD_REVIEW.md`/`gold_review.html`로 정리. 테스트 217 유지.

- **2026-08-18 (13차)** — ✅ **추출 골드 v3 검수 완료.** 사용자가 20항목 전부 확인 → 전 항목
  `human_confirmed`. Extractor 지표가 확정 근거를 갖게 됐다. **확정 지문** 도입 —
  확정 이후 채점 관련 내용이 바뀌면 재검수를 요구한다(설명 문구 변경은 제외). metrics_spec
  임계값을 **위험 기준**으로 확정(🤖) — TBD 10여 개 → 1개(측정 불가한 것만 남김). 테스트 209→217.
- **2026-08-18 (12차)** — ✅ **골드 v3 측정 정비.** 23항목 검수 준비 중 각 entry의 채점 특이도를
  측정해 이중 측정·과잉 키워드·전이 미측정 세 문제를 고쳤다. `transition` 채점 신설(before/after
  직접 대조) — "70%가 어딘가 있다"와 "70%→40%로 바뀌었다"는 다른 주장이고 이 제품의 핵심은 후자다.
  엄격해진 뒤에도 100%/100%가 유지돼 기존 수치가 느슨함의 산물이 아님이 확인됐다.
  `dict.get` 기본값 조기 평가 버그도 발견·수정. 테스트 205→209.
- **2026-08-18 (11차)** — ✅ **골드 검수 1차 완료.** 사용자 판정: 충돌 3건 모두 "명세가 맞음".
  골드를 명세에 맞춰 정정하고 `human_confirmed`로 전환(최초 확정 항목). 3번은 값만이 아니라
  분류가 틀려 NO_CHANGE→EXCEPTION으로 재작성하고 함정 방향을 뒤집었다. 05_RULE_SPEC에
  재확인 기록을 남겨 같은 오독이 반복될 지점을 못박았다. 정정된 항목이 검사기에 다시 걸리던
  오탐도 수정 — 검수로 고친 것이 검사에 걸리면 사람을 되돌려 보낸다. 명세 대조 충돌 0건. 테스트 204→205.
- **2026-08-18 (10차)** — ✅ **골드 v2 검수 준비.** 추출 골드에 인용 추가(v2.1)해 검수 가능하게 만들고
  검수표(MD+HTML) 생성. **검수 준비 중 골드 결함 3건 발견** — FAQ HWP 표의 LTV/DTI 열이 텍스트
  추출에서 뭉개져 DTI 값을 LTV로 읽은 문항들. `check_gold_against_spec()`로 자동 검사화했고,
  첫 넓은 규칙이 오탐 10/13이라 관측된 결함 유형 2개만 잡도록 다시 만들었다(정밀도 3/3).
  테스트 194→204.
- **2026-08-18 (9차)** — ✅ **D-02 해결.** 추출 골드를 v2(19+4)로 확장하니 단일 패스 실성적이
  79%/50%로 드러났고(v1에서는 100%였다), 누락 4건 중 3건이 MOLIT에 몰려 있었다 → 문서 간
  그림자가 원인. `extract_per_document`(문서별 추출 + 캐시) + `merge_cross_document`로
  **100%/100%** 달성. **유사도 병합은 골드가 100%를 줬는데도 기각** — 실제 병합 내용을 열어 보니
  서로 다른 차주 유형·요건 임계값·경과규정이 합쳐지고 있었다(골드가 과병합에 둔감). 대신
  다른 문서 + 지문 일치 + 유사도 조건을 모두 만족할 때만 병합하고 `corroborations`로 인용 보존.
  Discovery 행 증가로 왜곡된 자동화율 분모도 코어 행으로 고정. 매트릭스·UI 재생성. 테스트 184→194.
- **2026-08-18 (8차)** — ✅ **골드셋 QA 평가 하네스 + DEV 베이스라인.** `eval/qa.py`(프롬프트·
  응답 검증기·결정적 채점기), `examples/run_goldset_eval.py`. DEV 40 실행 결과 정정 후
  Fact Coverage 95.0% / Exact 92.5% / Citation 100% / Escalation Recall 100%.
  **첫 채점의 실패 12건이 전부 채점기의 표현 차이였음을 답변 원문 대조로 확인**하고, 모델이 아니라
  채점기를 고쳤다(표면 정규화 + `|` 동의 표현, 양방향 회귀 테스트로 고정). 같은 원인으로
  **D-03(haiku 인용 환각 25%)을 철회** — 재채점 0%, 코어 모델 근거를 추출 완전성으로 교체.
  provider 레이어가 RegChange 스키마에 welded 돼 있던 결함도 수정(검증기 주입 가능).
  `docs/eval/GOLDSET_EVAL_REPORT.md` 신규. 테스트 158→184.
- **2026-08-18 (7차)** — ✅ **골드 평가셋 115문항 작성.** `src/regimpact/eval/`(schema·goldset·validate),
  `docs/eval/gold/`(dev 40 / locked 40 / challenge 35 + README + SEAL_ACCESS_LOG),
  `tools/gold_*.py`(작성 도구), `examples/validate_goldset.py`. 튜닝 전에 세 셋을 모두 작성해
  브리프 §12 순서를 지켰고, **봉인을 코드로 강제**(사유 없는 LOCKED/CHALLENGE 로드 거부 +
  append-only 접근 기록 + 정답 없이 구성만 보는 `split_stats()`). 인용은 `q()`가 원문에서 잘라 와
  verbatim을 보장하고, 검증기가 115문항 전체를 매번 원문 대조한다. DEV/LOCKED 분포 동일 고정.
  작성 직후 커버리지 집계로 봉인을 한 번 열었고 그 기록을 지우지 않은 채 API를 고쳤다. 테스트 129→158.
- **2026-08-18 (6차)** — ✅ **P0c 확정.** 사용자 도메인 검수 완료("시행 전에도 0% 맞다") →
  수도권 다주택 0%가 지역상태·시점·경과규정 무관임을 확정. `05_RULE_SPEC §C-2 보강`·§E P0c,
  `regulatory_facts` C06·C14 모두 🤖/🔺 → **✅확정** 전환. 코드는 이미 해당 규칙으로 동작 중이라
  변경 없음. **AI초안→사람확정 워크플로(LOCKED §4 운영방식)가 처음으로 한 바퀴 완주**했다.
- **2026-08-18 (5차)** — ✅ **Q10 확정.** 사용자 결정: 유주택자를 코어 스코프에 유지(실제 고객
  모집단에 존재), 기준값 없는 구간은 추정 없이 escalation 유지. 이 결정을 검증하려고 447건을
  열어 보니 **299건(66.9%)이 이미 판정된 건**이었다 — 규제지역 유주택은 시행일 0%로 확정되어
  심사가 된다. "자동판정 불가 22.4%"는 심사 불가와 변화량 미상을 한 통에 담은 잘못된 그림.
  `Segment.IMPACT_UNKNOWN` 신설, 지표를 `decision_coverage`(91.4%)/`impact_coverage`(74.1%)로
  분리. 진짜 판정 불가 7.4%(148건). `limit_*`가 미확정 LTV를 0원으로 대체하던 것도 `None`로 수정
  (허구 수치 방지). 매트릭스·UI 재생성. 테스트 124→129.
- **2026-08-18 (4차)** — ✅ **Q10 부분 해결.** 원문 재검토 결과 다주택 구간은 **이미 확정 사실(C06)이었고
  엔진이 범위를 좁게 구현**하고 있었다 — "규제지역 여부와 무관"인데 REGULATED 분기 안에서만 적용.
  `§E P0c` 신설(수도권 다주택 → 0%, 경과규정보다 앞), `regions.is_capital_area()`, 오라클 독립 재유도,
  TC 30→34. 시점 무관 근거 C14, 공백 확인 C15를 regulatory_facts에 신설. 자동판정 불가
  33.3%→22.4%(666→447). **변이 테스트가 "P0c 순서 무관" 주석을 반증**해 정정(뒤로 옮기면 447→480,
  `GF-MULTI-01`이 고정). 잔여 미결은 비처분 1주택 397건 — FAQ Q2 주1)이 열을 무주택 기준으로
  한정하므로 원문에 값이 없다. 추정 대신 escalation 유지, 자동화율 상한 78%를 명시. 테스트 119→124.
- **2026-08-18 (3차)** — ✅ **★ Stitch UI 하드코딩 → 엔진 실제 출력 교체.** `src/regimpact/ui/` 신규
  (theme: Stitch 토큰 verbatim + 정적 CSS 생성 / pages: 5개 화면, 리터럴 도메인 수치 금지 /
  site: 렌더·기록). `examples/build_ui.py` → `docs/ui/generated/`. **Stitch 재생성 대신 코드 생성**
  채택(재생성은 데이터 변경 때마다 재환각). **UI grounding 테스트** 신설 — Citation Assurance가
  인용을 원문에 대조하듯 화면 값을 엔진 출력에 대조하고, 2026-08-10 사고(환각 지역명/60%→50%/
  부등호 반전)를 회귀로 고정. Rule 화면 LTV는 양방향 검사(단방향은 하드코딩을 통과시킴 — 변이로 확인).
  **자기완결 HTML**로 전환(CDN JIT·아이콘 폰트 제거 → 정적 CSS 인라인 + 인라인 SVG), 오프라인
  스크린샷으로 검증. 포트폴리오 대조군 지역을 SEJONG→CHEONGJU로 변경(환각 금지어와 충돌 회피).
  `stitch_review.md`에 해결 배너 추가(사고 기록은 보존). 테스트 96→119.
- **2026-08-18 (2차)** — ✅ **★ Impact Matrix E2E 관통 (Phase 1 Walking Skeleton 완료).**
  `src/regimpact/impact/` 신규 — `portfolio`(층화 합성 2,000건, 비율을 상수로 노출·시드 고정),
  `customer`(같은 신청건을 6.30/7.1 두 시점으로 룰엔진 평가 → 6개 세그먼트 분류),
  `builder`(§10 행/열 조립, 수치는 전부 실제 컴포넌트 출력에서), `report`(Phase별 마크다운/텍스트).
  `demo_impact_e2e.py`가 브리프 §18 10단계를 전부 ✅ 관통(LLM 호출 0회, 0원).
  매트릭스 16행 — Phase 3축 유지, 자동처리 50%, Human Review 8행(전부 사유 명시),
  Discovery 4행은 표시만 하고 코어 룰엔진 미포함(§24-12). 고객영향: 한도 감소 638건(31.9%),
  총 −1,549억원. **E2E가 명세 공백을 정량화**: 33.3%가 `OWNER_BASELINE_UNKNOWN`으로 자동판정 불가
  → Q10 신설(자동화율 상한 67% 구조적 고정). `ImpactRow`는 사유 없는 비자동 행을 생성 시 거부.
  산출물 `docs/eval/impact_matrix_6_30.md`. 테스트 66→94.
- **2026-08-18 (1차)** — ✅ **무과금 LLM provider 레이어 + Extractor 첫 실측.** 사용자 제약("Anthropic API 키 발급
  어려움, 프로젝트에 비용 지출 안 함")을 설계로 흡수: `backends.py`에 `cli`/`gemini`/`manual`/`replay`/
  `anthropic` provider 추가, `resolve_completion("auto")`가 무과금 경로를 우선. structured output 부재는
  JSON 정규화+스키마 검증+1회 교정 재시도로 대체. 6·30 공문 3건 **실제 LLM 실행**(0원) — sonnet-5
  Citation Correctness 100%/Unsupported 0%/Completeness 100%/Exception Recall 50%. 결함 3건 확인:
  D-01 지역 어휘 불일치(해결 — 결정적 별칭 테이블 `normalize_region_name`, 프롬프트에 코드 어휘 주는
  대안은 정답 누설이라 거부), D-02 예외 누락(미해결·Q9 등록, 앵커 과적합 방지 위해 튜닝 중단),
  D-03 haiku-4-5 인용 환각 25%(모델 선택=리스크 선택 실증). `docs/06_LLM_PROVIDER.md`,
  `docs/eval/EXTRACTOR_RUN_REPORT.md`, `docs/eval/runs/*.json` 신규. 테스트 39→66.
- **2026-08-10** — ✅ **TC Generator + Rule-Regression 구현.** `src/regimpact/tc_generator/`(oracle·generator·regression·README). 룰엔진을 **독립 명세 오라클**로 차등 검증(differential testing) — 엔진 출력을 스스로 채점하지 않고 명세(§H)에서 독립 유도한 challenger와 대조하여 회귀가 tautology가 되지 않게 함. 오라클은 rule_engine/regions/grandfathering 미import(구조적 독립). 30 케이스(6 카테고리) Pass Rate 100%. mutation test 2건으로 fixture 방어력 증명. 명세 내부 상충(§E vs §H, 유주택+생애최초) 발견 → `03_OPEN_QUESTIONS.md` Q8 신설. `examples/demo_tc_regression.py`. 테스트 11개(총 39) 통과.
- **2026-08-10** — ✅ **RegChange Extractor(E) + Citation Assurance(A) 구현.** `src/regimpact/extractor/`(structured output, LLM 주입 가능=오프라인 테스트, claude-opus-5 기본). Citation grounding으로 환각 인용 탐지 실측 + 골드 대조(Change Completeness/Exception Recall). 골드 `docs/eval/regchange_gold_6_30.json`. 테스트 5개(총 28) 통과. claude-api 스킬 참조. `examples/run_extractor.py` 추가.
- **2026-08-10** — ✅ **룰엔진 v1 구현·검증.** `src/regimpact/`(models·regions·grandfathering·rule_engine) + `tests/`(pytest 23 통과) + `examples/demo_6_30.py`. 알고리즘 H를 deterministic 코드로. LOCKED §4 준수(규칙값은 확정 명세에서). pyproject·gitignore·엔진 README 추가.
- **2026-08-10** — Stitch 1차 산출물(5화면) 수령·리뷰. 디자인 훌륭(Assurance·Rule변경안·임팩트매트릭스 서사 성공)하나 **도메인 데이터 환각**(지역을 세종/부산/강남으로, LTV 60→50 등). 정정 프롬프트 작성(`docs/ui/stitch_review.md`), export 보존(`docs/ui/stitch_export/`). → 재생성 또는 HTML 직접수정 필요.
- **2026-08-10** — UI 목업용 Google Stitch 프롬프트 작성(`docs/ui/stitch_prompts.md`, 5개 화면: 분석 워크스페이스/임팩트매트릭스/Rule변경안+검토/Assurance/고객영향). 구현은 Streamlit 수준 유지, Stitch는 포트폴리오·참고 디자인용.
- **2026-08-10** — ✅ **룰 명세 v1 확정.** 사용자 "다 OK, 정책대출은 Discovery로". precedence·경과규정·알고리즘 lock, 정책대출 Discovery 분리, 코어=LTV만. `05_RULE_SPEC` 전체 ✅ 전환. **다음 세션/단계: 엔진 코드+테스트 구현(Phase 1 Walking Skeleton).**
- **2026-08-10** — 예외 우선순위(E, P0~P8) + 경과규정(F, G1~G3) + 통합 판정 알고리즘(H, pseudocode) 🤖초안 작성. reason_codes(D) 확정 목록화. 입력 스키마에 real_demand_flag/policy_product/land_permit 등 추가. → ✍️ 사용자 확정 대기 후 엔진 코드화.
- **2026-08-10** — 사용자 제공 FAQ Q2 이미지로 LTV 표 재설정: DTI(투기과열40/조정50) + 최대한도(가격구간별) 추가, `regulated_type` 필드 신설, 기준선 "수도권외"→"非규제 수도권" 정정, 보금자리 비아파트55%/DTI50% 반영. 05_RULE_SPEC C표·regulatory_facts 갱신. (DTI/한도 코어 포함 여부 ✍️ 대기)
- **2026-08-10** — 공문 3건(FSC·MOLIT 보도참고자료 PDF, 관계기관 FAQ HWP) Source Snapshot 저장(해시)+원문 추출(pymupdf/olefile). 룰 LTV 초안 자동 채움(05_RULE_SPEC C표), regulatory_facts에 원문 반영 및 브리프 교정 7건(🔺 생애최초70/서민60/유주택0/토허제7.5 등). LOCKED §4 운영방식("AI초안→사람확정") DECISION_LOG 기록(사용자 확인 대기).
- **2026-08-10** — 룰엔진 규칙 명세 착수: `05_RULE_SPEC.md` 스캐폴드(스키마·의사결정표 구조·경과규정 뼈대) 생성·커밋. LOCKED §4에 따라 ✍️ 도메인 값은 사용자 입력 대기.
- **2026-08-10** — Q3 해결: 주차 계획 수직 슬라이스 우선 재배열 + 총 9~10주 확정. `04_PLAN.md` 신규, DECISION_LOG·OPEN_QUESTIONS·README·STATE 반영, 로컬 커밋.
- **2026-08-10** — Q1 해결: 골드셋 100~120 확정(split DEV40/LOCKED40/CHALLENGE35, CHALLENGE 가중). DECISION_LOG·OPEN_QUESTIONS·metrics_spec·STATE 반영, 로컬 커밋.
- **2026-08-10** — Q2 해결: Assurance 체크 "수를 줄임" 결정(깊은 4 dimension + 로드맵/인프라). DECISION_LOG·OPEN_QUESTIONS·metrics_spec 반영, 로컬 커밋. (원격 push는 권한 대기)
- **2026-08-10** — 브리프 v2 검토, 분석 피드백 제공, handoff 문서 구조 생성·커밋. (기획 단계)
