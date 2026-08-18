# 06 — LLM PROVIDER (무과금 실행 정책)

> **결정(2026-08-18): 이 프로젝트는 유료 API 키를 전제하지 않는다. 총 지출 0원으로 실행·재현된다.**
> 배경: 사용자가 Anthropic 종량 API 키를 발급받기 어렵고, 프로젝트에 비용을 지출하지 않기로 함.
> 이 문서는 그 제약 아래에서 어떻게 실제 LLM 실측을 확보하는지 정의한다.

---

## 왜 이게 가능한가 (설계적 근거)

Extractor는 처음부터 LLM 호출을 **주입 가능한 함수 하나**로 좁혀 두었다.

```python
CompletionFn = Callable[[str, str], dict]     # (system, user) -> 스키마 준수 dict
extract_regchange(sources, complete=<여기에 무엇이든>)
```

파이프라인·프롬프트·Assurance 채점은 이 함수가 무엇인지 모른다. 따라서 **provider 교체는
1줄 교체**이며, 특정 벤더에 잠기지 않는다. `src/regimpact/extractor/backends.py`가 그 구현이다.

부수 효과: provider를 바꿔가며 같은 프롬프트를 태울 수 있으므로, 그 자체가
**모델 리스크 비교 실험 장치**가 된다 (`docs/eval/EXTRACTOR_RUN_REPORT.md` §2 D-03 참고).

---

## Provider 표

| provider | 비용 | 필요한 것 | 언제 쓰나 |
|---|---|---|---|
| **`cli`** ★기본 | **추가 과금 없음** — Claude Code 구독에 포함 | `claude` CLI 로그인 | 실제 실측 실행 |
| `gemini` | **무료 티어** (결제수단 등록 불필요) | `GEMINI_API_KEY` | 타 벤더 교차검증 |
| `manual` | **0원** | 사람 + 아무 챗 UI | 키도 CLI도 없는 환경 |
| `replay` | **0원 (호출 0회)** | 저장된 run JSON | 재현·회귀·CI·채점 로직 변경 후 재채점 |
| `anthropic` | 종량 과금 | `ANTHROPIC_API_KEY` | 선택 — 쓰지 않아도 무방 |

`--provider auto`(기본)는 무과금 경로를 우선해 `cli → gemini → anthropic → manual` 순으로 고른다.

### `cli` — 기본 경로
로컬 `claude` CLI를 1회성 프롬프트로 호출한다. 별도 API 키 발급도, 결제수단 등록도 없다
(구독 사용량 한도는 소모된다). 도구·MCP를 모두 끈 순수 텍스트 완성으로 실행해 부작용을 차단한다.

```bash
python examples/run_extractor.py --provider cli --model claude-sonnet-5
```

### `gemini` — 무료 티어 교차검증
[aistudio.google.com](https://aistudio.google.com)에서 키를 무료 발급받는다(카드 불필요).
표준 라이브러리 `urllib`만 사용하므로 SDK 설치도 필요 없다.

```bash
export GEMINI_API_KEY=...
python examples/run_extractor.py --provider gemini
```

### `manual` — 아무것도 없을 때
프롬프트를 `docs/eval/runs/manual/prompt.txt`로 내보낸다. 사람이 그것을 아무 챗 UI에
붙여넣고 받은 JSON을 같은 폴더 `response.json`으로 저장한 뒤 동일 명령을 재실행하면 이어서 채점된다.

### `replay` — 재현
과거 실행 기록을 LLM 호출 없이 재생한다. 리뷰어가 **아무 계정 없이도** 결과를 재현할 수 있고,
채점 로직을 고쳤을 때 과거 출력에 재채점할 수 있다.

```bash
python examples/run_extractor.py --provider replay --run docs/eval/runs/run_cli_sonnet5_v2.json
```

---

## 무과금 경로가 감수하는 것 (정직한 한계)

1. **structured output 보장이 없다.** Anthropic API의 `output_config.format`처럼 스키마를
   서버가 강제해 주지 않는다. → `backends.with_schema_retry()`가 JSON 정규화(코드펜스 제거) +
   스키마 검증 + **1회 교정 재시도**로 메운다. 재시도 프롬프트에는 위반 사유만 넣고 정답은
   넣지 않는다(채점 오염 방지). 검증 실패는 조용히 통과시키지 않고 예외를 던진다.
2. **호출 한도.** 구독 사용량·무료 티어 분당 한도에 걸릴 수 있다. → 실행 기록(`runs/*.json`)을
   남겨 `replay`로 재현하므로 반복 호출이 필요 없다.
3. **레이턴시·재현성.** temperature를 낮춰도 완전 결정적이지 않다. → 평가에 쓰는 수치는 항상
   저장된 run 기록을 기준으로 인용하고, run에 `source_sha256`를 함께 남겨 입력 동일성을 고정한다.

---

## 규칙

- 문서·리포트에 인용하는 모든 실측치는 `docs/eval/runs/`의 저장된 run에서 나와야 한다(구두 기억 금지).
- provider·모델을 바꾸면 새 run 태그로 저장한다(`--tag`). 기존 수치를 덮어쓰지 않는다.
- 원문(`docs/sources/raw/`)이 바뀌면 `source_sha256`가 달라지므로 과거 수치와 직접 비교하지 않는다.
