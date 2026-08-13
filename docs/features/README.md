# 기능단위(feature-unit) 문서 인덱스

> 각 기능/워크플로우의 **버전별 스냅샷**을 모아둔다. 관리 규칙은 **[`_VERSIONING.md`](./_VERSIONING.md)**.
> 최신 버전 = 각 폴더에서 가장 큰 `vN`. 폴더별 `CHANGELOG.md`가 이력을 누적한다.

## 기능단위
| 기능 | 폴더 | 최신 | 상태 |
|---|---|---|---|
| Deterministic LTV 룰엔진 | [`rule-engine/`](./rule-engine/rule-engine_v1.md) | v1 | ✅ |
| RegChange Extractor(E) + Citation Assurance(A) | [`extractor-assurance/`](./extractor-assurance/extractor-assurance_v4.md) | v4 | ✅ 무료 LLM 지원 |
| RAG / Retrieval 층 | [`retrieval/`](./retrieval/retrieval_v1.md) | v1 | ✅ BM25 + recall@k |
| TC Generator + Rule-Regression | [`tc-generator/`](./tc-generator/tc-generator_v3.md) | v3 | ✅ 격자 3,200건 통계 |
| Impact Matrix (시행 전/후) | [`impact-matrix/`](./impact-matrix/impact-matrix_v1.md) | v1 | ✅ |
| Impact Matrix UI 렌더 | [`ui-render/`](./ui-render/ui-render_v1.md) | v1 | ✅ |
| Rule Change Proposal + Human Review | [`rule-proposal/`](./rule-proposal/rule-proposal_v1.md) | v1 | ✅ |
| Assurance Scorecard (4 dimension + 임계값) | [`assurance-scorecard/`](./assurance-scorecard/assurance-scorecard_v1.md) | v1 | ✅ 12/12 PASS |
| Audit Trail (해시 체인) | [`audit-trail/`](./audit-trail/audit-trail_v1.md) | v1 | ✅ 변조 탐지 |
| Validation Report (검증보고서) | [`validation-report/`](./validation-report/validation-report_v3.md) | v3 | ✅ 정식 서사(17쪽) |

## 워크플로우
| 워크플로우 | 폴더 | 최신 | 상태 |
|---|---|---|---|
| E2E 파이프라인 (Walking Skeleton) | [`workflow-e2e/`](./workflow-e2e/workflow-e2e_v7.md) | v7 | ✅ 코어 완성([8] 정식 서사 17쪽) |

## 규칙 요약 (상세는 `_VERSIONING.md`)
- 수정 시 **새 버전 파일 생성**(이전 버전 보존, 덮어쓰기·삭제 금지).
- 새 파일 상단에 **이전 대비 변경(before→after) 모두** 기입 + 폴더 `CHANGELOG.md`에 누적.
- PRD도 동일 규칙(`docs/prd/<slug>/<slug>_vN.md`).
