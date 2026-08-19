# 09 — RegImpact AI 기능 총정리

> **한 줄 정의:** 생성형 AI 기반 주택담보대출 규제 변경 영향분석 및 검증 시스템
> (RegImpact AI — Financial Regulation Impact & Assurance Platform)
>
> 이 문서는 프로젝트의 기능 전체를 한 곳에 정리한 개요다. 지원서·소개자료·인수인계에 재료로 쓴다.
> 세부 철학은 `00_BRIEF.md`, 현재 상태는 `01_PROJECT_STATE.md`, 사업화 관점은 `business/BUSINESS_PLAN_v1.md`.
> 마지막 갱신: 2026-08-19 · 기준 수치: 테스트 484개 통과(1 skipped) · LLM 비용 0원(재생 모드)

---

## 1. 무엇을 하는 시스템인가

금융 규제 변경 공문(예: 6·30 규제지역 지정)을 입력받아:

1. **무엇이 바뀌었는지** 추출한다 — LLM이 원문 인용을 강제당한 채 "사실"만 뽑는다.
2. 그 변경이 **여신 룰 · 고객 · 테스트케이스로 어떻게 전파되는지** 산출한다.
3. **각 단계 산출물이 틀리지 않았음을 독립 기준과 대조해 증명한다** — 이것이 제품의 본체다.

**핵심 설계 원칙 (LOCKED):** LLM은 규제를 판정하지 않는다. 판정은 사람이 확정한 명세(`05_RULE_SPEC.md`)를
구현한 **결정적 룰엔진**이 한다. 이 경계 덕분에 엔진이 LLM 출력의 검증 기준이 될 수 있다.
반대 방향(LLM이 룰을 생성)이면 순환 검증이 되어 무의미하다.

## 2. 파이프라인 — E2E 11단계

`examples/demo_impact_e2e.py` 한 번 실행으로 관통한다. 기본은 **LLM 호출 0회·비용 0원**
(실제 LLM 실행 기록을 재생 — `docs/eval/runs/`).

```
 1. Source Snapshot          공문 원문 로드 (해시 고정 — 입력이 바뀌면 탐지)
 2. Policy Version Resolution 판정 기준일의 정책 버전 해석 (직전 정책 대비 diff)
 3. Before/After 추출         LLM 추출 + 인용 검증 (원문 verbatim 대조)
 4. 지역코드 정규화           자연어 지역 표현 → 표준 코드
 5. Impact Matrix            변경 → 업무영역·시간축(Phase)별 영향 매트릭스
 6. Customer Impact          합성 포트폴리오(synthetic) 기준 고객 영향 계량
 7. Rule Diff 제안            현행 룰 대비 변경 필요분 도출
 8. Test Cases               경계·예외 중심 테스트케이스 자동 생성
 9. Rule Regression          룰엔진 vs 독립 오라클 차등 회귀검증
10. Assurance Evaluation     확정 임계값 대비 스코어카드 판정
11. Human Review + 리포트     사람 검토 지점 표시 · 감사로그 해시체인 봉인
```

## 3. 기능 모듈별 정리

### 3.1 변경 추출 — `src/regimpact/extractor/`
- 공문 원문 → 구조화된 규제 변경 사실(Before/After, 시행일, 예외, 경과규정) 추출.
- **인용 강제:** 모든 추출 사실에 원문 인용이 붙어야 하며, 인용이 원문에 실재하는지 결정적으로 대조한다
  (Citation Assurance). 인용이 안 붙거나 원문에 없으면 그 사실은 탈락.
- **무과금 provider 레이어** (`backends.py`): 저장된 실행 기록 재생(replay, 기본) / CLI 구독 실행 /
  API 실행을 같은 인터페이스로 교체. API 키 없이 같은 수치가 재현된다.
- 다중 실행 병합(`merge.py`) · 후처리 정규화(`postprocess.py`) · 골드셋 채점(`evaluate.py`).

### 3.2 정책 버전 DB + 시점 해석 — `src/regimpact/policy/`
- 정책 문서(FSC·MOLIT 공문)를 버전으로 등록하고, **"이 판정일 기준으로 유효한 정책"**을 해석한다
  (Temporal Policy Resolver). "직전까지 유효했던 정책과 무엇이 달라졌는가"에 답하는 층.
- 지역별 규제 상태 타임라인(지정 전/후 전이) · 정책 DB와 룰엔진 기준선의 **양방향 드리프트 검사**
  (둘이 조용히 갈라지면 테스트가 실패한다).
- 등록 정책: `docs/policies/` — MOLIT 2016·2017·2025, FSC 2026-06-30.

### 3.3 룰엔진 — `src/regimpact/rule_engine.py`
- 주택구입목적 주담대 LTV 판정. 사람이 확정한 명세(`05_RULE_SPEC.md` §C 의사결정표)의 결정적 구현.
- 입력: 지역·판정기준일·주택수·생애최초·서민실수요·처분조건부·경과규정 관련 일자 등.
- 출력: 적용 LTV · 적용 규칙 ID · 경과규정 적용 여부 · 판정 근거 라벨 · 근거 정책 ID.
- **추정 금지:** 명세 밖 구간(정책대출·전세 등)은 자동판정하지 않고 `NEEDS_HUMAN_REVIEW`/Discovery로
  명시 라우팅한다. 미등록 지역은 UNKNOWN → 사람 검토(R-01 결함 수정으로 확립).
- 지역 레지스트리(`regions.py`): 서울 25 + 경기 15 규제지역 전량 등록.

### 3.4 테스트케이스 생성 + 차등 검증 — `src/regimpact/tc_generator/`
- 규제 변경의 **가장자리**(예외·경과규정·시행일 경계·지역 전이)를 중심으로 테스트케이스 자동 생성.
- **독립 오라클** (`oracle.py`): 같은 명세를 룰엔진과 별도로 재구현한 판정기. 오라클은 엔진을 import하지
  않는다 — 이 독립성이 차등 검증(differential testing)의 성립 조건.
- 회귀 하네스(`regression.py`): 엔진 vs 오라클 전건 대조. 불일치는 곧 결함 신호.

### 3.5 임팩트 분석 — `src/regimpact/impact/`
- **Impact Matrix** (`builder.py`): 변경사항 → 업무영역 × 시간축(Phase: 시행 전 필수 / 시행 후 도착) 매트릭스.
  "일은 두 물결로 온다"는 실무 사실을 구조로 반영 — 시행 후 트리거 작업이 잊히지 않게 한다.
- **고객 영향** (`customer.py`, `portfolio.py`): 합성 포트폴리오(수천 건, seed 고정)에 변경 전/후 룰을
  적용해 영향 고객 수·한도 변화를 계량. 실제 고객 데이터는 쓰지 않는다(LOCKED §8).
- 서술 리포트 생성(`narrative.py`, `report.py`).

### 3.6 Rule Change Proposal — `src/regimpact/proposal/`
- 추출 결과 → 구조화된 룰 변경안(DRAFT) 조립 → **룰엔진과 교차검증**(변경안대로 판정이 실제로
  바뀌는지) → 사람 승인 대기 상태로 산출. LLM 제안은 항상 DRAFT, 확정은 사람.
- 정합성 검사(`consistency.py`): 변경안·추출·정책 DB 삼자 일치 확인.

### 3.7 Assurance 스코어카드 — `src/regimpact/assurance/`
- 인용 접지율·추출 정확도·회귀 통과율 등 지표를 **사전 확정 임계값**(`thresholds.py`)과 대조해
  PASS/FAIL 판정. 임계값을 결과 보고 조정하는 것을 구조적으로 막는다.
- **미측정 ≠ 통과:** 못 잰 지표는 통과로 세지 않는다.

### 3.8 판별력 측정 — `src/regimpact/discrimination.py`
- **Negative control:** 정상 데이터 100% 통과는 하니스가 둔감해도 나온다. 오류(인용 환각, 수치 왜곡,
  시행일 변조)를 의도적으로 주입하고 지표가 실제로 떨어지는지 실측한다.
- 발견 사실을 숨기지 않는다: 집계 비율 지표는 단건 오류에 둔감(인용 1건 환각 = 2pp 하락)하고,
  실질 탐지력은 항목 단위 검사가 담당한다 — `docs/eval/VALIDATION_LIMITS.md`에 한계로 명시.

### 3.9 감사로그 — `src/regimpact/audit/`
- 파이프라인 전 단계의 행위를 **해시체인**으로 연결한 감사증적. 중간 변조 시 체인이 깨진다.
- 명시된 한계: 끝에서 잘라낸 로그는 체인만으로 구분 불가 → `verify(expected_head=...)` + head 해시
  외부 보관을 문서화. (한계를 아는 것도 기능이다.)

### 3.10 평가셋 · 골드 데이터 — `src/regimpact/eval/`, `docs/eval/`
- 평가셋을 개발보다 먼저 만들고 **DEV / LOCKED TEST / CHALLENGE 분리**(평가 누수 방지, LOCKED §5).
- 골드셋 저작·검수 도구(`tools/author_goldset.py`, `gold_*.py`) + 검수용 HTML 리포트 생성.
- 추출 성능 채점(`goldset.py`) · QA 검수(`qa.py`) · 스키마 검증(`validate.py`).

### 3.11 거버넌스 문서 자동 생성 — `src/regimpact/governance/`
- **Model & System Card**: 사용 목적 · 범위 외 · 오용 방지 명시.
- **AI Risk Register**: 리스크 18건 / 5범주, 실제 발생 이력 5건 표시. 리스크 판단(발생가능성·영향)은
  사람이 코드에 적고, 정량 수치는 검증보고서와 같은 evidence에서 온다.
- **통제 실재성 강제:** "통제 운영 중"이라 적으면 그 통제가 가리키는 코드·테스트가 실재하는지
  테스트가 확인한다 — 리스크 레지스터가 장식이 되는 것을 막는다.

### 3.12 검증보고서 자동 생성 — `src/regimpact/report/`
- 모델검증 관례 구조(개념적 건전성 · 구현 정확성 · 성과 검증 · 거버넌스 · 한계 · 발견사항)의
  보고서를 **파이프라인 실측 수치로 조립**한다. 렌더러에 도메인 수치 리터럴이 없는지 절 단위로 검사
  — 손으로 적은 숫자가 실측인 척 못 하게 한다.
- §12 발견사항: **자체 발견 결함 10건**을 심각도·조치와 함께 기록 (차등검증이 결함을 놓친 사례 포함).

### 3.13 검색/리트리벌 — `src/regimpact/retrieval/`
- 공문 청킹 + BM25 검색 · 검색 품질 평가. 사이트 검색 페이지의 기반 (JS 포팅 대조 포함).

### 3.14 UI · 정적 사이트 — `src/regimpact/ui/`, `tools/build_site.py`
- 파이프라인 1회 실행 결과로 **정적 사이트 전체를 굽는다** — 서버·API 키 없이 열린다.
  배포: https://ahra-june.github.io/RegImpact_AI/
- 페이지 구성:

| 페이지 | 내용 |
|---|---|
| index (랜딩) | 프로젝트 개요 · 핵심 수치 |
| regchange | 추출된 변경사항 + 인용 근거 |
| rule | 룰엔진 판정 결과 뷰 |
| impact_matrix | 업무영역×시간축 영향 매트릭스 |
| portfolio | 합성 포트폴리오 고객 영향 |
| assurance | 스코어카드 판정 |
| **playground** | **판정 플레이그라운드** — 차주 조건을 바꾸면 즉시 판정 + 어느 규칙에서 멈췄는지 |
| validation_report / validation_summary | 검증보고서 전문 / 1페이지 요약 |
| model_system_card · ai_risk_register | 거버넌스 문서 |
| sources · graph · search | 원문 출처 · 산출물 관계 그래프 · 문서 검색 |

- **JS 포팅 대조:** 플레이그라운드의 판정 엔진은 Python 원본을 JS로 포팅한 것. 규칙 값은 JS에
  하드코딩하지 않고 픽스처에서 읽으며, 판정 36건 + 지역×시점 450건 자동 대조가 CI에서 강제된다.
  대조 실패 시 배포가 막힌다.
- GitHub Actions: **테스트 통과 후에만 배포** — 깨진 수치를 올리지 않는다.

## 4. 검증 체계 한눈에 (이 프로젝트의 본체)

| 장치 | 요점 |
|---|---|
| 차등 검증 | 룰엔진을 스스로 채점하지 않는다 — 독립 재구현 오라클과 대조 (오라클은 엔진 import 금지) |
| 인용 검증 | LLM 추출 사실마다 원문 verbatim 대조 — 환각이 산출물에 들어오지 못하게 |
| 판별력 실측 | 오류를 주입해 지표가 실제로 떨어지는지 확인 (negative control) |
| 추정 금지 | 원문에 없는 값을 메우지 않는다 — 커버리지 상한을 감수하고 명시 |
| 미측정 ≠ 통과 | 못 잰 지표는 통과로 세지 않는다 |
| 사전 확정 임계 | 스코어카드 임계값은 결과를 보기 전에 확정 |
| 해시 고정 입력 | 공문 원문·실행 기록 해시 스냅샷 — 입력 변조 탐지 |
| 감사 해시체인 | 전 단계 행위 연결 · 변조 시 체인 파괴 |
| 자체 결함 기록 | 발견 결함 10건을 심각도·조치와 함께 공개 (검증 장치가 놓친 사례 포함) |
| 문서 자동 생성 | 보고서·카드·레지스터는 손으로 쓰지 않는다 — 시스템이 바뀌면 문서도 바뀐다 |

## 5. 실행 방법 (전부 무료)

```bash
pip install -e ".[dev]"

python -m pytest -q                          # 테스트 전량 (484 passed)
python examples/demo_impact_e2e.py           # 파이프라인 11단계 관통
python examples/demo_discrimination.py       # 판별력 실측 (오류 주입 후 재측정)
python examples/demo_tc_regression.py        # 차등 회귀검증 단독
python examples/build_validation_report.py   # 검증보고서 재생성
python tools/build_site.py                   # 사이트 빌드 → site/
node tools/verify_js_port.mjs                # JS 포팅 판정 대조
```

기본 provider가 `replay`라 실제 LLM 실행 기록을 재생한다 — API 키 없이 같은 수치가 나온다.
라이브 실행은 `docs/06_LLM_PROVIDER.md`.

## 6. 범위와 한계 (정직 고지)

- **수직 슬라이스:** 주택구입목적 주담대 LTV만 자동판정. 전세·신용·중도금·사업자·정책대출은
  Discovery(사람 검토)로 명시 분리. 넓이보다 "한 슬라이스의 검증 가능성"을 택했다.
- **DTI·한도액은 참고값** — 코어 판정이 아니다 (명세 §B).
- 고객 데이터·실제 내규 미사용 — 공개 공문 + 모의 내규 + 합성 포트폴리오. 수치에는 항상
  "synthetic" 명시.
- 나머지 한계는 `docs/eval/VALIDATION_LIMITS.md` · 검증보고서 §한계에 정량으로 기록.

## 7. 활용 맥락별 강조점

| 맥락 | 앞세울 것 |
|---|---|
| 이직 포트폴리오 (Model Risk·모델검증·AI Governance) | §4 검증 체계 + 자체 결함 10건 + 검증보고서 |
| 핀테크 아이디어 공모전 (~10/8) | "검증 가능한 금융 AI" 본체 + 플레이그라운드 데모 |
| Tomorrow Challenge B2C (~8/31) | 플레이그라운드·JS 엔진·정책 시점 해석 → 소비자용 전/후 시뮬레이터 (`business/APPLY_TOMORROW_CHALLENGE_v0.md`) |
| B2B 사업화 | 규제 1건 대응 패키지 — `business/BUSINESS_PLAN_v1.md` |
