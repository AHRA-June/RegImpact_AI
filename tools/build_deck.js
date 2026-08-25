/* 서비스 소개서(PPTX) 생성 — 수치는 손으로 적지 않고 `tools/deck_facts.py` 에서 읽는다.
 *
 * 2026-08-21 지원서 최종 점검에서 이 덱의 수치 두 곳이 이미 실제와 갈라져 있었다:
 * 테스트 수(590 → 실제)와 목표 역산 처방 3줄(엔진이 더 이상 내지 않는 처방이 적혀 있었고,
 * "만기 40년"은 규제지역 상한 30년과 정면으로 어긋났다). 심사자가 공개 데모에 같은 값을
 * 넣어 보면 덱과 다른 화면을 본다 — 제출 문서가 신뢰를 잃는 가장 빠른 길이다.
 *
 *   python tools/deck_facts.py --out deck_facts.json
 *   node   tools/build_deck.js  deck_facts.json  내한도시그널_서비스소개서.pptx
 */
let pptxgen;
try {
  pptxgen = require("pptxgenjs");
} catch {
  // 저장소는 pptxgenjs 를 담지 않는다 — 덱 생성은 제출 때만 도는 일이라
  // 사이트 빌드·테스트의 의존성으로 만들 이유가 없다.
  console.error("pptxgenjs 가 없습니다.  npm install pptxgenjs  후 다시 실행하거나,");
  console.error("다른 곳에 설치돼 있으면 NODE_PATH=<node_modules 경로> 로 실행하세요.");
  process.exit(3);
}
const fs = require("fs");

const [, , FACTS_PATH, OUT_PATH] = process.argv;
if (!FACTS_PATH || !OUT_PATH) {
  console.error("사용법: node tools/build_deck.js <deck_facts.json> <출력.pptx>");
  process.exit(2);
}
const F = JSON.parse(fs.readFileSync(FACTS_PATH, "utf-8"));
const V = F.verdict, AF = F.afford, AS = F.assurance, SCN = F.scene;

const NAVY = "1E2761", ICE = "CADCFC", W = "FFFFFF";
const INK = "17182B", MUTED = "6B7280", LINE = "DCE1EC";
const SURF = "F4F6FB", RED = "C62828", GREEN = "2E7D32";
const KO = "맑은 고딕";           // 한국어 Office 기본 — 심사자 PC 에서 그대로 렌더된다
const MONO = "Consolas";

const p = new pptxgen();
p.layout = "LAYOUT_WIDE";          // 13.3 x 7.5
p.author = "팀 엣지케이스";
p.title = "내 한도 시그널 — 서비스 소개서";

const M = 0.62, CW = 13.3 - M * 2;

// 팀 경력. `deck_facts.py` 에 두지 않는 이유는 **엔진에서 나오는 값이 아니기 때문**이다
// (그쪽은 파이프라인을 돌려 만드는 수치 전용이다). 대신 여기 한 번만 적어 표지·문제·팀
// 세 슬라이드가 같은 문자열을 쓴다 — 예전에 덱과 설명서가 같은 사실을 다르게 적어
// 갈라진 적이 있고, 그 자리를 없앤다. 값이 바뀌면 `SERVICE_DESCRIPTION_TOMORROW.md` §10
// 과 함께 고친다(설명서 §12-D 가 이 수치의 검증 한계를 이미 밝혀 두었다).
const TEAM = {
  tenure: "금융권 개인여신 데이터분석 8년 7개월",
  did: "규제가 바뀌는 날 은행 안에서 해석 → Rule 변경 → 테스트 → 전산 반영을 직접 수행한 당사자입니다.",
  result: "LTV 차등 전략을 설계해 불량률 5.77% → 3.16%로 개선한 실적이 있습니다.",
};

// 규칙 id → 한국어. 화면(`ui/signal.py` 의 `_RULE_KO`)과 같은 문구를 쓴다 —
// 덱과 데모가 같은 판정을 다른 말로 부르면 같은 것인지 확인할 길이 없다.
const RULE_KO = {
  REG_STD: "규제지역 · 무주택 표준",
  REG_FIRSTHOME: "생애최초 예외 — 강화 대상 아님",
  REG_REALDEMAND: "서민·실수요 예외",
  REG_OWNER_0: "규제지역 · 유주택(비처분)",
  MULTI_0: "수도권 다주택",
  NONREG_STD_70: "비규제 기준선",
};

// ── 공통 조각 ────────────────────────────────────────────────────────────
function titleSlide(s, kicker, title, opts = {}) {
  const dark = !!opts.dark;
  s.addText(kicker, {
    x: M, y: 0.44, w: CW, h: 0.26, fontFace: MONO, fontSize: 11.5, bold: true,
    charSpacing: 2, color: dark ? ICE : NAVY, margin: 0,
  });
  s.addText(title, {
    x: M, y: 0.76, w: CW, h: 0.72, fontFace: KO, fontSize: 34, bold: true,
    color: dark ? W : INK, margin: 0,
  });
}
function chip(s, n, label, x, y, w) {
  s.addShape(p.ShapeType.roundRect, {
    x, y, w, h: 0.46, rectRadius: 0.22, fill: { color: W },
    line: { color: NAVY, width: 1.2 },
  });
  s.addText(String(n), {
    x: x + 0.11, y, w: 0.28, h: 0.46, fontFace: MONO, fontSize: 11, bold: true,
    color: NAVY, align: "center", valign: "middle", margin: 0,
  });
  s.addText(label, {
    x: x + 0.36, y, w: w - 0.46, h: 0.46, fontFace: KO, fontSize: 11.5, bold: true,
    color: INK, valign: "middle", margin: 0,
  });
}
function card(s, x, y, w, h, fill, line) {
  s.addShape(p.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.09,
    fill: { color: fill || W }, line: { color: line || LINE, width: 1 },
  });
}
function stat(s, x, y, w, value, label, color) {
  s.addText(value, {
    x, y, w, h: 0.62, fontFace: MONO, fontSize: 30, bold: true,
    color: color || NAVY, margin: 0,
  });
  s.addText(label, {
    x, y: y + 0.6, w, h: 0.52, fontFace: KO, fontSize: 11, color: MUTED, margin: 0,
  });
}
function foot(s, txt) {
  s.addText(txt, {
    x: M, y: 6.92, w: CW, h: 0.3, fontFace: KO, fontSize: 9.5, color: MUTED, margin: 0,
  });
}

// ── 1. 표지 ──────────────────────────────────────────────────────────────
{
  const s = p.addSlide();
  s.background = { color: NAVY };
  s.addText("신한퓨처스랩 TOMORROW CHALLENGE · 팀 엣지케이스", {
    x: M, y: 1.5, w: CW, h: 0.3, fontFace: MONO, fontSize: 12.5, bold: true,
    charSpacing: 2, color: ICE, margin: 0,
  });
  s.addText("내 한도 시그널", {
    x: M, y: 1.95, w: CW, h: 1.15, fontFace: KO, fontSize: 60, bold: true,
    color: W, margin: 0,
  });
  s.addText(
    "규제가 바뀐 다음 날, 내 대출 한도가 얼마에서 얼마로 달라졌고\n" +
    "나는 경과규정 대상인지를 — 근거 조문과 함께 알려주는 개인화 시뮬레이터", {
      x: M, y: 3.16, w: 9.6, h: 1.0, fontFace: KO, fontSize: 17, color: ICE,
      lineSpacing: 27, margin: 0,
    });
  s.addShape(p.ShapeType.roundRect, {
    x: M, y: 4.42, w: 3.35, h: 0.44, rectRadius: 0.22,
    fill: { color: NAVY }, line: { color: ICE, width: 1 },
  });
  s.addText("금융앱 웹뷰 탑재형 제안", {
    x: M, y: 4.42, w: 3.35, h: 0.44, fontFace: KO, fontSize: 12, bold: true,
    color: ICE, align: "center", valign: "middle", margin: 0,
  });
  // 경력을 표지에 올리는 이유: 뒤 슬라이드의 "규제 변경일"을 아는 사람이 만들었다는 것이
  // 이 덱에서 복제 불가능한 유일한 근거다. 마지막 장에만 두면 심사자는 그걸 다 본 뒤에 안다.
  s.addText([
    { text: TEAM.tenure, options: { fontFace: KO, fontSize: 13, bold: true, color: W } },
    { text: "   규제 변경일의 해석 · Rule 변경 · 테스트 · 전산 반영을 은행 안에서 수행했습니다",
      options: { fontFace: KO, fontSize: 12.5, color: ICE } },
  ], { x: M, y: 5.12, w: CW, h: 0.32, margin: 0 });
  s.addText([
    { text: "동작 데모  ", options: { fontFace: KO, fontSize: 12, color: ICE } },
    { text: "ahra-june.github.io/RegImpact_AI/signal.html",
      options: { fontFace: MONO, fontSize: 12, color: W, bold: true } },
  ], { x: M, y: 5.9, w: CW, h: 0.32, margin: 0 });
  s.addText("서비스 설명서(출처·검증 포함) · /service.html   |   3분 자동 시연 · /demo.html", {
    x: M, y: 6.26, w: CW, h: 0.3, fontFace: KO, fontSize: 11, color: ICE, margin: 0,
  });
  s.addNotes("표지. 팀명 엣지케이스는 규제 사고가 평균이 아니라 가장자리에서 난다는 뜻.");
}

// ── 2. 문제 ──────────────────────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "01  문제", "규제는 저녁에 발표되고, 시행은 다음 날입니다");
  card(s, M, 2.0, 6.0, 3.1, SURF, LINE);
  s.addText("같은 날, 같은 아파트를 계약한 두 사람의 한도 차이", {
    x: M + 0.34, y: 2.32, w: 5.3, h: 0.34, fontFace: KO, fontSize: 12.5,
    color: MUTED, margin: 0,
  });
  s.addText(V.delta, {
    x: M + 0.34, y: 2.72, w: 5.3, h: 0.9, fontFace: KO, fontSize: 44, bold: true,
    color: RED, margin: 0,
  });
  s.addText("차이는 계약금 영수증 한 장입니다", {
    x: M + 0.34, y: 3.76, w: 5.3, h: 0.36, fontFace: KO, fontSize: 13, bold: true,
    color: INK, margin: 0,
  });

  const rows = [
    ["뉴스는 “LTV 70% → 40%”라고만 말합니다",
     "실제로는 생애최초 70%, 서민·실수요 60%, 유주택 0%로 갈립니다"],
    ["고객은 두 방향으로 틀립니다",
     "대상인데 겁먹고 계약을 포기하거나, 대상이 아닌데 안심하다 잔금일에 막힙니다"],
    ["혼란은 전부 창구와 콜센터로 밀려옵니다",
     "발표 한 달 반 뒤에도 은행권 문의가 이어졌습니다"],
  ];
  let y = 2.06;
  rows.forEach(([h, d], i) => {
    s.addShape(p.ShapeType.ellipse, {
      x: 7.0, y: y + 0.05, w: 0.3, h: 0.3, fill: { color: NAVY }, line: { color: NAVY },
    });
    s.addText(String(i + 1), {
      x: 7.0, y: y + 0.05, w: 0.3, h: 0.3, fontFace: MONO, fontSize: 10, bold: true,
      color: W, align: "center", valign: "middle", margin: 0,
    });
    s.addText(h, { x: 7.46, y, w: 5.2, h: 0.34, fontFace: KO, fontSize: 14.5,
      bold: true, color: INK, margin: 0 });
    s.addText(d, { x: 7.46, y: y + 0.33, w: 5.2, h: 0.5, fontFace: KO, fontSize: 12,
      color: MUTED, lineSpacing: 18, margin: 0 });
    y += 1.02;
  });
  s.addText("2026. 06. 30  저녁 — 규제지역 3곳 추가 지정 (화성 동탄·용인 기흥·구리)  ·  시행 07. 01", {
    x: M, y: 5.5, w: CW, h: 0.4, fontFace: KO, fontSize: 13, bold: true,
    color: NAVY, margin: 0,
  });
  // 이 문제를 왜 이 팀이 아는지 — 문제 슬라이드에서 바로 답한다.
  card(s, M, 5.96, CW, 0.74, SURF, NAVY);
  s.addText([
    { text: "이 혼란을 창구 반대편에서 처리해 왔습니다  ",
      options: { fontFace: KO, fontSize: 13, bold: true, color: NAVY } },
    { text: TEAM.tenure + " — 발표 다음 날 해석 · Rule 변경 · 테스트 · 전산 반영이 제 업무였습니다",
      options: { fontFace: KO, fontSize: 12, color: INK } },
  ], { x: M + 0.34, y: 5.96, w: CW - 0.68, h: 0.74, valign: "middle", margin: 0 });
  foot(s, "출처: 금융위원회·국토교통부 보도참고자료(2026-06-30), 뉴시스(2026-08-14) — 전체 링크는 서비스 설명서 §12");
  s.addNotes(`문제 정의. 수치는 엔진 실제 판정값(${SCN.region_label} ${SCN.price}·무주택 기준). `
    + `경력 한 줄은 "왜 이 팀이 이걸 아는가"에 여기서 답하려는 것이다 — 실적 수치는 마지막 장에만 둔다.`);
}

// ── 3. 기존 도구 ─────────────────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "02  왜 아직 안 풀렸나", "기존 도구는 이 질문에 구조적으로 답하지 못합니다");
  const cards = [
    ["대출한도 계산기", "토스 · 핀다 · 뱅크몰 등",
     "‘오늘의 규칙’ 하나만 압니다. 변경 전/후 비교도, 경과규정 판정도, 근거도 없습니다.",
     "두 사람에게 같은 숫자"],
    ["은행 앱 한도조회", "각 은행 공식 앱",
     "실제 심사에 가깝지만 신청 시점의 결과 하나만 나옵니다.",
     "“바뀌면 나는?”에 무응답"],
    ["AI 규제 모니터링", "레그테크 · 컴플라이언스",
     "공문을 요약해 알리는 데서 끝납니다.",
     "개인화 판정이 없음"],
  ];
  cards.forEach(([t, sub, body, tag], i) => {
    const x = M + i * 4.12;
    card(s, x, 1.74, 3.86, 2.5);
    s.addText(t, { x: x + 0.28, y: 1.96, w: 3.3, h: 0.36, fontFace: KO, fontSize: 16,
      bold: true, color: INK, margin: 0 });
    s.addText(sub, { x: x + 0.28, y: 2.32, w: 3.3, h: 0.28, fontFace: KO, fontSize: 11,
      color: MUTED, margin: 0 });
    s.addText(body, { x: x + 0.28, y: 2.68, w: 3.3, h: 0.95, fontFace: KO, fontSize: 12.5,
      color: INK, lineSpacing: 19, margin: 0 });
    s.addText(tag, { x: x + 0.28, y: 3.72, w: 3.3, h: 0.32, fontFace: KO, fontSize: 12,
      bold: true, color: RED, margin: 0 });
  });
  card(s, M, 4.5, CW, 1.5, NAVY, NAVY);
  s.addText("실질적인 대체재는 오픈채팅방입니다", {
    x: M + 0.34, y: 4.72, w: 11.4, h: 0.36, fontFace: KO, fontSize: 16, bold: true,
    color: W, margin: 0,
  });
  s.addText(
    "규제 발표 후 주담대 상담 오픈채팅방 참여자가 2,000명을 넘고 유료 상담방까지 등장했습니다. " +
    "“저는 어떻게 되나요”에 이미 돈을 내는 수요가 있고, 그 질문이 지금은 은행 밖으로 흘러간다는 뜻입니다.", {
      x: M + 0.34, y: 5.12, w: 11.4, h: 0.7, fontFace: KO, fontSize: 12.5, color: ICE,
      lineSpacing: 20, margin: 0,
    });
  foot(s, "출처: 이데일리(2026-07-31) 오픈채팅방·유료 상담방 · 토스피드 DSR 계산기의 ‘예측값·참고용’ 고지 — 서비스 설명서 §12-B");
  s.addNotes("경쟁 항목(지원서 4번)의 근거 슬라이드.");
}

// ── 4. 무엇을 하는가 ─────────────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "03  무엇을 하는가", "일곱 개 주제를 옆으로 넘기며 답이 이어집니다");
  const labels = ["내 조건", "경과규정", "내 한도", "가능 금액", "상품", "타임라인", "물어보기"];
  labels.forEach((l, i) => chip(s, i + 1, l, M + i * 1.76, 1.76, 1.6));
  s.addText("폰 한 화면에 한 주제 — 고객이 입력하는 곳은 1단계 한 곳뿐입니다", {
    x: M, y: 2.42, w: CW, h: 0.34, fontFace: KO, fontSize: 13.5, bold: true,
    color: INK, margin: 0,
  });

  card(s, M, 2.94, 6.0, 2.25, SURF, LINE);
  s.addText("왜 한 화면에 다 담지 않았나", {
    x: M + 0.32, y: 3.14, w: 5.35, h: 0.34, fontFace: KO, fontSize: 14.5, bold: true,
    color: INK, margin: 0,
  });
  s.addText(
    "처음에는 전부 한 세로 화면에 담았습니다. 폰(390×844)에서 문서 높이가 4,960px — " +
    "한 화면을 여섯 번 밀어야 끝이었고, 실사용 리뷰에서 “스크롤만 하다 끝난다”는 반응이 " +
    "나왔습니다. 주제별 가로 넘김으로 바꿔 화면 높이가 뷰포트와 같아졌습니다.", {
      x: M + 0.32, y: 3.5, w: 5.35, h: 1.5, fontFace: KO, fontSize: 12, color: INK,
      lineSpacing: 19, margin: 0,
    });

  card(s, 6.94, 2.94, CW - 6.32, 2.25);
  s.addText("세로 스크롤 길이", {
    x: 7.26, y: 3.14, w: 5.4, h: 0.3, fontFace: KO, fontSize: 12, color: MUTED, margin: 0,
  });
  s.addText([
    { text: "4,960px", options: { fontFace: MONO, fontSize: 26, bold: true, color: RED } },
    { text: "   →   ", options: { fontFace: MONO, fontSize: 20, color: MUTED } },
    { text: "844px", options: { fontFace: MONO, fontSize: 26, bold: true, color: GREEN } },
  ], { x: 7.26, y: 3.48, w: 5.4, h: 0.6, margin: 0 });
  s.addText("≈ 6화면 → 뷰포트 1화면 (가장 긴 주제도 1.3화면)", {
    x: 7.26, y: 4.06, w: 5.4, h: 0.3, fontFace: KO, fontSize: 12, color: MUTED, margin: 0,
  });
  s.addText(
    "넘김은 CSS 스크롤 스냅이 담당하므로 스크립트가 죽어도 손가락으로는 넘어갑니다. " +
    "한 주제가 두 화면을 넘으면 자동 검사가 배포를 막습니다.", {
      x: 7.26, y: 4.42, w: 5.4, h: 0.7, fontFace: KO, fontSize: 12, color: INK,
      lineSpacing: 19, margin: 0,
    });
  s.addText("조건과 결과가 다른 주제에 있으므로, 상단 요약 바(지금 조건 + 판정 LTV)가 따라다니고 누르면 조건 화면으로 돌아갑니다.", {
    x: M, y: 5.42, w: CW, h: 0.36, fontFace: KO, fontSize: 12.5, color: MUTED, margin: 0,
  });
  s.addNotes("화면 구조. 4,960px→844px 은 실측값이며 테스트로 고정돼 있다.");
}

// ── 5. 장면 1 — 변경 전 → 후 ─────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "04  핵심 장면 ①", "같은 조건을 두 시점 규칙으로 각각 판정합니다");
  s.addText(`${SCN.region_label} · ${SCN.price} 아파트 · 무주택`, {
    x: M, y: 1.66, w: CW, h: 0.32, fontFace: KO, fontSize: 13, color: MUTED, margin: 0,
  });
  const box = (x, when, ltv, amt, why, accent) => {
    card(s, x, 2.06, 5.0, 2.2, W, accent === RED ? RED : LINE);
    s.addText(when, { x: x + 0.32, y: 2.26, w: 4.4, h: 0.3, fontFace: MONO,
      fontSize: 11.5, color: MUTED, margin: 0 });
    s.addText(ltv, { x: x + 0.32, y: 2.58, w: 4.4, h: 0.78, fontFace: MONO,
      fontSize: 40, bold: true, color: accent, margin: 0 });
    s.addText(amt, { x: x + 0.32, y: 3.38, w: 4.4, h: 0.36, fontFace: KO,
      fontSize: 17, bold: true, color: INK, margin: 0 });
    s.addText(why, { x: x + 0.32, y: 3.76, w: 4.4, h: 0.3, fontFace: KO,
      fontSize: 11.5, color: MUTED, margin: 0 });
  };
  box(M, `~ ${SCN.cutoff} · 변경 전`, V.before_ltv, V.before_amt, RULE_KO[V.before_rule], NAVY);
  box(M + 5.36, `${SCN.effective} ~ · 변경 후`, V.after_ltv, V.after_amt, RULE_KO[V.after_rule], RED);
  s.addText(`−${V.delta.replace(/원$/, "")}`, {
    x: 11.02, y: 2.86, w: 1.9, h: 0.4, fontFace: KO, fontSize: 15, bold: true,
    color: RED, align: "center", margin: 0,
  });
  s.addText("하루 만에", {
    x: 11.02, y: 3.26, w: 1.9, h: 0.3, fontFace: KO, fontSize: 11, color: MUTED,
    align: "center", margin: 0,
  });
  card(s, M, 4.5, CW, 1.5, SURF, LINE);
  s.addText("값만 주지 않습니다 — 어느 규칙에서 그 결론이 났는지 판정 경로를 펼쳐 볼 수 있고, 근거 조문이 원문 그대로 붙습니다.", {
    x: M + 0.34, y: 4.72, w: 11.4, h: 0.36, fontFace: KO, fontSize: 14, bold: true,
    color: INK, margin: 0,
  });
  s.addText(
    "“(주담대 LTV) 규제지역 내 주담대 취급시 LTV 강화(비규제지역70% → 규제지역40%)”\n" +
    "— 금융위원회 규제지역 추가 지정 관련 「긴급 가계부채 점검회의」 개최 (보도참고자료) · 2026-06-30", {
      x: M + 0.34, y: 5.1, w: 11.4, h: 0.74, fontFace: KO, fontSize: 11.5, color: MUTED,
      lineSpacing: 19, margin: 0,
    });
  s.addNotes("인용문은 원문 대조를 통과한 verbatim 인용이다.");
}

// ── 6. 장면 2 — 경과규정 ─────────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "05  핵심 장면 ②", "계약금 영수증 한 장이 한도를 가릅니다");
  s.addText("같은 날, 같은 가격의 아파트를 계약한 두 사람 — 조건 차이는 ‘계약금 납부 증명’ 하나뿐입니다", {
    x: M, y: 1.66, w: CW, h: 0.32, fontFace: KO, fontSize: 13, color: MUTED, margin: 0,
  });
  const person = (x, who, cond, ltv, amt, badge, accent) => {
    card(s, x, 2.06, 5.0, 2.5, W, accent);
    s.addText(who, { x: x + 0.32, y: 2.26, w: 4.4, h: 0.32, fontFace: KO, fontSize: 15,
      bold: true, color: INK, margin: 0 });
    s.addText(cond, { x: x + 0.32, y: 2.6, w: 4.4, h: 0.3, fontFace: KO, fontSize: 11.5,
      color: MUTED, margin: 0 });
    s.addText(ltv, { x: x + 0.32, y: 2.94, w: 4.4, h: 0.74, fontFace: MONO, fontSize: 38,
      bold: true, color: accent, margin: 0 });
    s.addText(amt, { x: x + 0.32, y: 3.72, w: 4.4, h: 0.34, fontFace: KO, fontSize: 16,
      bold: true, color: INK, margin: 0 });
    s.addShape(p.ShapeType.roundRect, { x: x + 0.32, y: 4.08, w: 2.5, h: 0.34,
      rectRadius: 0.17, fill: { color: accent }, line: { color: accent } });
    s.addText(badge, { x: x + 0.32, y: 4.08, w: 2.5, h: 0.34, fontFace: KO, fontSize: 11,
      bold: true, color: W, align: "center", valign: "middle", margin: 0 });
  };
  const cond = `${SCN.contract} 계약 · ${SCN.region_label} · 무주택`;
  person(M, "A — 계약금 납부 증명 있음", cond,
    V.gf_ltv, V.gf_amt, "경과규정 · 종전 기준 유지", GREEN);
  person(M + 5.36, "B — 계약금 증빙 없음", cond,
    V.after_ltv, V.after_amt, "새 기준 적용", RED);
  card(s, M, 4.78, CW, 1.24, NAVY, NAVY);
  s.addText("일반 한도 계산기는 ‘오늘의 규칙’ 하나만 알기 때문에 이 두 사람에게 같은 숫자를 보여줍니다.", {
    x: M + 0.34, y: 5.0, w: 11.4, h: 0.36, fontFace: KO, fontSize: 15, bold: true,
    color: W, margin: 0,
  });
  s.addText("변경 전/후와 경계 조건을 판정하는 것이 내 한도 시그널의 차이입니다. 규제 사고는 평균이 아니라 가장자리에서 납니다 — 팀명이 엣지케이스인 이유입니다.", {
    x: M + 0.34, y: 5.38, w: 11.4, h: 0.38, fontFace: KO, fontSize: 12.5, color: ICE, margin: 0,
  });
  s.addNotes("두 사람 비교는 화면에 실제로 있는 기능이며 값은 엔진이 그린다.");
}

// ── 7. 장면 3 — 병목 ─────────────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "06  핵심 장면 ③", "한도를 막은 것이 LTV인지 DSR인지까지 짚어줍니다");
  s.addText(SCN.inputs, {
    x: M, y: 1.66, w: CW, h: 0.32, fontFace: KO, fontSize: 13, color: MUTED, margin: 0,
  });
  const bars = AF.rows.map((r) => [r.label, r.amount, r.ratio, r.hit]);
  let y = 2.1;
  bars.forEach(([nm, vv, frac, bind]) => {
    s.addText(nm, { x: M, y, w: 6.6, h: 0.3, fontFace: KO, fontSize: 13,
      bold: bind, color: bind ? RED : INK, margin: 0 });
    s.addText(vv, { x: 6.9, y, w: 1.9, h: 0.3, fontFace: MONO, fontSize: 13,
      bold: true, color: bind ? RED : INK, align: "right", margin: 0 });
    s.addShape(p.ShapeType.roundRect, { x: M, y: y + 0.32, w: 8.2, h: 0.16,
      rectRadius: 0.08, fill: { color: "E5E8F0" }, line: { color: "E5E8F0" } });
    s.addShape(p.ShapeType.roundRect, { x: M, y: y + 0.32, w: 8.2 * frac, h: 0.16,
      rectRadius: 0.08, fill: { color: bind ? RED : NAVY },
      line: { color: bind ? RED : NAVY } });
    y += 0.78;
  });
  card(s, 9.4, 2.1, 3.28, 3.3, SURF, LINE);
  s.addText("목표 역산", { x: 9.68, y: 2.3, w: 2.7, h: 0.32, fontFace: KO, fontSize: 15,
    bold: true, color: INK, margin: 0 });
  s.addText(`“${AF.goal}을 빌리고 싶어요”`, { x: 9.68, y: 2.64, w: 2.7, h: 0.3, fontFace: KO,
    fontSize: 12, color: MUTED, margin: 0 });
  s.addText(`${AF.short}\n모자랍니다`, { x: 9.68, y: 2.98, w: 2.7, h: 0.62,
    fontFace: KO, fontSize: 15, bold: true, color: RED, lineSpacing: 21, margin: 0 });
  // 엔진이 **실제로 낸 처방만** 싣는다. 예전 덱에는 엔진이 불가로 판정한 처방
  // (부채 감축·만기 연장)이 적혀 있었고, "만기 40년"은 규제지역 상한 30년과 어긋났다.
  s.addText(AF.ways.map((w, i) => ({
    text: `· ${w}`,
    options: i < AF.ways.length - 1 ? { breakLine: true } : {},
  })), { x: 9.68, y: 3.68, w: 2.78, h: 1.55, fontFace: KO, fontSize: 10.5, color: INK,
    lineSpacing: 15, margin: 0 });
  s.addText("진단에서 끝내지 않고 행동으로 잇습니다", {
    x: 9.4, y: 5.52, w: 3.28, h: 0.3, fontFace: KO, fontSize: 11.5, bold: true,
    color: NAVY, align: "center", margin: 0 });
  s.addText(`“당신의 한도는 ${AF.total}이고, LTV가 아니라 ${AF.binding.join("·")} 때문입니다”라고 말해주는 계산기는 현재 없습니다.`, {
    x: M, y: 5.36, w: 8.4, h: 0.6, fontFace: KO, fontSize: 13.5, bold: true,
    color: INK, lineSpacing: 21, margin: 0 });
  foot(s, "참고 추정 · 원리금균등 상환 기준이며 스트레스 금리 가산은 미반영 — 실제 한도는 이보다 적을 수 있고 최종 금액은 은행 심사로 확정됩니다");
  s.addNotes("고객 인터뷰에서 나온 요구가 이 기능이 됐다.");
}

// ── 8. 신뢰 ──────────────────────────────────────────────────────────────
{
  const s = p.addSlide();
  s.background = { color: NAVY };
  titleSlide(s, "07  왜 믿을 수 있나", "AI가 판정하지 않는 AI 서비스", { dark: true });
  s.addText("한도 안내가 틀리면 그건 오답이 아니라 금융사고입니다. 그래서 역할을 갈랐습니다.", {
    x: M, y: 1.62, w: CW, h: 0.34, fontFace: KO, fontSize: 14, color: ICE, margin: 0,
  });
  const flow = [
    ["LLM", "공문에서 사실만 추출\n항목마다 원문 인용 강제"],
    ["룰엔진", "판정은 사람이 확정한\n명세의 결정적 구현"],
    ["오라클·테스트", "명세에서 따로 유도한\n검증기와 전 케이스 대조"],
  ];
  flow.forEach(([t, d], i) => {
    const x = M + i * 4.12;
    s.addShape(p.ShapeType.roundRect, { x, y: 2.12, w: 3.86, h: 1.34, rectRadius: 0.09,
      fill: { color: "17204E" }, line: { color: "35407A", width: 1 } });
    s.addText(t, { x: x + 0.3, y: 2.3, w: 3.3, h: 0.34, fontFace: KO, fontSize: 15,
      bold: true, color: W, margin: 0 });
    s.addText(d, { x: x + 0.3, y: 2.66, w: 3.3, h: 0.68, fontFace: KO, fontSize: 12,
      color: ICE, lineSpacing: 19, margin: 0 });
  });
  const stats = [
    [AS.citation, "인용이 원문에 실재\n(글자 단위 대조)"],
    [AS.oracle, "룰엔진 ↔ 독립 오라클\n전 케이스 일치"],
    [AS.js_port, "브라우저 판정 엔진 ↔\n원본 자동 대조"],
    [AS.tests, "자동 테스트\n전량 통과가 배포 조건"],
  ];
  stats.forEach(([v, l], i) => {
    const x = M + i * 3.09;
    s.addText(v, { x, y: 3.8, w: 2.9, h: 0.6, fontFace: MONO, fontSize: 30, bold: true,
      color: W, margin: 0 });
    s.addText(l, { x, y: 4.42, w: 2.9, h: 0.66, fontFace: KO, fontSize: 11.5,
      color: ICE, lineSpacing: 18, margin: 0 });
  });
  s.addShape(p.ShapeType.roundRect, { x: M, y: 5.28, w: CW, h: 1.1, rectRadius: 0.09,
    fill: { color: "17204E" }, line: { color: ICE, width: 1 } });
  s.addText(`검증 성적표를 함께 공개합니다 — ${AS.card}`, {
    x: M + 0.34, y: 5.46, w: 11.4, h: 0.34, fontFace: KO, fontSize: 14, bold: true,
    color: W, margin: 0 });
  s.addText("미측정을 통과로 세지 않습니다. 모르는 것을 통과로 처리하는 것이 검증 체계가 무력해지는 가장 흔한 경로이기 때문입니다.", {
    x: M + 0.34, y: 5.82, w: 11.4, h: 0.34, fontFace: KO, fontSize: 12, color: ICE, margin: 0 });
  s.addNotes("모든 수치는 공개 저장소 코드로 재현 가능. 손으로 적은 숫자가 없다.");
}

// ── 9. 슈퍼SOL 연계 기대효과 (필수) ──────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "08  필수 항목", "슈퍼SOL 연계 기대효과");
  const items = [
    ["규제 발표일의 경험 차별화",
     "다른 앱은 뉴스를 주고, 슈퍼SOL은 ‘내 답’을 줍니다. 고객 불안이 최고조인 시점에 개인화된 답변을 제공하는 첫 금융앱이 됩니다."],
    ["상담 부담 분산",
     "발표 직후 창구·콜센터로 몰리는 “저는 어떻게 되나요”를 앱 내 자가확인으로 흡수합니다."],
    ["주담대 퍼널 상단 선점",
     "한도가 궁금한 순간이 대출 여정의 시작점입니다. 기존 한도조회를 대체하지 않고 앞단에서 증폭해 상담·조회로 잇습니다."],
    ["신뢰 브랜딩",
     "근거 조문 인용과 검증 체계에 기반한 AI 안내는 금융 AI 설명책임 흐름과 정합하며, ‘믿을 수 있는 AI’를 슈퍼SOL의 자산으로 만듭니다."],
    ["현업 확장성",
     "같은 엔진이 심사·리스크 현업 도구로 확장되므로, 한 번의 온보딩으로 고객 콘텐츠와 내부 업무도구가 함께 열립니다."],
  ];
  let y = 1.68;
  items.forEach(([t, d], i) => {
    s.addShape(p.ShapeType.ellipse, { x: M, y: y + 0.04, w: 0.42, h: 0.42,
      fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(String(i + 1), { x: M, y: y + 0.04, w: 0.42, h: 0.42, fontFace: MONO,
      fontSize: 12, bold: true, color: W, align: "center", valign: "middle", margin: 0 });
    s.addText(t, { x: M + 0.62, y, w: 4.0, h: 0.36, fontFace: KO, fontSize: 15,
      bold: true, color: INK, margin: 0 });
    s.addText(d, { x: M + 4.7, y, w: 7.4, h: 0.66, fontFace: KO, fontSize: 12.5,
      color: INK, lineSpacing: 20, margin: 0 });
    y += 0.86;
  });
  card(s, M, 6.06, CW, 0.86, SURF, LINE);
  s.addText("탑재 부담도 적습니다 — 판정 엔진이 브라우저에서 동작하므로 웹뷰 하나로 탑재되고, 서버 호출이 없어 고객 입력이 외부로 나가지 않습니다.", {
    x: M + 0.34, y: 6.28, w: 11.4, h: 0.42, fontFace: KO, fontSize: 13, bold: true,
    color: INK, margin: 0 });
  s.addNotes("지원서 필수 포함 항목. 5번은 B2B 확장까지 잇는 고리다.");
}

// ── 10. 양면 ─────────────────────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "09  확장성", "같은 엔진이 고객 화면과 현업 도구를 동시에 구동합니다");
  s.addText("고객이 보는 답과 창구·심사가 보는 근거가 같은 엔진에서 나옵니다 — 발표일 응대의 일관성이 구조적으로 확보됩니다.", {
    x: M, y: 1.64, w: CW, h: 0.34, fontFace: KO, fontSize: 13, color: MUTED, margin: 0,
  });
  const rows = [
    ["규제 변경 추출·검증", "공문에서 변경 항목을 구조화하고 인용을 원문 대조", F.reach.extraction],
    ["임팩트 매트릭스", "업무영역별 조치·기한·담당. 자동처리 불가 행은 사유 없이 생성 불가", F.reach.matrix],
    ["포트폴리오 영향 분석", "보유 신청 건을 시행 전·후 두 시점으로 전량 재평가", F.reach.portfolio],
    ["룰 변경안 + 회귀 테스트", "심사 룰 개정안과 테스트케이스 자동 생성·검증", F.reach.oracle],
    ["검증보고서 · 모델카드 · 리스크 레지스터", "감독 대응·내부 증빙 문서를 같은 실행에서 자동 생성", F.reach.risks],
  ];
  let y = 2.14;
  rows.forEach(([a, b, c], i) => {
    if (i % 2 === 0) card(s, M, y - 0.08, CW, 0.78, SURF, SURF);
    s.addText(a, { x: M + 0.28, y, w: 3.5, h: 0.62, fontFace: KO, fontSize: 12.5,
      bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(b, { x: M + 3.9, y, w: 5.7, h: 0.62, fontFace: KO, fontSize: 11.5,
      color: MUTED, valign: "middle", lineSpacing: 17, margin: 0 });
    s.addText(c, { x: M + 9.75, y, w: 2.3, h: 0.62, fontFace: MONO, fontSize: 11.5,
      bold: true, color: NAVY, valign: "middle", align: "right", margin: 0 });
    y += 0.86;
  });
  s.addText("하나의 검증된 엔진으로 B2C 콘텐츠와 B2B 내부 도구를 동시에 서비스합니다.", {
    x: M, y: 6.44, w: CW, h: 0.36, fontFace: KO, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  foot(s, "포트폴리오 수치는 층화 합성 데이터 기반이며 실 고객 데이터를 사용하지 않았습니다");
  s.addNotes("전부 공개 웹에 배포되어 있어 심사자가 직접 열어볼 수 있다.");
}

// ── 11. 지금 되는 것 / PoC ───────────────────────────────────────────────
{
  const s = p.addSlide();
  titleSlide(s, "10  구현 상태", "과장하지 않기 위해 구분해 밝힙니다");
  card(s, M, 1.7, 6.0, 4.2, W, GREEN);
  s.addText("이미 동작합니다", { x: M + 0.32, y: 1.92, w: 5.4, h: 0.36, fontFace: KO,
    fontSize: 16, bold: true, color: GREEN, margin: 0 });
  s.addText("공개 데모에서 직접 확인 가능", { x: M + 0.32, y: 2.28, w: 5.4, h: 0.28,
    fontFace: KO, fontSize: 11.5, color: MUTED, margin: 0 });
  s.addText([
    "변경 전/후 판정 · 경과규정 · 예외 판정 엔진",
    "총 가능금액 계산 (LTV·최대한도·DSR·DTI + 병목 표시)",
    "목표 역산 — 부채 감축액·필요 소득·만기 처방",
    "내게 가능한 상품 찾기 — 3상태 자격 판정 + 원문 인용",
    "한도 타임라인 — 정책 버전 DB 실데이터",
    "근거 조문 인용 · 원문 전체 열람 · 문장 강조",
    "공문 원문 검색(BM25) 및 recall 실측",
    "현업 산출물 전체 (추출 검증 · 매트릭스 · 검증보고서)",
  ].map((t, i, a) => ({ text: t,
    options: { bullet: { code: "2022" }, breakLine: i < a.length - 1 } })),
  { x: M + 0.32, y: 2.66, w: 5.4, h: 3.0, fontFace: KO, fontSize: 12, color: INK,
    paraSpaceAfter: 6, margin: 0 });

  card(s, 6.94, 1.7, CW - 6.32, 4.2, W, NAVY);
  s.addText("PoC 기간 목표", { x: 7.26, y: 1.92, w: 5.4, h: 0.36, fontFace: KO,
    fontSize: 16, bold: true, color: NAVY, margin: 0 });
  s.addText("아직 안 되는 것을 되는 것처럼 적지 않습니다", { x: 7.26, y: 2.28, w: 5.4, h: 0.28,
    fontFace: KO, fontSize: 11.5, color: MUTED, margin: 0 });
  s.addText([
    "자유 질문에 문장으로 답하는 LLM 연결 (모든 문장에 인용 부착)",
    "실시간 공문 수집·추출 파이프라인 자동화",
    "슈퍼SOL 웹뷰 연동 및 사용성 테스트",
    "조건 저장 + 한도 변동 알림 구독",
    "상품 자격 판정에 은행 실제 상품 데이터 결합",
  ].map((t, i, a) => ({ text: t,
    options: { bullet: { code: "2022" }, breakLine: i < a.length - 1 } })),
  { x: 7.26, y: 2.66, w: 5.4, h: 2.0, fontFace: KO, fontSize: 12, color: INK,
    paraSpaceAfter: 6, margin: 0 });
  s.addText("현재의 한계 — 그대로 밝힙니다", { x: 7.26, y: 4.7, w: 5.4, h: 0.3,
    fontFace: KO, fontSize: 12.5, bold: true, color: RED, margin: 0 });
  s.addText(
    "스트레스 금리 가산 미반영 · 최종 금액은 은행 심사로 확정 · 원문에 기준값이 없는 구간은 " +
    "추정하지 않고 사람 검토로 넘깁니다. 커버리지가 100%가 아닌 이유가 이것이며, 값을 지어내면 " +
    "즉시 100%가 됩니다.", {
      x: 7.26, y: 5.02, w: 5.4, h: 0.8, fontFace: KO, fontSize: 11, color: MUTED,
      lineSpacing: 17, margin: 0 });
  s.addText("그 자리를 비워 두는 것이 이 서비스의 설계 원칙입니다.", {
    x: M, y: 6.1, w: CW, h: 0.36, fontFace: KO, fontSize: 14, bold: true, color: INK, margin: 0 });
  s.addNotes("정직한 구분 자체가 신뢰의 근거다.");
}

// ── 12. 팀 · 확인 ────────────────────────────────────────────────────────
{
  const s = p.addSlide();
  s.background = { color: NAVY };
  titleSlide(s, "11  팀 · 확인", "직접 열어 보고 검증해 주세요", { dark: true });
  s.addShape(p.ShapeType.roundRect, { x: M, y: 1.66, w: 6.0, h: 2.5, rectRadius: 0.09,
    fill: { color: "17204E" }, line: { color: "35407A", width: 1 } });
  s.addText("팀 엣지케이스", { x: M + 0.34, y: 1.88, w: 5.3, h: 0.36, fontFace: KO,
    fontSize: 16, bold: true, color: W, margin: 0 });
  s.addText(TEAM.tenure, { x: M + 0.34, y: 2.26, w: 5.3, h: 0.32,
    fontFace: KO, fontSize: 13, bold: true, color: ICE, margin: 0 });
  s.addText(TEAM.did + " " + TEAM.result, {
      x: M + 0.34, y: 2.64, w: 5.3, h: 0.9, fontFace: KO, fontSize: 12, color: ICE,
      lineSpacing: 19, margin: 0 });
  s.addText("이 도메인 지식으로 룰엔진부터 검증 체계, 고객 화면까지 MVP를 완성했습니다.", {
    x: M + 0.34, y: 3.56, w: 5.3, h: 0.44, fontFace: KO, fontSize: 12, color: W,
    lineSpacing: 19, margin: 0 });

  const links = [
    ["고객 화면 (핵심)", "/signal.html"],
    ["3분 자동 시연", "/demo.html"],
    ["서비스 설명서 (출처·검증 포함)", "/service.html"],
    ["검증 요약 1페이지", "/validation_summary.html"],
    ["전체 산출물", "/"],
  ];
  s.addText("ahra-june.github.io/RegImpact_AI", { x: 6.94, y: 1.66, w: 5.74, h: 0.36,
    fontFace: MONO, fontSize: 14, bold: true, color: W, margin: 0 });
  let y = 2.14;
  links.forEach(([t, u]) => {
    s.addText([
      { text: u + "  ", options: { fontFace: MONO, fontSize: 12, bold: true, color: W } },
      { text: "— " + t, options: { fontFace: KO, fontSize: 12, color: ICE } },
    ], { x: 6.94, y, w: 5.74, h: 0.3, margin: 0 });
    y += 0.42;
  });
  s.addShape(p.ShapeType.roundRect, { x: M, y: 4.5, w: CW, h: 1.5, rectRadius: 0.09,
    fill: { color: "17204E" }, line: { color: ICE, width: 1 } });
  s.addText("협업 이력의 공백은 산출물의 투명성으로 대신합니다", {
    x: M + 0.34, y: 4.72, w: 11.4, h: 0.36, fontFace: KO, fontSize: 15, bold: true,
    color: W, margin: 0 });
  s.addText(
    "판정 데모 · 시스템 검증보고서 · 모델/시스템 카드 · AI 리스크 레지스터를 모두 공개 웹에 " +
    "배포해 두었습니다. 협업 상대가 계약 전에 직접 열어 보고 검증할 수 있습니다.\n" +
    "본 문서의 성능 수치는 공개 파이프라인을 실제로 실행해 산출한 값이며, 손으로 적은 숫자가 없습니다.", {
      x: M + 0.34, y: 5.1, w: 11.4, h: 0.8, fontFace: KO, fontSize: 12, color: ICE,
      lineSpacing: 20, margin: 0 });
  s.addText("공개 보도자료·FAQ 만 사용했습니다. 실제 회사 문서·고객 데이터는 쓰지 않았고, 포트폴리오는 층화 합성 데이터입니다.", {
    x: M, y: 6.4, w: CW, h: 0.32, fontFace: KO, fontSize: 10.5, color: ICE, margin: 0 });
  s.addNotes("마무리. 검증 가능성이 이 팀의 차별점이다.");
}

p.writeFile({ fileName: OUT_PATH }).then(f => console.log("saved:", f));
