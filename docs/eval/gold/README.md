# 골드 평가셋 — 115문항 (DEV 40 / LOCKED 40 / CHALLENGE 35)

> 브리프 §11(문항 설계) · §12(누수 방지) · `metrics_spec.md` §0-A(규모·split) 구현.
> 작성일 2026-08-18 · 현재 전 문항 **🤖 `ai_draft`** — ✍️ 사람 도메인 검수 대기.

## 구성

| split | 파일 | 규모 | high-risk 비중 | 용도 |
|---|---|---:|---:|---|
| DEV | `dev.json` | 40 | 52% | 프롬프트·retrieval·extractor 튜닝 — **개발 중 쓰는 유일한 셋** |
| LOCKED TEST | `locked.json` | 40 | 52% | 최종 성능평가 (코어 완성 후 1회) |
| CHALLENGE | `challenge.json` | 35 | 80% | 적대적 평가 (마지막 1회) |
| TEMPORAL | `temporal.json` | 12 | 58% | 시점 질의 — Policy-version Consistency 가동용 (비봉인, 2026-08-19 신설) |

TEMPORAL은 위 115문항과 **별도의 셋**이다(DEV/LOCKED 분포 규율 불변). 코퍼스 확장에서
드러난 실패모드(recall 급락의 원인 = 시점 판별)를 직접 겨눈다: 시점이 명시된 질문,
발표일≠시행일 경계쌍, 2025↔2026 동형 문구 판별, 그리고 **원문에 해제일이 없어
escalation이 정답인** 문항. `as_of` 필드가 있는 문항은 인용 대조에 더해 Temporal Policy
Resolver와의 정합 검사(`eval/temporal.py`)를 통과해야 한다 — 2020 6·17이 해제 원문과 함께
confirm() 되는 순간, 같은 검사가 escalation 문항을 "답변형으로 갱신하라"고 지목한다.
작성 도구: `tools/gold_temporal.py`. 🤖 ai_draft — ✍️ 검수 대기.

DEV와 LOCKED는 **카테고리 분포가 동일**하다. 분포가 다르면 최종 성능 차이가 실력 차이인지
난이도 차이인지 구분할 수 없기 때문이다(테스트로 고정).

CHALLENGE는 브리프 §11 "설계 철학"대로 EXCEPTION/GRANDFATHERING/EFFECTIVE_DATE/CONFLICT를
가중해 high-risk 80%로 구성했고, NORMAL·REGION 같은 평이한 카테고리는 의도적으로 넣지 않았다
(검증기가 "미커버 카테고리" 경고를 내지만 이 셋에서는 의도된 설계다).

## 문항 필드 (브리프 §11)

`question` · `gold_answer` · `gold_facts`(자동 채점 앵커) · `citations`(근거 문서 + **원문 위치**) ·
`category` · `expect_escalation` · `policy_version` · `rule_id` · `authored_by` · `note`

**원문 위치를 문자 offset으로 적지 않는다.** offset은 원문을 다시 추출하면 조용히 어긋나지만,
verbatim 인용은 검증기가 매번 원문과 대조해 깨진 것을 즉시 드러낸다. 위치의 진실은 숫자가 아니라 문자열이다.

## 🔒 봉인 — 문서가 아니라 코드가 막는다

브리프 §12의 규율("LOCKED/CHALLENGE는 개발 중 튜닝에 쓰지 않는다")은 문서에만 적으면 지켜지지 않는다.
무심코 열어보는 것이 누수의 실제 경로이므로 **로더가 거부한다.**

```python
load_split(Split.DEV)                          # 자유
load_split(Split.LOCKED)                       # → SealedSplitError
load_split(Split.LOCKED, unseal_reason="...")  # 20자 이상 구체적 사유 필요 → 열리고 기록됨
split_stats(Split.LOCKED)                      # 정답 없이 구성만 — 봉인 유지
```

- 봉인 해제 자체는 막지 않는다(언젠가는 열어야 한다). 대신 **이유를 요구하고 append-only로 기록**한다
  → `SEAL_ACCESS_LOG.md`. 사고를 막는 통제가 아니라 사고가 조용히 지나가지 못하게 하는 통제다.
- `split_stats()`가 정답 없이 구성만 돌려주는 이유: 일상적인 커버리지 점검이 봉인 해제를 요구하면
  사람은 결국 습관적으로 봉인을 열게 된다. **통제는 정당한 작업을 방해하지 않아야 지켜진다.**
- `tests/test_goldset.py`가 `src/`·`examples/`에서 `locked.json`/`challenge.json` 참조를 금지한다.

## 무결성 — 정답지 자신에게 Citation Assurance를 적용한다

정답지가 틀리면 그 위의 모든 지표가 틀린다. 사람 눈으로 115문항의 인용을 원문과 대조할 수 없으므로
`validate_items()`가 매번 검사한다.

```bash
python examples/validate_goldset.py     # LLM 호출 0회, 정답 미출력
python -m pytest -k goldset             # 29개
```

검사 항목: **인용이 원문에 verbatim으로 존재** / id·질문 중복 / id 접두사와 split 일치 /
`gold_facts`가 `gold_answer` 안에서 확인 가능 / AMBIGUOUS는 반드시 escalation 기대 /
`rule_id`가 룰엔진의 실제 rule_id / `policy_version` 유효.

작성 도구(`tools/author_goldset.py`)의 `q()`는 인용문을 **손으로 옮기지 않고 원문에서 잘라 온다.**
손으로 옮기면 PDF/HWP 추출본의 개행·특수문자 때문에 반드시 어긋나고, 그 어긋남은
"인용은 그럴듯한데 원문엔 없음" — 이 프로젝트가 LLM에서 잡아내려는 바로 그 실패와 같은 모양이다.

## 정직한 한계 (브리프 §12)

1. **독립 벤치마크가 아니다.** 브리프 §12 그대로:
   > "The locked test set was frozen before system tuning, but was authored within the project
   > and is not an independent third-party benchmark."
2. **작성자와 시스템 개발자가 같다.** LOCKED는 튜닝 시작 **전에** 작성됐으므로 "고정" 요건은
   충족하지만, 외부 블라인드 평가는 아니다. 이 한계는 검증보고서에 명시한다.
3. **전 문항 🤖 초안 상태.** 도메인 정답은 사람 확정이 필요하다(LOCKED §4).
   확정된 문항은 `authored_by`를 `human_confirmed`로 바꾼다.
4. **단일 정책(6·30) 코퍼스.** 다른 정책 사례가 추가되면 Temporal/Policy-version 계열 문항을
   확장해야 한다(현재는 6·30 내부의 시행일 2종·도입일 5종으로 구성).

## 작성·재생성

```bash
python tools/gold_dev.py         # DEV 재생성 + 무결성 검사
python tools/gold_locked.py      # LOCKED
python tools/gold_challenge.py   # CHALLENGE
```

문항 추가·수정은 `tools/gold_*.py`에서 하고 JSON을 직접 편집하지 않는다 — JSON을 손대면
인용이 원문에서 잘려 온 것이라는 보장이 깨진다.
