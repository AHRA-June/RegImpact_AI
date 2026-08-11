# Validation Report — E2E 검증보고서

브리프 §18 "코어 완성" 파이프라인의 **최종 노드**. 전 노드 산출물을 사람 검토용
검증보고서(Markdown)로 조립하고, 승인 상태 + audit trail을 포함한다(브리프 §16~17).

## 사용

```python
from regimpact.e2e import run_six_thirty_e2e

result = run_six_thirty_e2e()          # 오프라인 관통(canonical 추출)
print(result.report.render_markdown()) # 검증보고서
result.report.to_dict()                # 구조화(감사·UI용)
result.report.decision_status          # DRAFT / NEEDS_REVIEW
```

`build_validation_report(...)`로 개별 산출물을 직접 넘겨 조립할 수도 있다.

## 보고서 구성

1. 규제 변경 요약(RegChange + 인용 정합)
2. Impact Matrix (엔진 실측 표)
3. Rule Change Proposal (구조화 변경안 + 근거 인용)
4. 테스트 커버리지 · 회귀 · 충실성
5. Assurance Evaluation (깊은 4 dimension)
6. Human Review / Approval (결정상태 + 검토 사유 + 참고 gap)
7. Audit Trail (재현용, 브리프 §17)

## 결정상태 결합

`decision_status` = Assurance gate + proposal status 결합:
- gate REVIEW_REQUIRED → `NEEDS_REVIEW`(승인 불가)
- gate PASS → proposal status 유지(`DRAFT`, 사람 최종 승인 대기)

**자동 승인은 없다** — APPROVED는 사람만 부여하며, 그 후에야 rule registry에 반영된다.

## Audit Trail (§17)

`event_id·timestamp·policy_id·source_hash·system_version·model_name·prompt_version·
decision_status·reviewer·reviewed_at`. `source_hash`는 원문 텍스트의 sha256으로 계산해
"어떤 원문으로 만들었는지" 재현 가능하게 한다. 시각·event_id 등 비결정 값은 `ReportMeta`로
런타임 주입(테스트 재현성 보장).
