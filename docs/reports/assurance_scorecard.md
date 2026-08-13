# Assurance Scorecard (4 dimension, 확정 임계값 Strict)

**종합 판정: ✅ PASS** — 고위험(★) 지표 FAIL 시 전체 FAIL.

## Dimension 1. Source Grounding & Citation — ✅ PASS
| 지표 | 값 | 임계(Strict) | 고위험 | 판정 |
|---|---|---|---|---|
| Citation Correctness | 100% | ≥95% |  | ✅ PASS |
| Unsupported Claim Rate | 0% | ≤5% | ★ | ✅ PASS |
| Source Contradiction Rate | 0% | ≤0% | ★ | ✅ PASS |

## Dimension 2. Change & Exception Completeness — ✅ PASS
| 지표 | 값 | 임계(Strict) | 고위험 | 판정 |
|---|---|---|---|---|
| Change Completeness | 100% | ≥90% | ★ | ✅ PASS |
| Exception Recall | 100% | ≥95% | ★ | ✅ PASS |
| Grandfathering Recall | 100% | ≥95% | ★ | ✅ PASS |

## Dimension 3. Temporal / Policy-Version Consistency — ✅ PASS
| 지표 | 값 | 임계(Strict) | 고위험 | 판정 |
|---|---|---|---|---|
| Effective-date Accuracy | 100% | ≥100% | ★ | ✅ PASS |
| Region Completeness | 100% | ≥100% | ★ | ✅ PASS |
| Policy-version Consistency | 100% | ≥100% | ★ | ✅ PASS |

## Dimension 4. Rule Regression & Conflict — ✅ PASS
| 지표 | 값 | 임계(Strict) | 고위험 | 판정 |
|---|---|---|---|---|
| Rule-regression Pass Rate | 100% | ≥100% | ★ | ✅ PASS |
| Boundary-case Pass Rate | 100% | ≥100% |  | ✅ PASS |
| Conflict-case Pass Rate | 100% | ≥100% | ★ | ✅ PASS |

> 임계값 출처: `src/regimpact/assurance/thresholds.py`(확정 2026-08-13, Strict).
> 지표는 6·30 단일 앵커 기준(n=1 문서셋). 오라클은 challenger(제3자 벤치마크 아님).
