# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 **이 파일부터** 읽는다.
> 규칙: "지금 어디 / 다음 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-19 (고객용 화면 signal.html 신설 — Tomorrow Challenge 제안 화면)
- **개발 브랜치:** `claude/work-progress-jlg9hy`
- **전체 단계:** 🟢 **Phase 2 마무리 + 공모전 트랙** — 배포 완료, 남은 것은 QA 골드 검수와 Phase 3 진입
- **테스트:** 538개 통과(1 skipped) · **비용: 0원** (유료 API 키 미사용)

---

## 다음 작업 (2026-08-19 기준)

✅ **R-01 지역 레지스트리 결함 해결** — 강남·서초·송파·용산이 비규제로 판정되던 문제.
   MOLIT p5 참고2 현황표에서 서울 25곳 + 경기 15곳 전량 이관(C16), 미등록 지역은 UNKNOWN →
   룰엔진 P0d 로 사람 검토. 곁가지로 **차등검증이 이 결함을 공유하고 있던 것**을 발견해 오라클도 정정.
   상세: `02_DECISION_LOG.md` 2026-08-19.

✅ **S-22 사업계획서 트랙 이식** — v0/v1 + 제품 명칭 RegImpact AI 통일.

✅ **S-04 Rule Change Proposal 이식** — 추출 → 구조화 변경안(DRAFT) → 엔진 교차검증 →
   사람 승인. 실제 추출에 배선하면서 빌더 결함 2건을 잡았다(LTV 스칼라 덮어쓰기, 맨숫자 오파싱).
   E2E 관통 11단계로 확장.

✅ **S-02 판별력(negative control)** — `discrimination.py` + `docs/eval/VALIDATION_LIMITS.md`.
   dq1gtz 의 문서는 그 브랜치 수치라 그대로 못 쓰고, main 실측으로 다시 썼다.
   전 지표가 오염에 반응하지만 **간극이 지표마다 다르다** — 집계 비율은 단건 오류에
   둔감하다(인용 1건 환각 = 2pp). 항목 단위 검사가 실질 탐지력을 담당한다.

✅ **S-03 해시체인 감사로그** — `audit/` + E2E 11단계 배선. 이식하며 한계를 하나 명시했다 —
   해시 체인은 **끝에서 잘라낸 로그**를 혼자 구분하지 못한다(잘린 뒤에도 유효한 체인이다).
   `verify(expected_head=...)` 를 추가하고, head 해시를 로그 바깥에 남겨야 함을 문서화.

✅ **S-05 정책 버전 DB + Temporal Policy Resolver** — 브리프 §7의 질문("직전까지 유효했던
   정책과 무엇이 달라졌는가")을 구현. E2E 3단계가 이제 정책 타임라인·직전 정책·지역 전이를
   보여준다. 기준선과 정책 DB가 조용히 갈라지지 않도록 양방향 드리프트 검사를 신설했다.

→ **티어 A(S-01~S-05) 전량 완료.**

✅ **S-06 검증보고서** — `src/regimpact/report/` + `docs/validation/VALIDATION_REPORT.md`(602줄).
   구조는 fmo0g8(모델검증 관례), 방식은 dq1gtz(라이브 수치 조립), 수치는 main 실측.
   렌더러에 도메인 수치 리터럴이 없도록 **절 단위**로 검사한다 — 실측 절은 금지, 서술 절은
   과거 값 인용이 정상(§12 발견사항). 변이 테스트로 데이터 흐름 확인.

✅ **S-08 Model/System Card + AI Risk Register** — `src/regimpact/governance/`.
   리스크 판단(발생가능성·영향)은 사람이 `risk.py` 에 적고, 정량 수치는 검증보고서와 같은
   evidence 에서 온다. **통제가 실재하는 코드·테스트를 가리키도록 테스트가 강제한다** —
   "운영 중"이라 적고 근거가 없는 것이 리스크 레지스터가 무력해지는 가장 흔한 경로다.
   리스크 18건 / 5범주, 실제 발생 이력 5건 표시.

✅ **Day 1 배포** — `tools/build_site.py` 가 파이프라인 1회 실행으로 9쪽 정적 사이트를 굽는다
   (화면 5 + 문서 3 + 랜딩). md→HTML 렌더러(`ui/docrender.py`)와 랜딩(`ui/landing.py`) 신설.
   GitHub Actions 워크플로우가 **테스트 통과 후에만** 배포한다 — 깨진 수치를 올리지 않는다.
   Pages 활성화(Settings → Pages → Source = GitHub Actions)는 2026-08-19 완료.

✅ **Day 2 플레이그라운드 + JS 포팅 대조** — `tools/export_fixtures.py` 가 Python 엔진 판정을
   픽스처로 뽑고, `tools/verify_js_port.mjs` 가 판정 36건 + 지역×시점 450건을 대조한다.
   대조 실패 시 CI 가 배포를 막는다. 규칙 값은 JS 에 없다(픽스처에서 읽음) — 리터럴이 있으면
   대조가 실패한다. 화면은 값만이 아니라 **어느 규칙에서 멈췄는지(trace)** 를 보여준다.

✅ **Day 3** — S-07 Assurance 스코어카드(`assurance/`) + README 리크루터-first 재작성.
   임계는 `thresholds.py` 에 근거와 함께 등록하며 근거 없이는 코드가 거부한다.
   **미측정은 통과가 아니다** — JS 포팅 대조를 안 돌리면 NOT_MEASURED 로 남는다.
   metrics_spec 과 코드가 갈라지면 테스트가 실패한다.

✅ **브랜치 정리 완료** — `kus0w7`·`71qh9m`·`o2geks` 삭제, PR #3 종료. 삭제 전 재확인에서
   고유 기능 2건(고객용 내러티브 S-23, 타 provider 실측 기록 S-24)을 발견해 먼저 이식했다.
   처음 분류가 부분적으로 틀렸던 이유: merge-base 기준 diff 를 봐서 경로가 다른 고유 기능을
   놓쳤다 — main 현재 트리와 직접 비교해야 한다.

✅ **배포 완료 (2026-08-19)** — **https://ahra-june.github.io/RegImpact_AI/**
   푸시할 때마다 GitHub Actions 가 `build`(테스트 → 사이트 빌드 → JS 포팅 대조)와
   `mobile`(390px 가로 스크롤 검사)을 **병렬로** 돌리고, 둘 다 통과해야 배포된다.

### ⚠️ 배포 확인의 함정 세 가지 (전부 실제로 밟았다)

**① 라이브 URL 을 열 수 없다.** 이 실행 환경의 egress 프록시가 `github.io` 를 막는다
(curl·WebFetch 모두 403). "배포됐다"는 GitHub deployment status 로, "화면이 멀쩡하다"는
**같은 커밋을 로컬에서 렌더해** 확인한다 — 둘은 다른 증거다.

배포 상태는 반드시 `?environment=github-pages` 로 거른다. 그냥 최신 1건을 집으면 엉뚱한
환경이 잡힌다 — 실제로 Vercel Preview 주소를 라이브 URL 로 잘못 보고했다.
(그 Vercel 연동은 2026-08-19 프로젝트 삭제로 정리했다. **배포 경로는 GitHub Pages 하나뿐이다.**)

**② 뷰포트를 나눠서 재야 한다.** 데스크톱만 재고 "10쪽 전부 정상"이라 보고했는데
폰에서 화면 5종이 무너져 있었고 사용자가 발견했다. Stitch 목업이 데스크톱 전용이라
사이드바 288px 가 390px 화면에서 본문을 **102px** 로 만들고 있었다.
`scrollWidth` 비교로는 못 잡는다 — 그 값은 스크롤 컨테이너 안의 넓은 표에도 반응한다.
실제로 `window.scrollTo(900,0)` 하고 `scrollX` 가 0인지 봐야 한다.

    REGIMPACT_BROWSER_TESTS=1 python -m pytest tests/test_site.py -k horizontal

  로컬은 약 2분(샌드박스가 느리다), CI 는 30초. 기본 스위트에서는 빠져 있다.

**③ 브랜치를 기본 브랜치로 리셋하기 전에 미병합 커밋이 있는지 볼 것.**
`git checkout -B <branch> origin/<default>` 를 습관적으로 치다가 **커밋해 둔 문서 갱신을
두 번 날렸다.** 리셋 전에 확인한다:

    git log --oneline origin/claude/portfolio-project-planning-9sip11..HEAD

  비어 있지 않으면 먼저 PR 을 만들어 병합하거나, 리셋 대신 `git merge` 로 최신을 받는다.

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
| **QA 골드 115문항** | 🤖 초안(검수 4/40) | `docs/eval/gold/`, `examples/run_goldset_eval.py` | DEV 40 / 🔒LOCKED 40 / 🔒CHALLENGE 35 |
| **시점 질의 골드 TEMPORAL** | 🤖 초안 | `docs/eval/gold/temporal.json`, `eval/temporal.py` | 12문항 · resolver 정합 검사 통과 |
| **QA 평가 하네스** | ✅ | `eval/qa.py` | DEV 실측: Fact 95.0% · Exact 92.5% · **Escalation Recall 100%** |
| **metrics_spec 임계값** | ✅ **사람 확정** | `docs/metrics_spec.md` | 2026-08-19 확정 · TBD 1개(시점 골드 검수 후) |
| 검증보고서 | ✅ (S-06) | `report/`, `docs/validation/VALIDATION_REPORT.md` | 602줄, 라이브 수치 조립 |

---

## 다음 작업 (순서대로)

### ✅ metrics_spec 임계값 확정 — **완료 (2026-08-19 사용자)**
- 제안 전체 채택. Policy-version Consistency만 TBD 유지(시점 질의 골드 검수 후 측정 가동 +
  임계 별도 제안). 상세: `02_DECISION_LOG.md` 2026-08-19.

### 1. ✍️ QA 골드 DEV 40 검수 — **진행 중 4/40 (2026-08-19)**
- 검수표: `docs/eval/QA_GOLD_REVIEW.md` + `qa_gold_review.html` (`python tools/build_qa_review.py`로 재생성)
- ✅ 1차 완료: "인용만으로 확인 불가" 4문항(GF-007·REG-002·BOR-003·AMB-001) 사용자 확정 +
  인용 보강 2건. 상세: `02_DECISION_LOG.md` 2026-08-19. **잔여 36문항.**
- 다음 볼 것: 베이스라인이 놓친 앵커 2문항(EFF-001·EFF-002 — AMB-001은 확정됨),
  그다음 카테고리 순서대로.
- 확정되면 `tools/gold_dev.py`에서 `authored_by="human_confirmed"` 지정 후 재생성.
- 확정 후에야 QA 지표(Fact Coverage 95.0% 등)가 절대값이 된다. 지금은 상대 비교용.

### 2. ✍️ 시점 질의 골드 TEMPORAL 12문항 검수 — **신설 (2026-08-19 🤖)**
- 파일: `docs/eval/gold/temporal.json` (`tools/gold_temporal.py`로 재생성)
- Policy-version Consistency 가동용 별도 셋 — 115문항(DEV/LOCKED/CHALLENGE)과 분리, 비봉인.
- as_of 문항은 Temporal Policy Resolver 정합을 코드가 강제(`eval/temporal.py`).
  **escalation 2문항은 2020 6·17 해제일 미상의 한계를 새긴 것** — 해제 원문 확보·confirm() 시
  같은 검사가 갱신을 요구한다.
- 검수 완료 → 측정 가동 → 임계 제안(TBD 해소)의 순서.

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
| QA 골드 DEV 40 검수 (잔여 36) | `docs/eval/gold/dev.json` | QA 지표의 절대값 신뢰도 |
| 시점 질의 골드 TEMPORAL 12 검수 | `docs/eval/gold/temporal.json` | Policy-version Consistency 측정 가동 |
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

- **2026-08-19(고객용 화면)** — 📱 **내 한도 시그널 signal.html 신설** (Tomorrow Challenge 지원서
  `APPLY_TOMORROW_CHALLENGE_SUBMIT.md`의 4단 콘텐츠를 화면으로, 사용자 지시: 기존 화면 유지 +
  고객용 별도 구현·웹앱 호환). `ui/signal.py` — 모바일 우선 웹뷰형(데스크톱은 폰 프레임 + 제안
  요약 패널): ①영향 알림(시뮬레이션) ②변경 전/후 한도 비교(주택가격×LTV, 판정 경로 접이식)
  ③경과규정 체크(계약·계약금·접수일 → 종전 기준 유지 배지) ④근거 우선 Q&A(BM25 포팅본 +
  시점 필터, 원문 문단 verbatim — LLM 답변 생성은 PoC 배선 목표라고 화면에 명시). 근거 조문은
  추출 grounded 인용에서 규칙별 매핑(`_rule_quotes`, 패턴 실패 시 빌드 거부). 브라우저 실측:
  70%/5.6억→40%/3.2억(-2.4억), 경과규정 70% 유지, 다주택 0%, 생애최초 70%+인용, 390px 가로
  스크롤 0. 신한·슈퍼SOL 로고·UI 는 흉내 내지 않음(텍스트 맥락만). 테스트 3건 신설(검증된
  포팅본 강제 · 인용 verbatim · 고객 대상 정직성). 랜딩에 CTA. 테스트 535→538.

- **2026-08-19(시연 모드)** — 🎬 **demo.html 신설** (신한퓨처스랩 지원 시연동영상용, 사용자 지시:
  고도화 중단·시연 화면 우선). `ui/demo.py` — 사이드바 없는 풀스크린 7막 무대(훅 → 원문 등록 →
  AI 추출 → 룰 변경안 70→40 플립 → **라이브 판정** → 포트폴리오 영향 → 검증 성적표+CTA).
  녹화 모드(자동 재생·전체화면·진행바)와 라이브 시연(←/→·장면 클릭) 겸용, 390px 반응형(가로
  스크롤 0 실측). 라이브 판정은 플레이그라운드와 **같은 검증된 JS 엔진 포팅본** — 발표일 70% /
  시행일 40% / 경과규정 70% / 미등록 지역 '사람 검토'를 브라우저 실측으로 확인. 수치는 전부
  evidence·픽스처에서 오고(스코어카드 미측정·합성 데이터 명시 포함 — 피치라고 숨기지 않는다),
  테스트 4건이 grounding·엔진 재사용·한계 표기·조작 장치를 고정. 랜딩에 "▶ 시연 모드" CTA.
  '이 페이지는?' 설명은 ℹ 오버레이로 유지(무대 오염 방지). 테스트 530→535.

- **2026-08-19(임계 확정 + 시점 골드)** — ✍️ **metrics_spec 임계값 확정**(사용자: 제안 전체 채택,
  🤖→✅ 전환, Policy-version Consistency만 TBD 유지) + 🤖 **시점 질의 골드 TEMPORAL 12문항 신설**
  (`tools/gold_temporal.py` → `temporal.json`, 115문항과 별도·비봉인). 새 장치: GoldItem `as_of`
  필드 + `eval/temporal.py` — as_of 문항은 Temporal Policy Resolver와 정합해야 하고, escalation
  문항(해제일 미상 2건)은 **해제 원문 확보로 DB가 답할 수 있게 되면 검사가 갱신을 요구**한다.
  곁가지: KNOWN_POLICY_VERSIONS 손 목록 → 정책 DB 유도, 골드 인용 대조를 코퍼스 7건 전체로,
  "단일 정책이라 측정 불가" 문구를 실상(골드 초안이라 검수 대기)으로 정정. 검증보고서·거버넌스
  문서 재생성(추적본이 §3.1 스코어카드 절 이전 버전이었던 것도 이번에 정합화). 테스트 521→530.
  **다음: TEMPORAL 12 + DEV 잔여 36 검수(✍️) → Policy-version Consistency 측정 가동 → 임계 제안.**

- **2026-08-19(지역 이관 확정)** — ✍️ **2020 6·17 검수 확정 반영** (사용자: Q1-A·Q2-A·Q3-A 전부 채택).
  레지스트리 코드 11개 신설 + 동명 구 별칭 결함 수정('대전 중구'→DAEJEON_JUNG, 맨 '중구'는 서울 유지).
  `MOLIT_20200617` deltas 21개 코드(수원·안양 구 단위 전개) + 조정대상 범위 rule_note(원문 verbatim).
  **DRAFT 유지** — 해제일이 원문에 없으므로(effective_to=None) 해제 보도자료 확보 후 confirm().
  신설 코드는 버전 구간 없이 UNKNOWN(사람 검토)이 정직한 상태. 수도권 7곳 CAPITAL_AREA 등록.
  그래프: DRAFT 지정 "(초안)" 표시, 집계는 확정만. 검수표는 확정 기록으로 전환. 테스트 518→521.
  **대기: 해제 보도자료 원문(2022~2023 국토부) — 확보 시 구간 닫고 확정, 시점 질의 골드도 그때 함께.**

- **2026-08-19(지역 이관 초안)** — 🤖 **2020 6·17 지역 이관 검수표** (`tools/build_region_review_2020.py`
  → `docs/policies/REGION_REVIEW_20200617.md` + HTML). 신규 투기과열 17곳(경기10+인천3+대전4,
  본문 서술과 개수 교차 일치) 매핑 초안: 기존 코드 5 · 신규 코드 제안 9 · 부분/경계 결정 3.
  조정대상지역은 원문이 "全 지역-제외" 방식이라 **열거를 지어내지 않고** 원문 그대로 보존(Q1).
  구조 질문 3개(조정대상 기록 방식 / 레지스트리 확장 범위 / **해제 이력 없는 확정 불가** — 해제
  원문 확보 전 DRAFT 유지 권고). 곁가지 결함 발견: 별칭 테이블이 '대전 중구'를 SEOUL_JUNG 으로
  오매핑(수도권 전제의 동명 구 문제) — 확장 시 함께 수정. 인용 전건 verbatim 대조 통과. ✍️ 검수 대기.

- **2026-08-19(코퍼스 확장)** — 📚 **과거 정책 원문 4건 편입** (사용자 제공: 2025 10·15 대책 2건,
  2020 6·17 대책 2건). `tools/ingest_source.py` 신설 — 해시 봉인 → SOURCES.md → 추출을 한 명령으로.
  코퍼스 2층 분리(`SOURCE_FILES` 3건 불변 / `CORPUS_FILES` 7건). 정책 DB: MOLIT_20251016 원문 연결
  (시행일 10.16 교차 일치 확인), **MOLIT_20200617 DRAFT 신규**(효력 6.19 원문 명시, 지역 이관 ✍️ 대기).
  **핵심 발견: 코퍼스 확장 → recall@5 82%→53% 급락** — 대책마다 거의 같은 문구의 FAQ 가 시점만
  다르게 재등장(2025↔2026). **시점 필터(doc_ids)로 82% 회복** — 검색 화면에 시점 칩 추가, 세 방식
  수치를 나란히(떨어진 수치 숨기면 과장 — 테스트 강제). 상세: `02_DECISION_LOG.md`. 테스트 513→518.
  **다음: 2020 지역 이관 검수(✍️) · 시점 질의 골드 초안 · 2016/2017 원문 대기.**

- **2026-08-19(페이지 설명)** — 💬 **전 페이지 상단 '이 페이지는?' 밴드** (사용자 리뷰: 뭘 가지고
  어떻게 만든 건지 안 보인다). `theme.explainer()` — 비전공자용 3문답(무엇을 보는 화면인가 /
  무엇으로 만들었나 / 어떻게 보나)을 랜딩 제외 13쪽 전부에 달았다. glance(결과 요약)와 역할 분리:
  explainer 는 기능·재료 설명. 문서 3종은 `markdown_to_html(intro_html=)` 로 전달.
  `test_every_page_explains_itself_to_non_experts` 가 재발을 막는다. 테스트 513, 13쪽 전부
  390px 가로 스크롤 0 재실측.

- **2026-08-19(그래프+검색)** — 🧠 **지식그래프 + BM25 검색 편입** (사용자 결정: LLM·RAG류 기능
  부재 아쉬움 → A·B 동시 진행, 상세는 `02_DECISION_LOG.md`). ① `graph/` — 정책 DB·룰 diff·
  고객 영향 실측·룰 회귀에서 **결정적으로 조립**한 31노드/49엣지, provenance 없는 엣지는 생성
  거부. graph.html 레이어드 DAG(노드 클릭 → 양방향 도달 경로 강조 + 출처 패널). ② `retrieval/` —
  청킹(위치 보존) + BM25(한글 2-gram, stdlib) + 지역 별칭 확장(D-01 재사용). **recall@5 82% /
  @10 89% 실측**(DEV 인용 45건 기준), 미적중 5건 화면 표기. search.html 은 브라우저에서 실제
  검색 실행 — JS 포팅본은 80프로브 대조 후에만 배포(`verify_search_port.mjs`). S-13 검색 절반
  완료. **대기: 과거 정책 원문(사용자 수집 중) 확보 시 코퍼스 확장 → 전체문맥 vs RAG 비교 평가 +
  시점 질의.** 테스트 489→512.

- **2026-08-19(검증 요약)** — 📄 **검증 요약 1페이지 신설** (`ui/summary.py` → validation_summary.html,
  사용자 요청: "검증보고서가 너무 길다"). 구성: 종합 판정 → 목적·목표·방법 → 파이프라인 한 줄 →
  검증 점수(스코어카드 12지표를 **확정 임계와 대조**해 표로, 미측정은 통과로 치지 않음) →
  고객 영향도(스탯 4 + 세그먼트 분포 바 + 한글 설명) → **작동하는 것/부족한 것 2단**(한계를
  점수와 같은 비중으로 — 좋은 것만 추리면 요약이 곧 과장) → 전문 링크. 수치는 전부 evidence 에서
  오고 QA 검수 진행률(4/40)도 실데이터. 테스트 2건 신설(수치 그라운딩 + **한계 포함 강제**).
  곁가지 수정: `.grid-cols-2` 기본 규칙이 레이아웃 CSS 에 없어 2단 그리드가 데스크톱에서
  세로로 쌓이던 것(문서 등록 화면 업로드 패널도 같은 결함) 수정. 테스트 489.

- **2026-08-19(사이트 UX)** — 🎨 **배포 사이트 5개 지적 반영** (사용자 리뷰). ① 홈 버튼: 사이드바
  로고·홈 항목이 index.html 로 간다. ② 메뉴 통일: `theme.NAV_SECTIONS` 단일 정의를 랜딩 제외
  전 페이지(화면 5 + 문서 3 + 플레이그라운드 + 신규 1)가 공유 — 문서·플레이그라운드도 같은 셸로
  이식했고 테스트가 고정한다(`test_every_page_has_the_same_global_nav`). ③ 한눈에 요약:
  각 화면 최상단에 `glance()` 밴드(결론 한 문장 + 핵심 칩, 수치는 전부 evidence에서). ④ 한국어
  우선: Citation Correctness→인용 정확성 등 라벨 정리(단, 테스트가 고정한 TBD·Escalation 용어와
  문서 관례 명칭은 유지). ⑤ **규제 문서 등록 화면 신설**(`ui/intake.py` → sources.html) —
  정적 배포가 정직하게 할 수 있는 것만 한다: 원문 스냅샷 해시(빌드 시 실계산 + SOURCES.md 레지스트리
  대조를 코드로 강제), 정책 버전 타임라인(policy DB 실데이터), 새 문서 SHA-256 브라우저 실계산.
  추출(LLM)·확정(사람)은 실행하는 척하지 않고 실제 CLI를 안내한다. 테스트 487(+3), 390px 가로
  스크롤 0 실측, 업로드 해시 흐름 브라우저 실측.

- **2026-08-19(검수 1차)** — ✍️ **QA 골드 DEV 검수 1차: 4/40 확정** (사용자). "인용만으로 확인 불가"
  4문항 전건 — 원문 문맥·전수 스캔으로 대조해 전부 골드가 맞음을 확인. 곁가지 발견: **FSC 보도자료가
  '투기과열지역'으로 오기**(지정권자 MOLIT는 '지구') → 공식 용어 앵커 엄격 유지 결정. 인용 보강 2건
  (GF-007 󰊵 각주, REG-002 MOLIT 지정 문장) → "인용만으로 확인 불가"는 구조적인 2건만 남음
  (BOR-003 괄호 표기, AMB-001 부정 주장 — 플래그가 남는 것이 정상). `02_DECISION_LOG.md` 기록. 테스트 484 유지.

- **2026-08-19(검수표)** — ✅ **QA 골드 DEV 40 검수표** (`tools/build_qa_review.py` →
  `docs/eval/QA_GOLD_REVIEW.md` + `qa_gold_review.html`). 상태판 "다음 작업 2"의 전제를 해소 —
  검수는 사람의 일이지만 검수 가능하게 만드는 것은 기계의 일(LOCKED §4). 문항마다 골드 답·채점
  앵커·원문 인용·replay 베이스라인 실측을 한 화면에 붙이고, 주의 신호를 먼저 올렸다:
  **인용만으로 확인 불가 4문항**(앵커가 실린 인용 안에 없음 — 원본 대조 필요), 베이스라인이 놓친
  앵커 3문항. 모델 답변 원문은 싣지 않았다(검수자 앵커링 방지). 검수표 CSS·인용 블록은
  `tools/review_theme.py`로 추출해 추출 골드 검수표와 공유(HTML 산출물 바이트 동일 확인).
  LOCKED/CHALLENGE는 열지 않음(DEV만). 테스트 484 유지.

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
