# Policy Version DB + Temporal Policy Resolver

브리프 §7의 질문을 구현한다.

> **"이번 정책이 시행되는 시점에, 직전까지 유효했던 정책과 무엇이 달라졌는가?"**

이 시스템은 새 문서 하나를 요약하는 것이 아니다. 그래서 정책은 문서가 아니라
**시행일 구간을 갖는 버전**이고, `supersedes` 로 이어진다.

저장소는 DB 서버가 아니라 **git 안의 JSON**(`docs/policies/*.json`)이다. 정책 버전은
감사 대상이고, git 이력이 곧 "누가 언제 무엇을 확정했는가"의 기록이 된다.

```python
from regimpact.policy import load_registry, timeline, previous_policy, preview_region_impact

registry = load_registry()
current  = current_policy(registry, date(2026, 7, 1))     # FSC_20260630
previous_policy(registry, current)                        # MOLIT_20251016
preview_region_impact(current)                            # 구리시 NON_REGULATED → REGULATED
```

파이프라인 배선: `examples/demo_impact_e2e.py` 3단계.

## 확정 전에는 판정에 쓰이지 않는다 (LOCKED §4)

업로드된 정책은 항상 `DRAFT` 로 태어난다. `resolve_region_with_policies()` 는
**CONFIRMED 만** 오버레이하므로, 초안이 규제상태를 만드는 일은 없다.

확정 전에도 `preview_region_impact()` 로 "적용하면 어떻게 되는지"는 볼 수 있다 —
전역 상태를 바꾸지 않는 순수 함수라 되돌릴 것이 없다.

`draft_policy()` 는 코드로 매핑하지 못한 지역명을 **조용히 버리지 않고** `unmapped_regions`
로 보고한다. 넘겨짚는 순간 근거 없는 규제상태가 만들어진다.

## 같은 사실이 두 곳에 산다 — 그래서 드리프트를 잡는다

| | 역할 |
|---|---|
| `regions.REGION_VERSIONS` | 엔진이 쓰는 **기준선** — 확정된 사실의 누적 결과 |
| `docs/policies/*.json` | **정책 버전 기록** — 그 사실이 어느 공문에서 언제 왔는지 + 미확정 정책 |

합치지 않은 이유는 역할이 다르기 때문이다. 문제는 조용히 갈라질 수 있다는 것이고,
한쪽만 고쳐도 테스트는 전부 통과한다. `check_registry_matches_baseline()` 이 양방향으로 본다.

- **정책 → 기준선**: 확정 정책이 말하는 상태를 기준선도 말하는가
- **기준선 → 정책**: 기준선이 출처로 지목한 정책이 실제로 등록·확정돼 있는가

시드는 `python tools/seed_policies.py` — `REGION_VERSIONS` 의 `source_policy_id` 를
정책 단위로 뒤집어 모은다. 같은 사실을 두 번 타이핑하면 반드시 갈라지므로 생성한다.

## 이식하며 고친 것

| 결함 | 증상 |
|---|---|
| `is_pending` 프로퍼티가 `status` 만 봄 | 시행 중인 정책까지 전부 '시행 예정'. 시점 없이는 답할 수 없는 질문이라 `is_pending_at(as_of)` 메서드로 |
| `preview_region_impact` 의 before/after를 같은 시점으로 조회 | 미리보기가 `REGULATED → REGULATED` 로 보여 **변화가 사라짐**. before 는 시행 전날이어야 한다 |
| 지역 코드 체계 불일치 | 원 브랜치는 `GYEONGGI_GURI`, 이 저장소는 `GURI`. JSON을 그대로 들이면 정합성 검사가 전부 미스 → 기준선에서 생성하는 쪽으로 |
