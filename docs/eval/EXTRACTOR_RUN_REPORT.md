# Extractor 첫 실측 리포트 — 6·30 앵커

> **이 프로젝트 최초의 실제 LLM 실측치다.** 그 전까지 모든 수치는 오프라인 stub 기반이었다.
> - 실행일: 2026-08-18
> - 대상: 6·30 공문 3건 (`docs/sources/raw/`, 총 25.5KB)
> - 골드: `docs/eval/regchange_gold_6_30.json` (사람 확정)
> - **비용: 0원** — Anthropic 종량 API 키를 쓰지 않았다. `claude` CLI 백엔드(구독 포함) 사용.
> - 원시 기록: `docs/eval/runs/run_*.json` (`--provider replay`로 완전 재현 가능)

---

## 1. 결과 요약

| run | 모델 | 추출 건수 | Citation Correctness | Unsupported Claim Rate | Change Completeness | Exception Recall | Effective-date | Regions |
|---|---|---|---|---|---|---|---|---|
| `cli_sonnet5` (v1 프롬프트) | claude-sonnet-5 | 15 | **100%** | **0%** | 100% | 50% | OK | ❌ MISS |
| `cli_sonnet5_v2` (v2 프롬프트+정규화) | claude-sonnet-5 | 19 | **100%** | **0%** | 100% | 50% | OK | ✅ OK |
| `cli_haiku45` | claude-haiku-4-5 | 12 | **75%** | **25%** | 100% | 50% | OK | ✅ OK |

지표 정의는 `docs/metrics_spec.md`. Citation Correctness는 인용문이 원문에 **verbatim으로
존재하는지**를 결정적으로 대조한 값이므로 LLM 자기채점이 아니다.

---

## 2. 확인된 결함 3건 (실측으로 드러남)

### D-01 지역 어휘 불일치 — `[✅ 해결]`
- **증상:** 추출기가 `["화성시 동탄구", "용인시 기흥구", "구리시"]`(한글 표기)를 냈는데
  룰엔진·골드는 `["HWASEONG_DONGTAN", ...]`(코드)를 쓴다 → Regions MISS.
- **본질:** 환각이 아니라 **컴포넌트 간 인터페이스 결함**. E2E 관통을 실제로 깨는 종류.
- **조치:** 프롬프트에 코드 어휘를 넣지 **않았다**(코드 목록 자체가 정답 힌트가 되어 평가 오염).
  대신 결정적 별칭 테이블(`regimpact.regions.normalize_region_name`) + 경계 변환 단계
  (`regimpact.extractor.normalize_regions`)를 추가. 매핑 실패는 버리지 않고 `unmapped`로 표면화.
- **결과:** coverage 100%, Regions OK.

### D-02 열거 병합에 의한 예외 누락 — `[⚠ 미해결, 재현됨]`
- **증상:** Exception Recall 50%. 골드의 `real_demand`(서민·실수요자)를 **두 모델 모두** 놓쳤다.
- **원인:** FSC 보도자료는 "생애최초 주택구입, 정책모기지 **등**"으로 축약해 서술하고,
  FAQ(`faq_20260630.txt` L52)만 "생애최초 주담대, **서민·실수요자 주담대**, 정책모기지 등"으로
  전부 열거한다. 모델은 짧은 쪽(FSC)을 인용원으로 골라 "등"에 흡수된 항목을 잃었다.
- **시도한 조치:** 프롬프트 v2에 규칙 6("열거를 병합·축약하지 마라") + 규칙 7("문서 교차 확인,
  가장 자세한 서술 기준") 추가 → 추출 건수는 15→19로 늘었지만 **이 항목은 여전히 누락**.
- **판단:** 앵커 1건에 프롬프트를 더 맞추는 것은 과적합이자 지표 게이밍이다. 여기서 튜닝을 멈추고
  **확인된 결함으로 기록**한다. 실제 해결은 Phase 2에서 DEV 40건 전체를 상대로 진행한다.
- **왜 중요한가:** 예외 누락은 이 시스템의 **high-risk 실패 유형**이다(예외를 못 보면 규제 적용을
  과대·과소 판정). 이 프로젝트의 가치 제안("실패의 명시적 통제")이 실제로 작동한 첫 증거다.
- 후보 대책: ①문서별 개별 추출 후 union(문서 간 축약 손실 차단) ②"등/기타" 토큰 감지 시
  다른 문서에서 열거 확장 강제 ③예외 항목 전용 2차 패스.

### D-03 모델 등급에 따른 인용 환각 — `[관찰됨]`
- **증상:** haiku-4-5는 Unsupported Claim Rate **25%**(3/12). sonnet-5는 0%.
- **성격:** 인용문이 그럴듯하지만 원문에 그 문자열이 없다 — 의역·재구성한 "가짜 verbatim".
  세 건 모두 내용은 대체로 맞지만 **인용 무결성**이 깨졌다.
- **의미:** 모델 선택이 곧 리스크 프로파일 선택이다. Citation grounding 체크가 없었다면
  이 차이는 보이지 않았을 것이다(내용이 맞아 보이므로 사람 검토에서도 통과하기 쉽다).
- **조치:** 코어 실행 모델은 sonnet-5 이상으로 둔다. haiku는 비용 비교 실험용으로만 유지.

---

## 3. 재현 방법 (키·비용 없이)

```bash
# 저장된 결과 재생 — LLM 호출 0회, 완전 결정적
python examples/run_extractor.py --provider replay --run docs/eval/runs/run_cli_sonnet5_v2.json

# 실제 재실행 (Claude Code 구독으로, 별도 API 키 불필요)
python examples/run_extractor.py --provider cli --model claude-sonnet-5

# 무료 티어 교차검증
export GEMINI_API_KEY=...   # aistudio.google.com 무료 발급
python examples/run_extractor.py --provider gemini
```

`source_sha256`가 run 기록에 남으므로 원문이 바뀌면 과거 실측치와 비교가 무효임을 알 수 있다.

---

## 4. 다음 단계로 넘기는 것

- D-02를 Phase 2 extractor 튜닝의 **1순위 목표**로 등록 (DEV 40건 기준, 앵커 1건 기준 아님).
- `metrics_spec.md` 임계값 초안에 실측 근거 반영: Citation Correctness ≥ 95%(sonnet-5 실측 100%),
  Unsupported Claim Rate 상한(haiku 실측 25% = 미달 사례로 기록).
- Impact Matrix E2E 연결 시 정규화된 지역코드를 그대로 룰엔진 입력으로 사용.
