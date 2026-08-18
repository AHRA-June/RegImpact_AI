"""추출 골드(regchange_gold_6_30.json) v2 — 인용을 붙여 검수 가능하게 만든다.

v2 최초 작성 시에는 id·categories·keywords만 있었다. 그러면 사람이 각 항목을 검수하려면
원문을 직접 뒤져야 하고, 인용이 원문에 실제로 있는지 기계가 확인할 수도 없다.
QA 골드와 같은 대우를 한다 — **인용은 손으로 옮기지 않고 원문에서 잘라 온다**(`q`).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from tools.author_goldset import FAQ, FSC, MOLIT, q  # noqa: E402

C = lambda doc, anchor, n=90, **kw: {  # noqa: E731
    "source_doc_id": q(doc, anchor, n, **kw).source_doc_id,
    "quote": q(doc, anchor, n, **kw).quote,
}

# (id, categories, keywords, claim, citations, transition)
# transition이 있으면 키워드 대신 항목의 before/after 필드를 직접 대조한다.
# "70%가 어딘가에 있다"와 "70%에서 40%로 바뀌었다"는 다른 주장이고, 이 제품의 핵심은 후자다.
REQUIRED = [
    ("LTV_REGULATED_40", ["LTV"], ["40%"], "규제지역 일반 LTV 70% → 40%",
     [C(FSC, "규제지역 내 주담대 취급시 LTV 강화", 60),
      C(MOLIT, "LTV : 무주택(처분조건부 1주택 포함) 40%, 유주택 0%", 50)],
     {"before": "70%", "after": "40%"}),
    ("LTV_BASELINE_70", ["LTV"], ["70%"], "지정 전 기준선이 70%임을 before로 명시",
     [C(FSC, "규제지역 내 주담대 취급시 LTV 강화", 60)],
     {"before": "70%"}),
    ("LTV_OWNER_0", ["EXCEPTION", "LTV"], ["유주택"], "규제지역 유주택 LTV 0%",
     [C(MOLIT, "LTV : 무주택(처분조건부 1주택 포함) 40%, 유주택 0%", 50)],
     {"after": "0%"}),
    ("LTV_MULTI_0", ["EXCEPTION", "LTV"], ["다주택"], "수도권 다주택 0% (규제 여부 무관)",
     [C(FSC, "다주택자는 수도권 內 주택구입시 규제지역 여부와 무관하게 LTV 0% 적용")], None),
    ("EFFECTIVE_7_1", ["EFFECTIVE_DATE"], ["7.1", "7월 1일", "2026-07-01"], "대출규제 시행일 7.1",
     [C(MOLIT, "투기과열지구와 조정대상지역을 추가 지정하였다.(7월 1일부터 지정효력 발생)")], None),
    ("LAND_PERMIT_EFFECTIVE_7_5", ["EFFECTIVE_DATE"], ["7.5", "7월 5일", "2026-07-05"],
     "토지거래허가구역 효력일 7.5 (대출규제와 다름)",
     [C(MOLIT, "구리시를 2026년 7월 5일*부터 2027년 12월 31일까지 토지거래허가")], None),
    ("REGION_DESIGNATION", ["REGION"], ["투기과열", "조정대상"], "3곳 투기과열·조정대상 지정",
     [C(MOLIT, "경기도 화성시 동탄구, 용인시 기흥구, 구리시 등 3곳을")], None),
    ("GF_GENERAL", ["GRANDFATHERING"], ["계약금"], "일반 주담대 경과규정 (접수 또는 계약+계약금)",
     [C(FAQ, "(일반 주담대) 규제지역 효력 발생일 전일(6.30일)까지 금융회사 전산상", 140)], None),
    ("GF_LAND_PERMIT", ["GRANDFATHERING"], ["토지거래허가"], "토허제 주택 경과규정 (허가 신청 접수)",
     [C(FAQ, "* 단, 토지거래허가제 적용 주택의 경우, 규제지역 효력 발생일 전일(6.30일)까지", 150)], None),
    ("GF_GROUP_LOAN", ["GRANDFATHERING"], ["집단대출", "입주자모집"], "집단대출 경과규정 (입주자모집공고 등)",
     [C(FAQ, "(집단대출) 규제지역 효력 발생일 전일(6.30일)까지 입주자모집", 150)], None),
    ("SCOPE_JEONSE", ["SCOPE_LIMIT"], ["3억원 초과 APT", "3억초과 APT"], "전세대출 제한 (3억 초과 APT)",
     [C(FSC, "(전세대출) 전세대출 보유 차주의 규제지역 내 3억원 초과 APT 취득과 규제", 110)], None),
    ("SCOPE_CREDIT", ["SCOPE_LIMIT"], ["신용대출"], "1억 초과 신용대출 보유자 1년 제한",
     [C(FSC, "(신용대출) 1억원 초과 신용대출을 보유한 차주에 대해 대출실행일로부터", 90)], None),
    ("SCOPE_INTERIM", ["SCOPE_LIMIT"], ["중도금·이주비대출", "중도금·이주비 대출"],
     "중도금·이주비 대출 시 추가구입 제한",
     [C(FSC, "(중도금·이주비 대출) 규제지역 내 1주택 보유자가 해당 주택 재건축·재개발로", 110)], None),
    ("SCOPE_BUSINESS", ["SCOPE_LIMIT"], ["여타 사업자", "사업자대출 제한"], "사업자대출 제한",
     [C(FSC, "(사업자대출) 주택 매매·임대사업자* 외 여타 사업자도 규제지역 내 주택구입", 100)], None),
    ("MAX_LIMIT_6", ["LTV", "SCOPE_LIMIT"], ["최대한도 6억", "6억원 제한", "6억원 한도"],
     "최대한도 6억원 제한",
     [C(MOLIT, "- 최대한도 6억원 제한*, 6개월 이내 전입의무 부과, 최대 만기 30년이내", 60)], None),
    ("MOVE_IN_DUTY", ["LTV", "SCOPE_LIMIT"], ["전입"], "6개월 이내 전입의무",
     [C(MOLIT, "- 최대한도 6억원 제한*, 6개월 이내 전입의무 부과, 최대 만기 30년이내", 60)], None),
]

EXCEPTIONS = [
    ("first_home_buyer", ["생애최초"], "생애최초 (세대원 전원 무주택 이력)",
     [C(FAQ, "주4) 세대 구성원 모두가 과거에 주택을 소유한 사실이 없는 자")]),
    ("real_demand", ["서민", "실수요"], "서민·실수요자 (소득·주택가격·무주택 요건)",
     [C(FAQ, "주5) ①부부합산 연소득 9천만원 이하", 80)]),
    ("policy_mortgage", ["정책모기지", "디딤돌", "보금자리"], "정책모기지 (Discovery — 상품별)",
     [C(FAQ, "보금자리론 아파트70% / 非아파트65% 아파트60% / 非아파트55%", 60)]),
    ("disposal_condition", ["처분조건부"], "처분조건부 1주택 (무주택 기준 취급)",
     [C(FAQ, "주1) 무주택자(처분조건부 1주택자 포함) 기준")]),
]

payload = {
    "_note": "6·30 RegChange 추출 골드 정답지 — DEV 등급(튜닝 사용). 봉인된 QA split과 별개다.",
    "_scoring": "keywords는 동의 표현 대안이며 하나만 맞아도 히트다. 여러 사실을 한 entry에 묶지 않는다. 매칭 대상은 추출 항목의 summary/before/after이며 citation은 채점에 쓰지 않는다.",
    "_limitation": "키워드가 항목 전체를 훑으므로 한 항목이 두 entry의 키워드를 함께 담으면 둘 다 히트로 잡힌다. 항목 단위 1:1 대응은 검증하지 않는다.",
    "_version": "v3 (2026-08-18) — 검수 중 측정 품질 정비. ①예외 3건을 required_changes에서 제거(exceptions와 동일 키워드로 이중 측정) ②값 전이는 transition으로 before/after 직접 대조 ③광범위 키워드 4건 축소(SCOPE_JEONSE 17건→5건 매칭 등). 엄격해진 뒤에도 Completeness/Exception Recall 100% 유지 — 기존 100%가 느슨한 키워드 덕이 아니었음을 뜻한다. required 19→16이므로 v2.1 수치와 분모가 다르다.",
    "_review": "전 항목 🤖 ai_draft. 인용은 원문에서 기계적으로 잘라 왔으므로 verbatim이 보장되지만, **그 인용이 그 주장을 뒷받침하는지**는 사람 검수 대상이다. 검수표: docs/eval/GOLD_V2_REVIEW.md",
    "authored_by": "ai_draft",
    "policy_id": "FSC_20260630",
    "effective_from": "2026-07-01",
    "target_regions": ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
    "required_changes": [
        {"id": i, "categories": c, "keywords": k, "claim": claim, "citations": cits,
         **({"transition": tr} if tr else {})}
        for i, c, k, claim, cits, tr in REQUIRED
    ],
    "exceptions": [
        {"name": n, "keywords": k, "claim": claim, "citations": cits}
        for n, k, claim, cits in EXCEPTIONS
    ],
}

out = REPO / "docs" / "eval" / "regchange_gold_6_30.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(REQUIRED)} required + {len(EXCEPTIONS)} exceptions → {out.relative_to(REPO)}")
