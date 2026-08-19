"""2020 6·17 대책 지역 이관 검수표 생성 — 사람이 확정할 수 있는 형태로 펼친다.

원칙 (골드 검수표와 동일):
  - 매핑 초안은 🤖 — 확정은 ✍️ 사람 (LOCKED §4)
  - 모든 인용은 원문 추출본에서 verbatim 대조 후 실린다 (어긋나면 생성 실패)
  - "全 지역(제외 목록)" 방식의 조정대상지역은 **시군구 열거를 지어내지 않는다** —
    원문에 없는 목록을 만들면 그게 곧 환각이다

원문: docs/sources/original/molit_press_20200617.pdf (p12 지정 표 + 본문 서술 교차 대조)
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.regions import REGION_LABELS  # noqa: E402
from review_theme import FONTS_LINK, REVIEW_CSS, esc  # noqa: E402

RAW = (REPO / "docs/sources/raw/molit_press_20200617.txt").read_text(encoding="utf-8")
NORM = re.sub(r"\s+", " ", RAW)


def q(anchor: str, length: int = 110) -> str:
    """원문에서 anchor로 시작하는 구간을 그대로 잘라 온다 — verbatim 보장."""
    a = re.sub(r"\s+", " ", anchor).strip()
    i = NORM.find(a)
    if i < 0:
        raise SystemExit(f"[anchor 없음] {a!r}")
    return NORM[i:i + max(length, len(a))].strip()


# ---------------------------------------------------------------- 초안 데이터 (🤖)
# 신규 투기과열지구 17곳 — 원문 p12 개선표에서 기존(과천·성남분당·광명·하남) 제외분.
# 본문 서술("경기 10개지역, 인천 3개지역, 대전 4개지역")과 개수 교차 일치 확인됨.
#   status: EXISTING(레지스트리 코드 존재) | NEW(신규 코드 제안) | PARTIAL(부분 지정 — 경계 결정 필요)
SPECULATIVE_NEW = [
    ("성남 수정구",   "SEONGNAM_SUJEONG", "EXISTING", ""),
    ("수원시",       "SUWON_JANGAN + SUWON_PALDAL + SUWON_YEONGTONG (+ 권선구 코드 없음)",
     "PARTIAL", "원문은 '수원' 시 전체 — 레지스트리는 구 단위 3개뿐(권선구 없음). "
                "① 신규 SUWON_GWONSEON 추가 후 4개 구로 등록 ② 시 단위 코드 신설 중 선택"),
    ("안양시",       "ANYANG_DONGAN (+ 만안구 코드 없음)", "PARTIAL",
     "원문은 '안양' 시 전체 — 동안구만 등록돼 있음. 신규 ANYANG_MANAN 제안"),
    ("안산 단원구",   "ANSAN_DANWON (신규)", "NEW", ""),
    ("구리시",       "GURI", "EXISTING", ""),
    ("군포시",       "GUNPO (신규)", "NEW", ""),
    ("의왕시",       "UIWANG", "EXISTING", ""),
    ("용인 수지구",   "YONGIN_SUJI", "EXISTING", ""),
    ("용인 기흥구",   "YONGIN_GIHEUNG", "EXISTING", ""),
    ("화성 (동탄2만)", "HWASEONG_DONGTAN", "PARTIAL",
     "원문은 '동탄2 신도시'만 — 레지스트리 코드는 2026년 행정구 '동탄구'. "
     "경계가 같지 않다(동탄1 포함 여부 등). 부분 지정 표현 방식 결정 필요"),
    ("인천 연수구",   "INCHEON_YEONSU (신규)", "NEW",
     "레지스트리에 INCHEON(시 단위)만 있음 — 강화·옹진 제외 부분 지정이라 구 단위 코드 필요"),
    ("인천 남동구",   "INCHEON_NAMDONG (신규)", "NEW", ""),
    ("인천 서구",     "INCHEON_SEO (신규)", "NEW", ""),
    ("대전 동구",     "DAEJEON_DONG (신규)", "NEW", "대전은 레지스트리에 코드가 전혀 없음"),
    ("대전 중구",     "DAEJEON_JUNG (신규)", "NEW",
     "⚠ 결함 발견: 현행 별칭 테이블이 '대전 중구'를 SEOUL_JUNG(서울 중구)으로 오매핑 — "
     "별칭이 수도권 전제로 만들어져 광역시 동명 구를 구분 못 한다. 확장 시 함께 수정 필요"),
    ("대전 서구",     "DAEJEON_SEO (신규)", "NEW", "'서구'도 인천 서구와 동명 — 같은 문제"),
    ("대전 유성구",   "DAEJEON_YUSEONG (신규)", "NEW", ""),
]

CITES = {
    "table_spec": q("(서울) 全 지역 (경기) 과천, 성남분당·수정, 광명, 하남, 수원, 안양, 안산단원, "
                    "구리, 군포, 의왕, 용인수지·기흥, 화성(동탄2만 지정) (인천) 연수, 남동, 서구 "
                    "(지방) 대구 수성, 세종(행복도시 예정지역만 지정), 대전 동·중·서·유성", 200),
    "body_count": q("➋非규제지역중과열이심각한지역중경기10개지역, 인천 3개지역, 대전4개지역을투기과열지구로지정", 120),
    "effective": q("(적용시기) 6.19(금) 일자로지정및효력발생", 60),
    "adj_all": q("(서울) 全 지역 (경기) 全 지역(일부 지역* 제외)", 80),
    "adj_exclude": q("* 김포, 파주, 연천, 동두천, 포천, 가평, 양평, 여주, 이천, 용인처인", 330),
    "adj_etc": q("(인천) 全 지역(강화·옹진 제외) (지방) 세종(행복도시 예정지역만 지정), 대전, "
                 "청주(동 지역, 오창·오송읍만 지정)", 140),
    "prior_spec": q("(서울) 全 지역 (경기) 과천, 성남분당, 광명, 하남 (지방) 대구 수성", 90),
}

QUESTIONS = [
    ("Q1. 조정대상지역(신규)을 어떻게 기록할 것인가",
     "원문은 시군구 열거가 아니라 \"경기 全 지역(제외 목록)·인천 全 지역(강화·옹진 제외)·대전·"
     "청주(부분)\" 방식이다. 원문에 없는 시군구 목록을 만들어 delta 로 넣으면 열거를 지어내는 것이 된다.",
     ["A. (권고) delta 는 명시 열거된 투기과열 17곳만 등록하고, 조정대상 '全 지역-제외' 서술은 "
      "정책의 범위 노트(rule_note)로 원문 그대로 보존한다",
      "B. 행정구역 목록(외부 자료)으로 시군구를 전개해 delta 등록 — 원문 밖 자료가 필요함을 감수",
      "C. 레지스트리에 이미 있는 지역만 조정대상 delta 로 추가 등록 (부분적 기록)"]),
    ("Q2. 레지스트리를 어디까지 확장할 것인가",
     "신규 코드 제안 8건(안산단원·군포·인천 3·대전 4). 인천·대전은 코어 엔진(수도권 LTV) 스코프 "
     "밖이지만 시점 판정(2020년의 규제 상태)에는 필요하다.",
     ["A. (권고) 17곳 전부 코드 신설 — 시점 판정 커버리지 확보. 동명 구(중구·서구) 별칭 결함도 함께 수정",
      "B. 수도권만 신설(인천 포함, 대전 제외) — 코어 스코프 유지",
      "C. 기존 코드로 매핑 가능한 6곳만 등록"]),
    ("Q3. 해제 이력 없이 확정할 수 있는가",
     "이 문서는 '지정'만 말한다. 이 지역들 다수는 이후 해제됐다가(원문 미보유) 2025년에 재지정됐다 — "
     "해제일 없이 2020 지정을 확정하면 2021~2024 시점 판정이 '계속 규제'로 잘못 나온다.",
     ["A. (권고) 2020 정책은 DRAFT 유지 + 검수 결과를 초안에 반영해 두고, 해제 보도자료(원문) 확보 후 "
      "구간을 닫으면서 함께 확정한다",
      "B. effective_to 미상으로 표시하는 스키마 확장 후 확정",
      "C. 해제 원문 확보 전에는 시점 판정에 쓰지 않는 조건부 확정"]),
]


# ---------------------------------------------------------------- 마크다운
ST_LABEL = {"EXISTING": "기존 코드", "NEW": "신규 코드 제안", "PARTIAL": "부분·경계 결정 필요"}
n_exist = sum(1 for r in SPECULATIVE_NEW if r[2] == "EXISTING")
n_new = sum(1 for r in SPECULATIVE_NEW if r[2] == "NEW")
n_part = sum(1 for r in SPECULATIVE_NEW if r[2] == "PARTIAL")

# 검수 결과 (2026-08-19, 사용자): Q1-A·Q2-A·Q3-A 채택, §1 매핑 전 행 승인.
RESOLVED = ("✅ **검수 완료 (2026-08-19)** — Q1-A(투기과열 17곳만 delta, 조정대상은 rule_note 보존) · "
            "Q2-A(코드 11개 신설 + 동명 구 별칭 시명 한정) · Q3-A(해제 원문 확보까지 DRAFT 유지). "
            "수원·안양 '시 전체'는 구 단위 전개(21개 코드), 반영: `MOLIT_20200617.json` · `regions.py`.")

L = ["# 2020 6·17 대책 지역 이관 검수표 (🤖 초안)", "",
     RESOLVED, "",
     "> 생성: `python tools/build_region_review_2020.py` · 대상: `MOLIT_20200617` (DRAFT) ·",
     "> 원문: `docs/sources/original/molit_press_20200617.pdf` p12 지정표 (본문 서술과 개수 교차 일치)", "",
     f"**신규 투기과열지구 17곳** — 기존 코드 매핑 {n_exist} · 신규 코드 제안 {n_new} · "
     f"부분/경계 결정 필요 {n_part}. 시행일 **2020-06-19** (원문: \"6.19(금) 일자로 지정 및 효력발생\").", "",
     "⚠️ **표 평탄화 주의** — 이 표기는 PDF 텍스트 추출본에서 왔다. FAQ Q2 사고(LTV/DTI 열 뭉개짐)의",
     "전례가 있으므로, 확정 전 원본 PDF p12·p14 를 눈으로 대조하는 것이 확실하다.", "",
     "---", "", "## 0. 먼저 결정할 구조 질문 3개", ""]
for title, why, opts in QUESTIONS:
    L += [f"### {title}", "", why, ""]
    for o in opts:
        L.append(f"- ☐ {o}")
    L.append("")

L += ["---", "", "## 1. 신규 투기과열지구 17곳 — 매핑 초안", "",
      "근거 (원문 p12 개선표, 기존 4곳 제외):", f"> {CITES['table_spec']}", "",
      f"> {CITES['body_count']}", "",
      "| ☐ | 원문 표기 | 매핑 초안 (🤖) | 상태 | 특이사항 |", "|---|---|---|---|---|"]
for name, code, st, note in SPECULATIVE_NEW:
    L.append(f"| ☐ | {name} | `{code}` | {ST_LABEL[st]} | {note or '—'} |")

L += ["", "---", "", "## 2. 조정대상지역(신규) — 열거하지 않고 원문 그대로 보존", "",
      "원문은 \"全 지역 - 제외 목록\" 방식이다. **원문에 없는 시군구 목록을 만들지 않는다** (Q1).", "",
      f"> {CITES['adj_all']}", "", f"> 제외: {CITES['adj_exclude']}", "",
      f"> {CITES['adj_etc']}", "",
      "참고 — 개선 前 (기존) 투기과열지구:", f"> {CITES['prior_spec']}", "",
      "---", "", "## 3. 검수 중 발견된 결함 (매핑과 별개로 수정 필요)", "",
      "- **별칭 테이블의 동명 구 오매핑** — `normalize_region_name('대전 중구')` 이 현재",
      "  `SEOUL_JUNG`(서울 중구)을 돌려준다. 별칭 테이블이 수도권 전제로 만들어져 광역시의",
      "  동명 구(중구·서구)를 구분하지 못한다. 대전·인천 코드를 신설하면(Q2-A) 별칭을",
      "  시·도 한정으로 바꾸지 않는 한 같은 오매핑이 조용히 재발한다.", "",
      "---", "", "## 4. 확정 절차", "",
      "1. Q1~Q3 선택 + §1 표의 매핑 판정 (틀린 행은 정정)",
      "2. 선택에 따라: 레지스트리 코드 신설(별칭 포함) → `MOLIT_20200617` region_deltas 반영",
      "3. Q3-A 라면 정책은 DRAFT 유지 — 해제 원문 확보 시 `confirm()` 으로 확정",
      "4. `python tools/build_region_review_2020.py` 재생성으로 검수 기록화", ""]

out_md = REPO / "docs" / "policies" / "REGION_REVIEW_20200617.md"
out_md.write_text("\n".join(L), encoding="utf-8")
print(f"검수표 생성: {out_md.relative_to(REPO)} ({len(L)}줄)")

# ---------------------------------------------------------------- HTML (같은 데이터에서)
def row_html(name, code, st, note):
    tone = {"EXISTING": "ok", "NEW": "new", "PARTIAL": "part"}[st]
    return (f'<li class="item"><label class="check"><input type="checkbox" class="cb"><span></span></label>'
            f'<div class="body"><div class="head"><span class="claim">{esc(name)}</span>'
            f'<code>{esc(code)}</code><span class="st st-{tone}">{esc(ST_LABEL[st])}</span></div>'
            + (f'<div class="why2">{esc(note)}</div>' if note else "") + "</div></li>")

q_html = ""
for title, why, opts in QUESTIONS:
    q_html += (f'<article class="conflict"><header><span class="id">{esc(title.split(".")[0])}</span>'
               f'<span class="ask" style="font-size:15px">{esc(title.split(". ", 1)[1])}</span></header>'
               f'<p class="why">{esc(why)}</p><fieldset class="verdict"><legend>선택</legend>'
               + "".join(f'<label><input type="radio" name="{esc(title.split(".")[0])}"> {esc(o[3:])}</label>'
                         for o in opts) + "</fieldset></article>")

quotes = "".join(
    f'<figure class="q"><figcaption>MOLIT_PRESS_20200617 · {esc(k)}</figcaption>'
    f'<blockquote>{esc(v)}</blockquote></figure>'
    for k, v in CITES.items())

html = f"""<title>2020 6·17 지역 이관 검수표</title>
{FONTS_LINK}
<style>{REVIEW_CSS}
.st{{font-size:11px;font-weight:600;border-radius:99px;padding:2px 9px}}
.st-ok{{background:var(--secondary);color:#fff}}
.st-new{{background:var(--pend-bg);color:var(--pend-ink);border:1px solid var(--pend)}}
.st-part{{background:var(--alarm-bg);color:var(--alarm-ink)}}
.why2{{font-size:12.5px;line-height:19px;color:var(--on-surface-variant)}}
.verdict{{flex-direction:column;align-items:flex-start}}
</style>
<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:14px">
    <h1>2020 6·17 대책 지역 이관 검수표</h1>
    <div class="note" style="border-left:3px solid var(--ok)"><p>{esc(RESOLVED.replace('**',''))}</p></div>
    <p class="lede">신규 투기과열지구 <strong>17곳</strong>의 레지스트리 매핑 초안(🤖).
    조정대상지역은 원문이 "全 지역-제외" 방식이라 <strong>열거를 지어내지 않고</strong> 원문 그대로 싣는다.
    시행일 2020-06-19. 확정 전 원본 PDF p12·p14 눈 대조 권장(표 평탄화 전례).</p>
    <div class="meta"><span>기존 코드 {n_exist}</span><span>신규 코드 제안 {n_new}</span>
    <span>부분·경계 결정 {n_part}</span><span>대상: MOLIT_20200617 (DRAFT)</span></div>
  </header>
  <section><h2>0. 먼저 결정할 구조 질문</h2>{q_html}</section>
  <section><h2>1. 신규 투기과열지구 17곳 — 매핑 초안</h2>
    <ol class="items">{''.join(row_html(*r) for r in SPECULATIVE_NEW)}</ol></section>
  <section><h2>2. 원문 근거 (verbatim 대조 통과)</h2>{quotes}</section>
  <section><h2>3. 검수 중 발견된 결함</h2>
    <div class="note"><p><b>별칭 테이블의 동명 구 오매핑</b> — <code>normalize_region_name('대전 중구')</code>가
    현재 <code>SEOUL_JUNG</code>(서울 중구)을 돌려준다. 별칭이 수도권 전제라 광역시의 동명 구(중구·서구)를
    구분하지 못한다. 대전·인천 코드 신설 시 별칭을 시·도 한정으로 바꾸지 않으면 같은 오매핑이 재발한다.</p></div></section>
  <footer style="padding-bottom:52px">검수 후 Q1~Q3 선택과 표 판정을 알려주시면 레지스트리·정책 DB에 반영합니다.
  체크 상태는 저장되지 않습니다 — 한 번의 검수 세션용입니다.</footer>
</div>"""

out_html = REPO / "docs" / "policies" / "region_review_20200617.html"
out_html.write_text(html, encoding="utf-8")
print(f"HTML 검수표: {out_html.relative_to(REPO)} ({len(html):,} bytes)")
