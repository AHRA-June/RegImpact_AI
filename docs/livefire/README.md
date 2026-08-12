# 라이브파이어 (Live Fire) — 브리프 §19

> **"이 도구는 실제 신규 규제를 발표 당일 처리했다."** — 시연이 아니라 실적을 남긴다.

실제 신규 부동산·가계대출 대책이 발표되면 **그날** 전 파이프라인을 돌리고,
사후 조작이 불가능하도록 **증거 패키지**(원문 해시 + 분석 timestamp + git commit +
시스템 버전 + 산출물)를 이 저장소에 커밋한다. 하네스는 `src/regimpact/livefire.py`
(`run_livefire`)이며 한 번의 호출로 증거 패키지를 남긴다.

## 상태판

| # | 사건 | 모드 | 상태 | 증거 |
|---|---|---|---|---|
| 리허설 | 6·30 규제지역 추가 지정 | REHEARSAL(예행) | ✅ 완료 | [`rehearsal_6_30/`](rehearsal_6_30/README.md) |
| Live Fire #1 | (다음 실제 대책 발표) | LIVE | ⬜ **대기** | — |

> ⚠️ **리허설은 실적이 아니다.** 6·30은 과거·골드셋 수록 사건이라 하네스가 턴키로 도는지
> 검증한 **예행연습**일 뿐이다. 실제 Live Fire #1 슬롯은 신규 정책이 나올 때까지 비워 둔다
> (정직성: 없는 실적을 있는 척하지 않는다).

## 증거 패키지 구성 (브리프 §19)

```
official source snapshot(해시로 고정) + source hash + analysis timestamp
+ git commit hash + system version + output artifact(report.html 등)
```

각 실행 폴더(`rehearsal_6_30/`, 향후 `livefire_1/` …)에:

| 파일 | 내용 |
|---|---|
| `manifest.json` | 증거 매니페스트 — 원문 해시·timestamp·commit·버전·Assurance·헤드라인·정직성 고지 |
| `README.md` | 사람이 읽는 증거 기록(§19 표기 양식) |
| `report.html` | 파이프라인 실제 출력 리포트(값 출처=엔진/추출, 하드코딩 없음) |
| `extraction.json` | 사용한 추출(입력 고정) |
| `impact_summary.json` | 임팩트·여력·민감도·룰변경안 헤드라인 수치 |

## 실제 발표일 실행 절차 (Live Fire #1)

1. **원문 확보·스냅샷** — 공식 보도자료/FAQ를 `docs/sources/original/`에 저장, `SOURCES.md`에 해시 등록.
2. **추출(실시간 LLM)** — `examples/run_extractor.py`(Gemini)로 추출 → `docs/eval/`에 원시 저장.
   (리허설은 이 단계만 저장 추출로 대체했다. 실전은 발표 당일 실측.)
3. **라이브파이어 실행** — `run_livefire(mode="LIVE", gold=None, …)`.
   신규 정책은 골드 정답지가 아직 없으므로 recall류는 미산정, grounding·룰-회귀 등 정답 불필요 지표만 보고.
   `analysis_timestamp`·`system_commit`은 생략 → 실제 now()·HEAD 기록.
4. **커밋·공개 기록** — 증거 폴더를 커밋하고 이 상태판에 행을 추가. 루트 `README.md`에도 표기.

```python
from regimpact.livefire import run_livefire
manifest = run_livefire(
    extraction=extraction, extraction_dict=extraction_dict,
    sources=sources, source_files=[(doc_id, path), ...],
    out_dir=Path("docs/livefire/livefire_1"),
    mode="LIVE", label="YYYY-MM-DD 대책", gold=None,
)
```

## 정직성 원칙

- LTV 판정은 **사람이 확정한 결정적 룰엔진** 출력이다(AI가 규칙을 만들지 않음, LOCKED §4).
- 여력 금액·민감도는 **문서화된 가정** 기반이며 실행액이 아니다(가격대별 최대한도 상한 미적용).
- 매니페스트 `system_commit`은 **분석 산출 시 HEAD** — 매니페스트는 다음 커밋으로 저장되므로
  보통 그 부모 커밋을 가리킨다(정상).
- 브리프 §19: 복잡한 "사후 조작 불가 시스템"을 별도 구현하지 않는다. 해시+timestamp+commit으로 충분.
