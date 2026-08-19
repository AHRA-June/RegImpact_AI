"""지역 규제상태의 시점 버전 관리 (docs/00_BRIEF.md §7, regulatory_facts.md '지역 버전').

지역 상태는 시점에 따라 달라지는 버전 데이터다. 값 출처는 사람이 확정한 공문 원문이다(LOCKED §4).

레지스트리 근거: `docs/sources/raw/molit_press_20260630.txt` p5 **참고2 「투기과열지구 및
조정대상지역 현황」** — 6·30 공문이 추가지정 前/後 전체 지정 현황표를 싣고 있어, 추정 없이
원문에서 그대로 옮길 수 있다. 지정일자는 현황표에 병기된 괄호 표기를 따른다.

  서울(25곳)  강남·서초·송파·용산('17.8.3 투기과열 / '16.11.3 조정)
              나머지 21개구('25.10.16)
  경기(12→15) 수원장안·수원팔달·수원영통·성남수정·성남중원·성남분당·안양동안·과천·
              용인수지·광명·하남·의왕('25.10.16) + 화성동탄·용인기흥·구리(6·30, '26.7.1)

현황표의 투기과열지구 열과 조정대상지역 열은 **완전히 동일**하다(모든 지정 지역이 양쪽 모두).
투기과열지구가 더 강한 규제이므로 `regulated_type` 은 투기과열지구로 해석한다.

## 미등록 지역을 UNKNOWN 으로 두는 이유

이전 구현은 미등록 지역을 NON_REGULATED 로 간주했다. 그 기본값 때문에 강남·서초·송파·용산이
비규제로 판정되어 무주택 차주가 강남에서 LTV 70%를 받았다(레지스트리에 6·30 신규 3곳만
등록돼 있었다). 결함의 본질은 누락된 데이터가 아니라 **"모르는 지역"과 "비규제 지역"을
구분하지 못하는 구조**였다 — 데이터가 빠지면 조용히 관대한 판정이 나간다.

그래서 지금은 레지스트리에 없는 코드는 UNKNOWN 이고, 룰엔진이 사람 검토로 보낸다.
비규제임이 확인된 지역은 `_KNOWN_NON_REGULATED` 에 **명시적으로** 등록한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .models import RegionStatus, RegulatedType

REG_EFFECTIVE = date(2026, 7, 1)   # 6·30 투기과열·조정 효력 (시행일)


@dataclass(frozen=True)
class RegionVersion:
    status: RegionStatus
    effective_from: Optional[date]   # None = 열림(과거)
    effective_to: Optional[date]     # None = 열림(현재)
    regulated_type: RegulatedType = RegulatedType.NONE
    source_policy_id: Optional[str] = None


# --------------------------------------------------------- 참고2 현황표 (원문 그대로)

# 강남·서초·송파·용산 — 조정대상 '16.11.3 → 투기과열 '17.8.3
_SEOUL_2016 = ("SEOUL_GANGNAM", "SEOUL_SEOCHO", "SEOUL_SONGPA", "SEOUL_YONGSAN")

# 서울 나머지 21개구 — '25.10.16 (투기과열·조정 동시)
_SEOUL_2025 = (
    "SEOUL_SEONGDONG", "SEOUL_MAPO", "SEOUL_GANGDONG", "SEOUL_YEONGDEUNGPO",
    "SEOUL_YANGCHEON", "SEOUL_DONGJAK", "SEOUL_GWANGJIN", "SEOUL_JUNG",
    "SEOUL_JONGNO", "SEOUL_SEODAEMUN", "SEOUL_GANGSEO", "SEOUL_NOWON",
    "SEOUL_SEONGBUK", "SEOUL_GURO", "SEOUL_DONGDAEMUN", "SEOUL_GWANAK",
    "SEOUL_EUNPYEONG", "SEOUL_JUNGNANG", "SEOUL_GEUMCHEON", "SEOUL_GANGBUK",
    "SEOUL_DOBONG",
)

# 경기 12곳 — '25.10.16
_GYEONGGI_2025 = (
    "SUWON_JANGAN", "SUWON_PALDAL", "SUWON_YEONGTONG",
    "SEONGNAM_SUJEONG", "SEONGNAM_JUNGWON", "SEONGNAM_BUNDANG",
    "ANYANG_DONGAN", "GWACHEON", "YONGIN_SUJI", "GWANGMYEONG",
    "HANAM", "UIWANG",
)

# 6·30 신규 지정 3곳 — '26.7.1 (이 프로젝트의 분석 대상 변경)
_SIX_THIRTY_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")

# 비규제임이 확인된 지역. UNKNOWN 과 구분하기 위해 **명시적으로** 등록한다.
#   세종·청주는 수도권이 아니고 현황표 어느 열에도 없다.
_KNOWN_NON_REGULATED = ("SEJONG", "CHEONGJU")


REGION_VERSIONS: dict[str, list[RegionVersion]] = {}

# 강남4구: 비규제 → 조정('16.11.3) → 투기과열('17.8.3)
for _code in _SEOUL_2016:
    REGION_VERSIONS[_code] = [
        RegionVersion(RegionStatus.NON_REGULATED, None, date(2016, 11, 2)),
        RegionVersion(
            RegionStatus.REGULATED, date(2016, 11, 3), date(2017, 8, 2),
            RegulatedType.ADJUSTMENT, "MOLIT_20161103",
        ),
        RegionVersion(
            RegionStatus.REGULATED, date(2017, 8, 3), None,
            RegulatedType.SPECULATIVE_OVERHEATED, "MOLIT_20170803",
        ),
    ]

for _code in _SEOUL_2025 + _GYEONGGI_2025:
    REGION_VERSIONS[_code] = [
        RegionVersion(RegionStatus.NON_REGULATED, None, date(2025, 10, 15)),
        RegionVersion(
            RegionStatus.REGULATED, date(2025, 10, 16), None,
            RegulatedType.SPECULATIVE_OVERHEATED, "MOLIT_20251016",
        ),
    ]

for _code in _SIX_THIRTY_REGIONS:
    REGION_VERSIONS[_code] = [
        RegionVersion(RegionStatus.NON_REGULATED, None, date(2026, 6, 30)),
        RegionVersion(
            RegionStatus.REGULATED, REG_EFFECTIVE, None,
            RegulatedType.SPECULATIVE_OVERHEATED, "FSC_20260630",
        ),
    ]

for _code in _KNOWN_NON_REGULATED:
    REGION_VERSIONS[_code] = [
        RegionVersion(RegionStatus.NON_REGULATED, None, None),
    ]


def resolve_region_status(
    region_code: str, as_of: date
) -> tuple[RegionStatus, RegulatedType]:
    """특정 시점의 지역 규제상태를 반환.

    레지스트리에 없는 코드는 **UNKNOWN** 이다. NON_REGULATED 로 대신 돌려주면
    데이터 누락이 관대한 판정으로 조용히 새어나간다(모듈 docstring 참조).
    """
    if region_code not in REGION_VERSIONS:
        return RegionStatus.UNKNOWN, RegulatedType.NONE
    for v in REGION_VERSIONS[region_code]:
        after_start = v.effective_from is None or as_of >= v.effective_from
        before_end = v.effective_to is None or as_of <= v.effective_to
        if after_start and before_end:
            return v.status, v.regulated_type
    return RegionStatus.UNKNOWN, RegulatedType.NONE


# --------------------------------------------------------------- 수도권 여부
#
# 왜 필요한가: 6·30 공문의 다주택 규칙은 **지역 규제상태가 아니라 수도권 여부**로 갈린다.
#   FSC 보도참고자료 p2 / FAQ Q1 ※: "다주택자는 수도권 內 주택구입시 **규제지역 여부와 무관하게**
#   LTV 0% 적용"
# 따라서 REGULATED/NON_REGULATED 축만으로는 이 규칙을 표현할 수 없다.
#
# 수도권 = 서울·인천·경기 (｢수도권정비계획법｣ 제2조). 세종·청주 등은 수도권이 아니다.
CAPITAL_AREA_REGIONS: frozenset[str] = frozenset(
    {"SEOUL", "INCHEON"}                      # 광역 표기(시군구 미상)도 수도권은 확실하다
    | set(_SEOUL_2016) | set(_SEOUL_2025)     # 서울 25개 자치구
    | set(_GYEONGGI_2025)                     # 경기 12곳
    | set(_SIX_THIRTY_REGIONS)                # 경기 3곳 (6·30 신규)
)


def is_capital_area(region_code: str) -> bool:
    """수도권(서울·인천·경기) 여부. 미등록 지역은 **수도권 아님**으로 간주한다.

    보수적 기본값이다: 수도권으로 잘못 간주하면 0% 자동판정이 잘못 내려가지만,
    수도권이 아니라고 보면 기준값 부재로 사람 검토(escalation)로 빠진다.
    """
    return region_code in CAPITAL_AREA_REGIONS


# --------------------------------------------------------------- 명칭 → 코드 정규화
#
# LLM 추출기는 공문 원문의 **한글 지역명**("화성시 동탄구")을 내놓지만 룰엔진은
# **코드**("HWASEONG_DONGTAN")로 동작한다. 이 경계를 LLM에게 맡기면(프롬프트에 코드
# 어휘를 주면) 정답 후보를 흘리는 셈이 되므로, **결정적 별칭 테이블**로 변환한다.
# 매칭 실패는 조용히 버리지 않고 None을 돌려 호출측이 escalate 하게 한다.
#
# 이 표는 규제 "값"이 아니라 식별자 별칭이다(LOCKED §4의 규칙값 범위 밖). 신규 지역이
# 등장하면 여기에 추가한다.
_SEOUL_GU = {
    "종로": "SEOUL_JONGNO", "중": "SEOUL_JUNG", "용산": "SEOUL_YONGSAN",
    "성동": "SEOUL_SEONGDONG", "광진": "SEOUL_GWANGJIN", "동대문": "SEOUL_DONGDAEMUN",
    "중랑": "SEOUL_JUNGNANG", "성북": "SEOUL_SEONGBUK", "강북": "SEOUL_GANGBUK",
    "도봉": "SEOUL_DOBONG", "노원": "SEOUL_NOWON", "은평": "SEOUL_EUNPYEONG",
    "서대문": "SEOUL_SEODAEMUN", "마포": "SEOUL_MAPO", "양천": "SEOUL_YANGCHEON",
    "강서": "SEOUL_GANGSEO", "구로": "SEOUL_GURO", "금천": "SEOUL_GEUMCHEON",
    "영등포": "SEOUL_YEONGDEUNGPO", "동작": "SEOUL_DONGJAK", "관악": "SEOUL_GWANAK",
    "서초": "SEOUL_SEOCHO", "강남": "SEOUL_GANGNAM", "송파": "SEOUL_SONGPA",
    "강동": "SEOUL_GANGDONG",
}

REGION_ALIASES: dict[str, str] = {
    # 서울 25개 자치구 — "강남구" / "서울 강남" 두 표기 모두
    **{f"{n}구": c for n, c in _SEOUL_GU.items()},
    **{f"서울 {n}": c for n, c in _SEOUL_GU.items()},
    "서울특별시": "SEOUL",
    "인천광역시": "INCHEON",
    # 경기 15곳 — 공문 현황표 표기("수원장안")와 행정 표기("수원시 장안구") 양쪽
    "수원시 장안구": "SUWON_JANGAN", "수원장안": "SUWON_JANGAN",
    "수원시 팔달구": "SUWON_PALDAL", "수원팔달": "SUWON_PALDAL",
    "수원시 영통구": "SUWON_YEONGTONG", "수원영통": "SUWON_YEONGTONG",
    "성남시 수정구": "SEONGNAM_SUJEONG", "성남수정": "SEONGNAM_SUJEONG",
    "성남시 중원구": "SEONGNAM_JUNGWON", "성남중원": "SEONGNAM_JUNGWON",
    "성남시 분당구": "SEONGNAM_BUNDANG", "성남분당": "SEONGNAM_BUNDANG",
    "분당구": "SEONGNAM_BUNDANG",
    "안양시 동안구": "ANYANG_DONGAN", "안양동안": "ANYANG_DONGAN",
    "과천시": "GWACHEON",
    "용인시 수지구": "YONGIN_SUJI", "용인수지": "YONGIN_SUJI",
    "광명시": "GWANGMYEONG",
    "하남시": "HANAM",
    "의왕시": "UIWANG",
    "구리시": "GURI", "구리": "GURI",
    "용인시 기흥구": "YONGIN_GIHEUNG", "기흥구": "YONGIN_GIHEUNG",
    "용인기흥": "YONGIN_GIHEUNG",
    "화성시 동탄구": "HWASEONG_DONGTAN", "동탄구": "HWASEONG_DONGTAN",
    "화성동탄": "HWASEONG_DONGTAN",
    # 비수도권 대조군
    "세종특별자치시": "SEJONG", "세종시": "SEJONG",
    "청주시": "CHEONGJU",
}

_ALIAS_STRIP = ("경기도", "경기", "인천광역시", "서울시", "특별자치시", "광역시")


def normalize_region_name(name: str) -> Optional[str]:
    """공문 표기 지역명을 룰엔진 지역코드로 변환한다. 모르면 None.

    이미 코드 형태("GURI")로 들어오면 그대로 통과시킨다. 광역 접두어("경기도 ")는
    떼고 매칭하며, 그래도 못 찾으면 별칭 키가 포함된 항목을 마지막으로 시도한다.
    """
    if not name:
        return None
    raw = name.strip()
    if raw in REGION_VERSIONS or (raw.isascii() and raw.isupper()):
        return raw

    cleaned = raw
    for prefix in _ALIAS_STRIP:
        cleaned = cleaned.replace(prefix, " ")
    cleaned = " ".join(cleaned.split())

    for candidate in (raw, cleaned):
        if candidate in REGION_ALIASES:
            return REGION_ALIASES[candidate]

    # 부분 포함(예: "경기도 화성시 동탄구 일원") — 가장 긴 별칭을 우선 매칭
    for alias in sorted(REGION_ALIASES, key=len, reverse=True):
        if alias in cleaned:
            return REGION_ALIASES[alias]
    return None


# --------------------------------------------------------------- 코드 정규화 · 표기
def canonical_code(name_or_code: str) -> str:
    """지역 표기를 코드로 정규화한다. 알 수 없으면 **입력을 그대로 돌려준다**.

    `normalize_region_name` 은 모르면 None 을 주지만(호출측이 escalate 하도록),
    여기서는 코드 자리에 쓸 문자열이 필요한 경우를 위해 통과시킨다. 정규화 실패는
    `resolve_region_status` 가 UNKNOWN 으로 잡으므로 관대해지지 않는다.
    """
    return normalize_region_name(name_or_code) or name_or_code


def _build_labels() -> dict[str, str]:
    """코드 → 한글 표기. 별칭표를 뒤집되 행정 표기('강남구'·'과천시')를 우선한다."""
    out: dict[str, str] = {}
    for alias, code in REGION_ALIASES.items():
        cur = out.get(code)
        better = (
            cur is None
            or (alias.endswith(("구", "시")) and not cur.endswith(("구", "시")))
            or (alias.endswith(("구", "시")) == cur.endswith(("구", "시")) and len(alias) > len(cur))
        )
        if better:
            out[code] = alias
    return out


REGION_LABELS: dict[str, str] = _build_labels()


def region_label(region_code: str) -> str:
    """코드의 한글 표기. 모르는 코드는 코드 그대로."""
    return REGION_LABELS.get(canonical_code(region_code), region_code)
