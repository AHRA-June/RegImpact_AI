"""지역 규제상태 레지스트리 — 시점 버전 데이터 (브리프 §7, regulatory_facts '지역 버전').

## 이 파일의 권위 근거
`docs/sources/raw/molit_press_20260630.txt` **참고2 "투기과열지구 및 조정대상지역 현황"** 표.
원문은 6·30 추가지정 **전(6월말)** 과 **후(7월 1일 이후)** 를 나란히 싣고 있으며, 그대로 옮기면:

    [추가지정 전]  서울 25곳 / 경기 12곳
    [추가지정 후]  서울 25곳 / 경기 15곳  (+ 화성동탄·용인기흥·구리)

    서울(25곳)  강남·서초·송파·용산(투기과열 '17.8.3 / 조정 '16.11.3)
                성동·마포·강동·영등포·양천·동작·광진·중·종로·서대문·강서·노원·
                성북·구로·동대문·관악·은평·중랑·금천·강북·도봉('25.10.16)
    경기(12곳)  수원장안·수원팔달·수원영통·성남수정·성남중원·성남분당·
                안양동안·과천·용인수지·광명·하남·의왕('25.10.16)

## 열거주의 — 무엇이 '확정 사실'인가
규제지역은 **지정된 곳만 규제지역**이다(열거주의). 따라서 이 레지스트리에서 권위를 갖는 것은
**규제지역 목록과 그 효력일**뿐이고, 나머지 전국 시·군·구는 "지정된 바 없음 = NON_REGULATED"이다.
비규제 지역 목록은 사용자가 고를 수 있게 하기 위한 **편의 목록**이며 판정에 영향을 주지 않는다.
(그래서 비규제 목록에 빠진 지역이 있어도 규제 판정은 틀리지 않는다 — 대신 UNKNOWN으로 escalate된다.)

## 미등록 코드는 왜 NON_REGULATED가 아니라 UNKNOWN인가
이전 버전은 레지스트리에 없는 코드를 조용히 NON_REGULATED로 간주했다. 그 결과 `SEOUL_GANGNAM`이
**규제지역인데도 비규제 기준선 70%로 판정**되는 사고가 났다(2026-08-18 발견). 조용한 기본값은
틀린 답을 정답처럼 내놓는다. 이제 미등록 코드는 `RegionStatus.UNKNOWN` → 엔진이 사람에게 넘긴다.

## 수도권 플래그
`capital_area`는 판정에 **아직 쓰이지 않는다**. 확정 명세(05_RULE_SPEC §C-2)가 비규제 유주택 기준값을
정의하지 않았기 때문이다. MOLIT 참고1에 "非규제지역(수도권 外) ... 유주택 60%"가 있으나 사람 확정 전이라
채택하지 않았다(`03_OPEN_QUESTIONS.md` Q9). 확정되면 이 플래그가 분기 조건이 된다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .models import RegionStatus, RegulatedType

# --- 효력일 (regulatory_facts C02/C03) ---
REG_EFFECTIVE = date(2026, 7, 1)          # 6·30 신규 지정 3곳의 지정효력 발생일
SIX_THIRTY_CUTOFF = date(2026, 6, 30)     # 그 전일 (비규제 마지막 날)
_SEOUL_ADJ_2016 = date(2016, 11, 3)       # 강남4구 조정대상지역 지정
_SEOUL_SPEC_2017 = date(2017, 8, 3)       # 강남4구 투기과열지구 지정
_WIDE_2025 = date(2025, 10, 16)           # 서울 21구 + 경기 12곳 지정

SRC_MOLIT = "MOLIT_20260630"
SRC_FSC = "FSC_20260630"


@dataclass(frozen=True)
class RegionVersion:
    """한 지역의 특정 기간 규제상태. effective_from/to 는 닫힌 구간(양끝 포함), None = 열림."""
    status: RegionStatus
    effective_from: Optional[date]
    effective_to: Optional[date]
    regulated_type: RegulatedType = RegulatedType.NONE
    source_policy_id: Optional[str] = None


@dataclass(frozen=True)
class Region:
    code: str
    sido: str
    name: str
    capital_area: bool                 # 수도권(서울·경기·인천) 여부
    versions: tuple[RegionVersion, ...]

    @property
    def label(self) -> str:
        return f"{self.sido} {self.name}"


# ---------------------------------------------------------------------------
# 버전 템플릿
# ---------------------------------------------------------------------------
def _always_non_regulated() -> tuple[RegionVersion, ...]:
    return (RegionVersion(RegionStatus.NON_REGULATED, None, None),)


def _regulated_since(d: date, rtype: RegulatedType, src: str) -> tuple[RegionVersion, ...]:
    return (
        RegionVersion(RegionStatus.NON_REGULATED, None, date.fromordinal(d.toordinal() - 1)),
        RegionVersion(RegionStatus.REGULATED, d, None, rtype, src),
    )


def _gangnam4_versions() -> tuple[RegionVersion, ...]:
    """강남·서초·송파·용산 — 조정대상지역('16.11.3) 후 투기과열지구('17.8.3)로 강화.

    LTV 코어 판정은 REGULATED 2값으로 충분하지만, DTI 참고값(투기과열 40 / 조정 50)이
    regulated_type 에 걸리므로 두 구간을 나눠 둔다.
    """
    return (
        RegionVersion(RegionStatus.NON_REGULATED, None,
                      date.fromordinal(_SEOUL_ADJ_2016.toordinal() - 1)),
        RegionVersion(RegionStatus.REGULATED, _SEOUL_ADJ_2016,
                      date.fromordinal(_SEOUL_SPEC_2017.toordinal() - 1),
                      RegulatedType.ADJUSTMENT, SRC_MOLIT),
        RegionVersion(RegionStatus.REGULATED, _SEOUL_SPEC_2017, None,
                      RegulatedType.SPECULATIVE_OVERHEATED, SRC_MOLIT),
    )


def _six_thirty_versions() -> tuple[RegionVersion, ...]:
    """6·30 신규 지정 3곳 — 6.30까지 비규제(수도권), 7.1부터 투기과열지구."""
    return (
        RegionVersion(RegionStatus.NON_REGULATED, None, SIX_THIRTY_CUTOFF),
        RegionVersion(RegionStatus.REGULATED, REG_EFFECTIVE, None,
                      RegulatedType.SPECULATIVE_OVERHEATED, SRC_FSC),
    )


# ---------------------------------------------------------------------------
# 규제지역 (✅ 원문 참고2 표 — 이 목록이 이 파일의 권위)
# ---------------------------------------------------------------------------
_SEOUL = "서울특별시"
_GYEONGGI = "경기도"

_SEOUL_GANGNAM4 = [("강남구", "GANGNAM"), ("서초구", "SEOCHO"),
                   ("송파구", "SONGPA"), ("용산구", "YONGSAN")]

_SEOUL_2025 = [
    ("성동구", "SEONGDONG"), ("마포구", "MAPO"), ("강동구", "GANGDONG"),
    ("영등포구", "YEONGDEUNGPO"), ("양천구", "YANGCHEON"), ("동작구", "DONGJAK"),
    ("광진구", "GWANGJIN"), ("중구", "JUNG"), ("종로구", "JONGNO"),
    ("서대문구", "SEODAEMUN"), ("강서구", "GANGSEO"), ("노원구", "NOWON"),
    ("성북구", "SEONGBUK"), ("구로구", "GURO"), ("동대문구", "DONGDAEMUN"),
    ("관악구", "GWANAK"), ("은평구", "EUNPYEONG"), ("중랑구", "JUNGNANG"),
    ("금천구", "GEUMCHEON"), ("강북구", "GANGBUK"), ("도봉구", "DOBONG"),
]

_GYEONGGI_2025 = [
    ("수원시 장안구", "SUWON_JANGAN"), ("수원시 팔달구", "SUWON_PALDAL"),
    ("수원시 영통구", "SUWON_YEONGTONG"), ("성남시 수정구", "SEONGNAM_SUJEONG"),
    ("성남시 중원구", "SEONGNAM_JUNGWON"), ("성남시 분당구", "SEONGNAM_BUNDANG"),
    ("안양시 동안구", "ANYANG_DONGAN"), ("과천시", "GWACHEON"),
    ("용인시 수지구", "YONGIN_SUJI"), ("광명시", "GWANGMYEONG"),
    ("하남시", "HANAM"), ("의왕시", "UIWANG"),
]

# 6·30 신규 지정 (7.1 효력)
_GYEONGGI_SIX_THIRTY = [
    ("화성시 동탄", "HWASEONG_DONGTAN"),
    ("용인시 기흥구", "YONGIN_GIHEUNG"),
    ("구리시", "GURI"),
]

# ---------------------------------------------------------------------------
# 비규제 지역 (편의 목록 — 지정된 바 없음. 판정에 영향 없음)
# ---------------------------------------------------------------------------
_NON_REGULATED_BY_SIDO: dict[tuple[str, bool], list[tuple[str, str]]] = {
    (_GYEONGGI, True): [
        ("수원시 권선구", "SUWON_GWONSEON"), ("용인시 처인구", "YONGIN_CHEOIN"),
        ("안양시 만안구", "ANYANG_MANAN"), ("고양시 덕양구", "GOYANG_DEOKYANG"),
        ("고양시 일산동구", "GOYANG_ILSANDONG"), ("고양시 일산서구", "GOYANG_ILSANSEO"),
        ("부천시", "BUCHEON"), ("안산시 상록구", "ANSAN_SANGNOK"),
        ("안산시 단원구", "ANSAN_DANWON"), ("남양주시", "NAMYANGJU"),
        ("화성시(동탄 외)", "HWASEONG_ETC"), ("평택시", "PYEONGTAEK"),
        ("시흥시", "SIHEUNG"), ("파주시", "PAJU"), ("김포시", "GIMPO"),
        ("광주시", "GWANGJU_SI"), ("군포시", "GUNPO"), ("오산시", "OSAN"),
        ("이천시", "ICHEON"), ("양주시", "YANGJU"), ("안성시", "ANSEONG"),
        ("포천시", "POCHEON"), ("의정부시", "UIJEONGBU"), ("여주시", "YEOJU"),
        ("동두천시", "DONGDUCHEON"), ("가평군", "GAPYEONG"), ("양평군", "YANGPYEONG"),
        ("연천군", "YEONCHEON"),
    ],
    ("인천광역시", True): [
        ("중구", "JUNG"), ("동구", "DONG"), ("미추홀구", "MICHUHOL"),
        ("연수구", "YEONSU"), ("남동구", "NAMDONG"), ("부평구", "BUPYEONG"),
        ("계양구", "GYEYANG"), ("서구", "SEO"), ("강화군", "GANGHWA"),
        ("옹진군", "ONGJIN"),
    ],
    ("부산광역시", False): [
        ("중구", "JUNG"), ("서구", "SEO"), ("동구", "DONG"), ("영도구", "YEONGDO"),
        ("부산진구", "BUSANJIN"), ("동래구", "DONGNAE"), ("남구", "NAM"), ("북구", "BUK"),
        ("해운대구", "HAEUNDAE"), ("사하구", "SAHA"), ("금정구", "GEUMJEONG"),
        ("강서구", "GANGSEO"), ("연제구", "YEONJE"), ("수영구", "SUYEONG"),
        ("사상구", "SASANG"), ("기장군", "GIJANG"),
    ],
    ("대구광역시", False): [
        ("중구", "JUNG"), ("동구", "DONG"), ("서구", "SEO"), ("남구", "NAM"),
        ("북구", "BUK"), ("수성구", "SUSEONG"), ("달서구", "DALSEO"),
        ("달성군", "DALSEONG"), ("군위군", "GUNWI"),
    ],
    ("광주광역시", False): [
        ("동구", "DONG"), ("서구", "SEO"), ("남구", "NAM"), ("북구", "BUK"),
        ("광산구", "GWANGSAN"),
    ],
    ("대전광역시", False): [
        ("동구", "DONG"), ("중구", "JUNG"), ("서구", "SEO"),
        ("유성구", "YUSEONG"), ("대덕구", "DAEDEOK"),
    ],
    ("울산광역시", False): [
        ("중구", "JUNG"), ("남구", "NAM"), ("동구", "DONG"), ("북구", "BUK"),
        ("울주군", "ULJU"),
    ],
    ("세종특별자치시", False): [("세종시", "SEJONG")],
    ("강원특별자치도", False): [
        ("춘천시", "CHUNCHEON"), ("원주시", "WONJU"), ("강릉시", "GANGNEUNG"),
        ("동해시", "DONGHAE"), ("태백시", "TAEBAEK"), ("속초시", "SOKCHO"),
        ("삼척시", "SAMCHEOK"), ("홍천군", "HONGCHEON"), ("횡성군", "HOENGSEONG"),
        ("영월군", "YEONGWOL"), ("평창군", "PYEONGCHANG"), ("정선군", "JEONGSEON"),
        ("철원군", "CHEORWON"), ("화천군", "HWACHEON"), ("양구군", "YANGGU"),
        ("인제군", "INJE"), ("고성군", "GOSEONG"), ("양양군", "YANGYANG"),
    ],
    ("충청북도", False): [
        ("청주시", "CHEONGJU"), ("충주시", "CHUNGJU"), ("제천시", "JECHEON"),
        ("보은군", "BOEUN"), ("옥천군", "OKCHEON"), ("영동군", "YEONGDONG"),
        ("증평군", "JEUNGPYEONG"), ("진천군", "JINCHEON"), ("괴산군", "GOESAN"),
        ("음성군", "EUMSEONG"), ("단양군", "DANYANG"),
    ],
    ("충청남도", False): [
        ("천안시", "CHEONAN"), ("공주시", "GONGJU"), ("보령시", "BORYEONG"),
        ("아산시", "ASAN"), ("서산시", "SEOSAN"), ("논산시", "NONSAN"),
        ("계룡시", "GYERYONG"), ("당진시", "DANGJIN"), ("금산군", "GEUMSAN"),
        ("부여군", "BUYEO"), ("서천군", "SEOCHEON"), ("청양군", "CHEONGYANG"),
        ("홍성군", "HONGSEONG"), ("예산군", "YESAN"), ("태안군", "TAEAN"),
    ],
    ("전북특별자치도", False): [
        ("전주시", "JEONJU"), ("군산시", "GUNSAN"), ("익산시", "IKSAN"),
        ("정읍시", "JEONGEUP"), ("남원시", "NAMWON"), ("김제시", "GIMJE"),
        ("완주군", "WANJU"), ("진안군", "JINAN"), ("무주군", "MUJU"),
        ("장수군", "JANGSU"), ("임실군", "IMSIL"), ("순창군", "SUNCHANG"),
        ("고창군", "GOCHANG"), ("부안군", "BUAN"),
    ],
    ("전라남도", False): [
        ("목포시", "MOKPO"), ("여수시", "YEOSU"), ("순천시", "SUNCHEON"),
        ("나주시", "NAJU"), ("광양시", "GWANGYANG"), ("담양군", "DAMYANG"),
        ("곡성군", "GOKSEONG"), ("구례군", "GURYE"), ("고흥군", "GOHEUNG"),
        ("보성군", "BOSEONG"), ("화순군", "HWASUN"), ("장흥군", "JANGHEUNG"),
        ("강진군", "GANGJIN"), ("해남군", "HAENAM"), ("영암군", "YEONGAM"),
        ("무안군", "MUAN"), ("함평군", "HAMPYEONG"), ("영광군", "YEONGGWANG"),
        ("장성군", "JANGSEONG"), ("완도군", "WANDO"), ("진도군", "JINDO"),
        ("신안군", "SINAN"),
    ],
    ("경상북도", False): [
        ("포항시", "POHANG"), ("경주시", "GYEONGJU"), ("김천시", "GIMCHEON"),
        ("안동시", "ANDONG"), ("구미시", "GUMI"), ("영주시", "YEONGJU"),
        ("영천시", "YEONGCHEON"), ("상주시", "SANGJU"), ("문경시", "MUNGYEONG"),
        ("경산시", "GYEONGSAN"), ("의성군", "UISEONG"), ("청송군", "CHEONGSONG"),
        ("영양군", "YEONGYANG"), ("영덕군", "YEONGDEOK"), ("청도군", "CHEONGDO"),
        ("고령군", "GORYEONG"), ("성주군", "SEONGJU"), ("칠곡군", "CHILGOK"),
        ("예천군", "YECHEON"), ("봉화군", "BONGHWA"), ("울진군", "ULJIN"),
        ("울릉군", "ULLEUNG"),
    ],
    ("경상남도", False): [
        ("창원시", "CHANGWON"), ("진주시", "JINJU"), ("통영시", "TONGYEONG"),
        ("사천시", "SACHEON"), ("김해시", "GIMHAE"), ("밀양시", "MIRYANG"),
        ("거제시", "GEOJE"), ("양산시", "YANGSAN"), ("의령군", "UIRYEONG"),
        ("함안군", "HAMAN"), ("창녕군", "CHANGNYEONG"), ("고성군", "GOSEONG"),
        ("남해군", "NAMHAE"), ("하동군", "HADONG"), ("산청군", "SANCHEONG"),
        ("함양군", "HAMYANG"), ("거창군", "GEOCHANG"), ("합천군", "HAPCHEON"),
    ],
    ("제주특별자치도", False): [("제주시", "JEJU"), ("서귀포시", "SEOGWIPO")],
}

_SIDO_SLUG = {
    _SEOUL: "SEOUL", _GYEONGGI: "GYEONGGI", "인천광역시": "INCHEON",
    "부산광역시": "BUSAN", "대구광역시": "DAEGU", "광주광역시": "GWANGJU",
    "대전광역시": "DAEJEON", "울산광역시": "ULSAN", "세종특별자치시": "SEJONG",
    "강원특별자치도": "GANGWON", "충청북도": "CHUNGBUK", "충청남도": "CHUNGNAM",
    "전북특별자치도": "JEONBUK", "전라남도": "JEONNAM", "경상북도": "GYEONGBUK",
    "경상남도": "GYEONGNAM", "제주특별자치도": "JEJU",
}

# 시도 표시 순서 (UI 그룹 순서)
SIDO_ORDER = [
    _SEOUL, _GYEONGGI, "인천광역시", "부산광역시", "대구광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "강원특별자치도", "충청북도",
    "충청남도", "전북특별자치도", "전라남도", "경상북도", "경상남도", "제주특별자치도",
]


def _build_registry() -> dict[str, Region]:
    reg: dict[str, Region] = {}

    def add(sido: str, name: str, slug: str, capital: bool,
            versions: tuple[RegionVersion, ...]) -> None:
        code = f"{_SIDO_SLUG[sido]}_{slug}"
        if code in reg:
            raise ValueError(f"중복 region_code: {code}")
        reg[code] = Region(code=code, sido=sido, name=name,
                           capital_area=capital, versions=versions)

    for name, slug in _SEOUL_GANGNAM4:
        add(_SEOUL, name, slug, True, _gangnam4_versions())
    for name, slug in _SEOUL_2025:
        add(_SEOUL, name, slug, True,
            _regulated_since(_WIDE_2025, RegulatedType.SPECULATIVE_OVERHEATED, SRC_MOLIT))
    for name, slug in _GYEONGGI_2025:
        add(_GYEONGGI, name, slug, True,
            _regulated_since(_WIDE_2025, RegulatedType.SPECULATIVE_OVERHEATED, SRC_MOLIT))
    for name, slug in _GYEONGGI_SIX_THIRTY:
        add(_GYEONGGI, name, slug, True, _six_thirty_versions())

    for (sido, capital), items in _NON_REGULATED_BY_SIDO.items():
        for name, slug in items:
            add(sido, name, slug, capital, _always_non_regulated())

    return reg


REGISTRY: dict[str, Region] = _build_registry()

# 구(舊) 코드 호환 — 레지스트리 도입 전 저장된 데이터를 깨뜨리지 않기 위함.
ALIASES: dict[str, str] = {
    "GURI": "GYEONGGI_GURI",
    "YONGIN_GIHEUNG": "GYEONGGI_YONGIN_GIHEUNG",
    "HWASEONG_DONGTAN": "GYEONGGI_HWASEONG_DONGTAN",
}


def canonical_code(region_code: str) -> str:
    """구 코드를 현행 코드로 정규화. 알 수 없는 코드는 그대로 돌려준다."""
    return ALIASES.get(region_code, region_code)


def get_region(region_code: str) -> Optional[Region]:
    return REGISTRY.get(canonical_code(region_code))


def resolve_region_status(
    region_code: str, as_of: date
) -> tuple[RegionStatus, RegulatedType]:
    """특정 시점의 지역 규제상태.

    레지스트리에 없는 코드는 **UNKNOWN** 이다. 조용히 비규제로 간주하지 않는다 —
    그 기본값이 규제지역(강남 등)을 70%로 판정하는 사고를 냈다(2026-08-18).
    """
    region = get_region(region_code)
    if region is None:
        return RegionStatus.UNKNOWN, RegulatedType.NONE
    for v in region.versions:
        after_start = v.effective_from is None or as_of >= v.effective_from
        before_end = v.effective_to is None or as_of <= v.effective_to
        if after_start and before_end:
            return v.status, v.regulated_type
    return RegionStatus.UNKNOWN, RegulatedType.NONE


def regulated_codes(as_of: date) -> list[str]:
    """특정 시점에 규제지역인 코드 목록 (원문 지역 수와 대조하는 검증에 쓰인다)."""
    return sorted(
        code for code in REGISTRY
        if resolve_region_status(code, as_of)[0] is RegionStatus.REGULATED
    )


def regions_by_sido() -> list[tuple[str, list[Region]]]:
    """UI 그룹 표시용 — 시도 순서대로 (시도명, 지역목록)."""
    out: list[tuple[str, list[Region]]] = []
    for sido in SIDO_ORDER:
        items = [r for r in REGISTRY.values() if r.sido == sido]
        if items:
            out.append((sido, items))
    return out
