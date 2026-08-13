# 기능단위: Rule Change Proposal + Human Review

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현: `src/regimpact/proposal/`.)

---

## 1. 목적·책임
규제 변경을 **여신 룰 변경 초안(구조화)**으로 전환한다(Walking Skeleton [4]).
LOCKED §4 "AI초안→사람확정": 제안은 **초안(PENDING_REVIEW)**으로 나오고,
사람 검토([7] Human Review)가 `approval` envelope로 확정한다. 제안 값은 **ImpactMatrix에서만
유도** → 하드코딩 없음, 엔진과 항상 일치.

## 2. 입력/출력 인터페이스
- `build_proposal(matrix, extraction?, proposal_id?) -> RuleChangeProposal`
- `record_decision(proposal, status, reviewer?, note?, reviewed_at?) -> RuleChangeProposal`
  — [7] Human Review. 본문(lines) 불변, approval만 갱신, 새 객체 반환.
- `RuleChangeProposal`: `proposal_id`, `policy_id`, `effective_from`, `target_regions[]`,
  `lines[]`, `approval`(ReviewDecision), `review_required_lines`, `summary()`.
- `RuleChangeLine`: `segment_id/label`, `rule_id`, `before_ltv`, `after_ltv`, `direction`,
  `delta_ltv`, `reason_codes`, `source_policy_ids`, `needs_review`, `note`.
- `ApprovalStatus`: PENDING_REVIEW / APPROVED / REJECTED / CHANGES_REQUESTED.

## 3. 핵심 로직·설계 결정
- **유도(하드코딩 0):** 각 line은 ImpactMatrix row에서 `rule_id/before/after/reason/source`를 가져옴.
- **초안 기본값:** `approval.status = PENDING_REVIEW`(사람 확정 전).
- **escalation 표시:** REVIEW 방향 세그먼트(非규제 유주택 등)는 `needs_review=True`.
- **원본 불변:** `record_decision`은 frozen line을 복사해 새 제안 반환(감사 추적 친화).

## 4. 관련 파일
- `src/regimpact/proposal/` — `schema.py`(RuleChangeProposal/Line/ApprovalStatus/ReviewDecision),
  `builder.py`(build_proposal, record_decision)
- `tests/test_proposal.py` · E2E 데모 `examples/demo_e2e.py`

## 5. 검증 상태
- `tests/test_proposal.py` — 7건(전체 72 통과에 포함):
  초안 기본값, 매트릭스 일치, escalation 플래그, id 유도, 요약, 승인/반려·원본 불변.

## 6. 알려진 제약·모호성
- 현재 제안 단위 = 세그먼트(라인). 룰 파라미터 표(규제지역 LTV 테이블) 단위 집계는 후속 옵션.
- approval envelope = INFRA(항상 켜짐, `metrics_spec.md`). Escalation 지표 정량화는 Phase 3.
