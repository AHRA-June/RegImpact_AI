# 기능단위: Audit Trail (해시 체인 감사추적)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). append-only 해시 체인 감사로그(변조 탐지) + JSONL 영속 + 시계 주입(결정론).
  구현: `src/regimpact/audit/`. Risk Register **R-GOV-01(감사추적 부재)** 를 실제로 통제.

---

## 1. 목적·책임
파이프라인 이벤트를 **tamper-evident(변조 탐지 가능)** 감사로그로 남긴다. 단순 로그가 아니라
각 항목의 해시가 직전 해시를 포함하는 **해시 체인**이라, 어느 항목을 사후 변조하면 이후 체인이
깨져 `verify()`가 잡는다. 금융권 모델검증/거버넌스의 감사추적 요건(무결성·부인방지·재현)을 충족.

## 2. 입력/출력 인터페이스
- `AuditLog(clock?)` — append-only 로그. `clock`(시각 함수) 주입 → 결정론(테스트 고정, 실사용 UTC).
- `log.record(action, target, details?, actor?, timestamp?) -> AuditEvent` — 이벤트 append + 체인 연결.
- `log.verify() -> VerifyResult(ok, problems)` — seq 연속·prev 연결·해시 재계산 일치 검증.
- `log.to_jsonl()` / `AuditLog.load_jsonl(text)` — 영속(한 줄=한 이벤트, 해시 보존).
- `Action.*` — 표준 이벤트 상수(SOURCE_INGESTED·EXTRACTION·IMPACT_ANALYZED·PROPOSAL_CREATED·
  HUMAN_REVIEW·REGRESSION_RUN·ASSURANCE_SCORED·REPORT_GENERATED).
- `AuditEvent`: seq·timestamp·actor·action·target·details·prev_hash·entry_hash.

## 3. 핵심 로직·설계 결정
- **해시 체인:** `entry_hash = sha256(prev_hash + canonical(body))`. body는 해시 필드 제외 정규화 JSON
  (sort_keys, ensure_ascii=False). 제네시스 prev_hash = "0"*64.
- **변조 탐지:** verify가 각 항목 해시를 prev로부터 재계산해 저장값과 대조 → 변조/재정렬/삭제 포착.
- **의존성 0·결정론:** 표준 라이브러리(hashlib·json)만. 시각 주입으로 재현 가능(테스트 고정 시계).
- **actor 구분:** "system" vs "human:<name>" — 사람 승인(HUMAN_REVIEW)과 자동 이벤트 분리.

## 4. 관련 파일
- `src/regimpact/audit/` — `log.py`(AuditLog·AuditEvent·verify·JSONL)
- `tests/test_audit.py` · `examples/demo_audit.py`
- 산출물: `docs/reports/audit_6_30.jsonl`(파이프라인 감사로그)

## 5. 검증 상태 (6·30)
- 파이프라인 8노드 → 10 이벤트 기록, 체인 verify ✅ OK.
- **변조 탐지 실증:** 승인 기록을 사후 반려로 위조 시 verify FAIL(seq 지목). 재정렬도 탐지.
- 테스트: `test_audit.py`(7) — 체인 연결·변조 탐지·재정렬 탐지·JSONL 왕복·결정론. 전체 135 통과.

## 6. 알려진 제약·모호성
- 해시 체인은 **내부 무결성**(사후 변조 탐지)을 보장한다. 외부 신뢰 앵커(타임스탬프 서명·외부 원장
  고정)는 범위 밖(후속). 현재는 파일 기반 append-only + verify.
- 실사용 시 각 파이프라인 실행에서 `record`를 호출하도록 오케스트레이션에 연결한다(데모가 참조 구현).
- INFRA 성격(항상 켜짐) — metric이 아님(metrics_spec §깊이 정책 [INFRA]).
