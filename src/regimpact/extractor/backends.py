"""LLM 백엔드 — **유료 API 키 없이도** Extractor를 실행하기 위한 provider 레이어.

배경: 이 프로젝트는 Anthropic API 키(종량 과금)를 전제로 하지 않는다. Extractor는
`CompletionFn = (system, user) -> dict` 하나만 요구하므로, 그 자리에 무엇을 꽂든
파이프라인·Assurance 채점은 동일하게 동작한다. 여기서 무과금 경로를 제공한다.

| provider   | 비용 | 필요한 것 | 용도 |
|------------|------|-----------|------|
| `cli`      | 추가 과금 없음(Claude Code 구독에 포함) | `claude` CLI 로그인 | **기본값.** 실측 실행 |
| `gemini`   | 무료 티어(카드 등록 불필요) | `GEMINI_API_KEY` | 타 provider 교차검증 |
| `manual`   | 0원 | 사람 + 아무 챗 UI | 키·CLI 아무것도 없을 때 |
| `replay`   | 0원(호출 없음) | 저장된 run.json | 재현·회귀·CI |
| `anthropic`| 종량 과금 | `ANTHROPIC_API_KEY` | 참고(선택) |

provider 교체가 곧 **Temporal/Provider consistency 실험 장치**가 된다: 같은 프롬프트를
서로 다른 모델에 태우고 Assurance 지표를 비교할 수 있다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .prompt import SYSTEM_PROMPT
from .schema import CATEGORIES

# (system_prompt, user_prompt) -> REGCHANGE_JSON_SCHEMA를 따르는 dict
CompletionFn = Callable[[str, str], dict]

PROVIDERS = ("cli", "gemini", "manual", "replay", "anthropic")

# 무과금 provider가 structured output을 보장하지 않으므로 형식을 프롬프트로 강제한다.
#
# 스키마는 **주입 가능**하다. 이 레이어는 provider를 추상화하는 곳이지 특정 출력 형식을
# 강제하는 곳이 아니다. RegChange 추출과 골드셋 QA는 형식이 다르므로 각자의 지시문·검증기를 넘긴다.
JSON_ONLY_INSTRUCTION = """
[출력 형식 — 반드시 지킬 것]
설명·머리말·코드펜스 없이 **JSON 객체 하나만** 출력하라. 최상위 키는 정확히 4개다:
  "policy_id": string
  "effective_from": string(YYYY-MM-DD) 또는 null
  "target_regions": string 배열
  "changes": 객체 배열. 각 원소의 키는 정확히
      "category"(다음 중 하나: {categories}),
      "summary"(string), "before"(string|null), "after"(string|null),
      "citation": {{"source_doc_id": string, "quote": string}},
      "confidence"(0.0~1.0 number)
citation.quote는 원문에서 **그대로 복사**한 연속된 문자열이어야 한다(요약·의역 금지).
""".format(categories=", ".join(CATEGORIES))


class LLMBackendError(RuntimeError):
    """백엔드 호출 또는 응답 파싱 실패."""


# ---------------------------------------------------------------- 응답 정규화

def coerce_json(text: str) -> dict:
    """모델의 자유 텍스트 응답에서 JSON 객체 하나를 뽑아낸다.

    structured output이 없는 백엔드(CLI/Gemini/사람)는 코드펜스나 짧은 머리말을
    붙이는 경우가 있다. 여기서 그것만 벗겨내고, 그 외의 관대한 보정은 하지 않는다
    (조용한 교정은 환각 측정을 왜곡하므로).
    """
    if not text or not text.strip():
        raise LLMBackendError("빈 응답")
    s = text.strip()

    fence = re.search(r"```(?:json)?\s*(.+?)```", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()

    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if start == -1 or end <= start:
            raise LLMBackendError(f"응답에서 JSON을 찾지 못함: {text[:200]!r}")
        try:
            obj = json.loads(s[start : end + 1])
        except json.JSONDecodeError as e:
            raise LLMBackendError(f"JSON 파싱 실패: {e}") from e

    if not isinstance(obj, dict):
        raise LLMBackendError(f"최상위가 객체가 아님: {type(obj).__name__}")
    return obj


def validate_regchange(obj: dict) -> list[str]:
    """REGCHANGE_JSON_SCHEMA 대비 위반 목록을 돌려준다(빈 리스트 = 통과).

    jsonschema 의존성을 추가하지 않기 위해 필요한 검사만 직접 수행한다.
    """
    errs: list[str] = []
    for key in ("policy_id", "effective_from", "target_regions", "changes"):
        if key not in obj:
            errs.append(f"필수 키 누락: {key}")

    if not isinstance(obj.get("policy_id", ""), str):
        errs.append("policy_id는 string이어야 함")
    eff = obj.get("effective_from")
    if eff is not None and not isinstance(eff, str):
        errs.append("effective_from은 string 또는 null이어야 함")
    if not isinstance(obj.get("target_regions", []), list):
        errs.append("target_regions는 배열이어야 함")

    changes = obj.get("changes")
    if not isinstance(changes, list):
        errs.append("changes는 배열이어야 함")
        return errs

    for i, item in enumerate(changes):
        if not isinstance(item, dict):
            errs.append(f"changes[{i}]는 객체여야 함")
            continue
        cat = item.get("category")
        if cat not in CATEGORIES:
            errs.append(f"changes[{i}].category 잘못됨: {cat!r}")
        if not isinstance(item.get("summary", ""), str) or not item.get("summary"):
            errs.append(f"changes[{i}].summary 누락")
        cit = item.get("citation")
        if not isinstance(cit, dict) or not cit.get("source_doc_id") or not cit.get("quote"):
            errs.append(f"changes[{i}].citation 불완전")
        conf = item.get("confidence", 1.0)
        if not isinstance(conf, (int, float)) or not 0.0 <= float(conf) <= 1.0:
            errs.append(f"changes[{i}].confidence 범위 밖: {conf!r}")
    return errs


# (obj) -> 위반 목록. 빈 리스트면 통과.
Validator = Callable[[dict], list]


def with_schema_retry(
    raw_call: Callable[[str, str], str],
    *,
    retries: int = 1,
    validator: Optional[Validator] = None,
    instruction: Optional[str] = None,
) -> CompletionFn:
    """텍스트를 돌려주는 호출을 감싸 JSON 파싱 + 스키마 검증 + 1회 교정 재시도를 붙인다.

    validator/instruction을 주지 않으면 RegChange 추출 형식을 기본으로 쓴다.
    재시도 프롬프트에는 위반 사유만 덧붙인다(정답을 알려주지 않음 — 채점 오염 방지).
    """
    check = validator or validate_regchange
    guide = instruction if instruction is not None else JSON_ONLY_INSTRUCTION

    def _complete(system: str, user: str) -> dict:
        sys_prompt = f"{system}\n{guide}"
        attempt_user, last_err = user, ""
        for attempt in range(retries + 1):
            text = raw_call(sys_prompt, attempt_user)
            try:
                obj = coerce_json(text)
                errs = check(obj)
                if not errs:
                    return obj
                last_err = "; ".join(errs[:8])
            except LLMBackendError as e:
                last_err = str(e)
            if attempt < retries:
                attempt_user = (
                    f"{user}\n\n[직전 응답이 형식 위반으로 거부됨: {last_err}]\n"
                    "내용은 바꾸지 말고 형식만 고쳐 JSON 객체 하나만 다시 출력하라."
                )
        raise LLMBackendError(f"스키마 검증 실패({retries + 1}회 시도): {last_err}")

    return _complete


# ---------------------------------------------------------------- 백엔드들

def cli_completion(
    model: str = "claude-sonnet-5",
    *,
    binary: str = "claude",
    timeout: int = 900,
    validator: Optional[Validator] = None,
    instruction: Optional[str] = None,
) -> CompletionFn:
    """**기본 무과금 경로.** 로컬 `claude` CLI를 1회성 프롬프트로 실행한다.

    이미 로그인된 Claude Code 구독 자격을 그대로 쓰므로 별도 API 키 발급도,
    종량 과금 결제수단 등록도 필요 없다(구독 사용량 한도는 소모됨).
    도구·MCP를 모두 끈 순수 텍스트 완성으로 호출해 부작용을 차단한다.
    """
    if shutil.which(binary) is None:
        raise LLMBackendError(
            f"`{binary}` CLI를 찾지 못했습니다. Claude Code 설치·로그인 후 재시도하세요."
        )

    def _raw(system: str, user: str) -> str:
        cmd = [
            binary, "-p",
            "--model", model,
            "--output-format", "json",
            "--append-system-prompt", system,
            "--allowed-tools", "",          # 도구 사용 차단 = 순수 완성
            "--strict-mcp-config",          # MCP 서버 미로드
            "--no-session-persistence",
        ]
        proc = subprocess.run(
            cmd, input=user, capture_output=True, text=True, timeout=timeout,
            cwd=os.environ.get("TMPDIR", "/tmp"),
        )
        if proc.returncode != 0:
            raise LLMBackendError(f"CLI 실패(rc={proc.returncode}): {proc.stderr[:300]}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise LLMBackendError(f"CLI 출력 파싱 실패: {e}") from e
        if envelope.get("is_error"):
            raise LLMBackendError(f"CLI 오류 응답: {str(envelope.get('result'))[:300]}")
        return envelope.get("result", "")

    return with_schema_retry(_raw, validator=validator, instruction=instruction)


def gemini_completion(
    model: str = "gemini-2.5-flash",
    *,
    api_key: str | None = None,
    timeout: int = 600,
    validator: Optional[Validator] = None,
    instruction: Optional[str] = None,
) -> CompletionFn:
    """Google AI Studio **무료 티어** 백엔드 (aistudio.google.com에서 키 무료 발급).

    표준 라이브러리 urllib만 사용 — SDK 의존성 없음. 결제수단 등록 없이 동작하며
    무료 티어의 분당/일일 호출 한도를 따른다.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise LLMBackendError(
            "GEMINI_API_KEY가 없습니다. https://aistudio.google.com 에서 무료 발급 후 "
            "export GEMINI_API_KEY=... 하세요."
        )

    def _raw(system: str, user: str) -> str:
        import urllib.error
        import urllib.request

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )
        body = json.dumps({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise LLMBackendError(f"Gemini HTTP {e.code}: {e.read()[:300]!r}") from e
        try:
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMBackendError(f"Gemini 응답 형식 예상 밖: {str(payload)[:300]}") from e

    return with_schema_retry(_raw, validator=validator, instruction=instruction)


def manual_completion(
    workdir: str | Path,
    *,
    validator: Optional[Validator] = None,
    instruction: Optional[str] = None,
) -> CompletionFn:
    """키도 CLI도 없을 때의 **완전 무과금 경로**: 사람이 중계한다.

    프롬프트를 `prompt.txt`로 쓰고, 사람이 아무 챗 UI(무료 웹 Claude/Gemini 등)에
    붙여넣어 받은 JSON을 `response.json`으로 저장하면 그것을 읽는다. 응답 파일이
    아직 없으면 안내와 함께 중단한다(재실행하면 이어서 진행).
    """
    wd = Path(workdir)

    def _raw(system: str, user: str) -> str:
        wd.mkdir(parents=True, exist_ok=True)
        prompt_path, resp_path = wd / "prompt.txt", wd / "response.json"
        prompt_path.write_text(f"{system}\n\n---\n\n{user}\n", encoding="utf-8")
        if not resp_path.exists():
            raise LLMBackendError(
                f"수동 모드: 프롬프트를 {prompt_path} 에 저장했습니다.\n"
                f"이 내용을 아무 챗 UI에 붙여넣고, 받은 JSON을 {resp_path} 로 저장한 뒤 "
                "동일 명령을 다시 실행하세요."
            )
        return resp_path.read_text(encoding="utf-8")

    return with_schema_retry(_raw, retries=0, validator=validator, instruction=instruction)


def replay_completion(
    run_path: str | Path, *, validator: Optional[Validator] = None
) -> CompletionFn:
    """저장된 실행 결과를 재생한다 — LLM 호출 0회, 완전 결정적.

    `run_extractor.py`가 남긴 run JSON(`extraction` 키) 또는 추출 dict 자체를 받는다.
    CI·회귀·리뷰어 재현용. 채점 로직이 바뀌었을 때 과거 출력에 재채점할 수 있다.
    """
    payload = json.loads(Path(run_path).read_text(encoding="utf-8"))
    extraction = payload.get("extraction", payload)

    check = validator or validate_regchange

    def _complete(system: str, user: str) -> dict:  # noqa: ARG001 - 서명 호환용
        errs = check(extraction)
        if errs:
            raise LLMBackendError(f"저장된 결과가 스키마 위반: {'; '.join(errs[:5])}")
        return extraction

    return _complete


def anthropic_completion(model: str = "claude-opus-5", max_tokens: int = 16000) -> CompletionFn:
    """Anthropic API 직접 호출 (structured output). **종량 과금** — 선택 경로다.

    ANTHROPIC_API_KEY로 인증. import는 지연(무과금 경로에는 SDK가 필요 없음).
    """
    import anthropic  # 지연 import: 오프라인 테스트·타 provider에는 SDK가 불필요

    from .schema import REGCHANGE_JSON_SCHEMA

    client = anthropic.Anthropic()

    def _complete(system: str, user: str) -> dict:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "format": {"type": "json_schema", "schema": REGCHANGE_JSON_SCHEMA}
            },
        )
        # output_config.format 보장: 첫 text 블록이 유효 JSON
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    return _complete


# ---------------------------------------------------------------- 선택기

def available_providers() -> dict[str, bool]:
    """이 환경에서 지금 바로 쓸 수 있는 provider를 조사한다(안내 메시지용)."""
    return {
        "cli": shutil.which("claude") is not None,
        "gemini": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "manual": True,
        "replay": True,
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


def resolve_completion(
    provider: str = "auto",
    *,
    model: str | None = None,
    validator: Optional[Validator] = None,
    instruction: Optional[str] = None,
    **kwargs,
) -> CompletionFn:
    """provider 이름으로 CompletionFn을 만든다. "auto"는 무과금 경로를 우선한다.

    우선순위: cli(구독 포함) → gemini(무료 티어) → anthropic(과금) → manual.
    """
    avail = available_providers()
    if provider == "auto":
        for name in ("cli", "gemini", "anthropic"):
            if avail[name]:
                provider = name
                break
        else:
            provider = "manual"

    shape = {"validator": validator, "instruction": instruction}
    if provider == "cli":
        return cli_completion(**({"model": model} if model else {}), **shape, **kwargs)
    if provider == "gemini":
        return gemini_completion(**({"model": model} if model else {}), **shape, **kwargs)
    if provider == "anthropic":
        # 유료 경로는 서버측 structured output을 쓰므로 프롬프트 지시문이 필요 없다
        return anthropic_completion(**({"model": model} if model else {}), **kwargs)
    if provider == "manual":
        return manual_completion(kwargs.pop("workdir", "manual_run"), **shape, **kwargs)
    if provider == "replay":
        return replay_completion(kwargs.pop("run_path"), validator=validator, **kwargs)
    raise LLMBackendError(f"알 수 없는 provider: {provider!r} (가능: {', '.join(PROVIDERS)})")
