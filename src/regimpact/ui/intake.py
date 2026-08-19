"""규제 문서 등록 화면 — 새 공문이 파이프라인에 들어오는 입구.

2026-08-19 사용자 리뷰: "새로운 규제나 과거 규제를 업로드하는 화면(기능)이 없다."

정적 배포(GitHub Pages)에는 서버가 없으므로 이 화면이 **정직하게** 할 수 있는 것과
없는 것을 구분한다:

  할 수 있는 것 (전부 실제 동작)
    - 등록된 원문 스냅샷 현황: 파일·SHA-256·레지스트리 대조·문서별 추출 실적
    - 정책 버전 타임라인: 과거 규제가 어떻게 등록돼 있는가 (policy DB 실데이터)
    - 새 문서의 스냅샷 해시 계산: 브라우저 WebCrypto 로 SHA-256 을 실제로 계산한다

  할 수 없는 것 (하는 척하지 않는다)
    - 추출(LLM 필요)과 확정(사람 필요·LOCKED §4)은 정적 페이지에서 실행되지 않는다.
      해시 계산까지 끝나면 다음 단계의 실제 CLI 명령을 안내한다.

수치·해시는 전부 저장소의 실제 파일과 정책 DB에서 계산한다 — 손으로 적지 않는다.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ..extractor.schema import RegChangeExtraction
from ..policy import load_registry
from .theme import card, chip, esc, glance, icon, page, page_title, table

REPO = Path(__file__).resolve().parents[3]
SOURCES_MD = REPO / "docs" / "sources" / "SOURCES.md"
ORIGINAL_DIR = REPO / "docs" / "sources" / "original"

SCENARIO = "문서 스냅샷 · 정책 버전"

_REGISTRY_ROW = re.compile(
    r"^\|\s*(\w+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\d-]+)\s*\|\s*`original/([^`]+)`"
    r"\s*\|\s*`([0-9a-f]{8})…([0-9a-f]{8})`"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_snapshots(extraction: RegChangeExtraction) -> list[dict]:
    """SOURCES.md 레지스트리 + 실제 파일 해시 + 문서별 추출 실적을 묶는다."""
    per_doc: dict[str, int] = {}
    for c in extraction.changes:
        per_doc[c.citation.source_doc_id] = per_doc.get(c.citation.source_doc_id, 0) + 1

    rows = []
    for line in SOURCES_MD.read_text(encoding="utf-8").splitlines():
        m = _REGISTRY_ROW.match(line)
        if not m:
            continue
        doc_id, title, issuer, published, original, h_head, h_tail = \
            (g.strip() for g in m.groups())
        path = ORIGINAL_DIR / original
        digest = _sha256(path) if path.exists() else None
        # 화면의 "레지스트리와 대조된다"는 말을 코드로 강제한다 — 어긋난 채 조용히 배포되지 않는다.
        if digest and not (digest.startswith(h_head) and digest.endswith(h_tail)):
            raise ValueError(
                f"[{doc_id}] 원본 해시가 SOURCES.md 레지스트리와 다르다: "
                f"파일 {digest[:8]}…{digest[-8:]} ≠ 기록 {h_head}…{h_tail}"
            )
        rows.append({
            "doc_id": doc_id,
            "title": title,
            "issuer": issuer,
            "published": published,
            "original": original,
            "sha256": digest,
            "changes": per_doc.get(doc_id, 0),
        })
    return rows


def render(extraction: RegChangeExtraction) -> str:
    snapshots = load_snapshots(extraction)
    registry = load_registry()
    policies = registry.sorted_by_effective()
    confirmed = [p for p in policies if p.status.value == "CONFIRMED"]

    top = glance(
        f"원문 스냅샷 {len(snapshots)}건이 해시로 봉인돼 있고, 정책 버전 {len(policies)}건이 "
        f"시행일 타임라인으로 등록돼 있다. 새 문서는 아래에서 스냅샷 해시를 만들어 등록을 시작한다.",
        [chip(f"원문 스냅샷 {len(snapshots)}건", tone="primary"),
         chip(f"정책 버전 {len(policies)}건 (확정 {len(confirmed)})", tone="good"),
         chip(f"추출된 변경 {len(extraction.changes)}건"),
         chip("실 고객데이터 미사용", tone="neutral")],
    )

    snap_rows = []
    for s in snapshots:
        h = s["sha256"]
        snap_rows.append([
            chip(s["doc_id"], tone="primary", mono=True),
            f'<div class="font-medium max-w-md">{esc(s["title"])}</div>'
            f'<div class="text-body-sm text-on-surface-variant">{esc(s["issuer"])} · {esc(s["published"])}</div>',
            f'<div class="flex flex-col gap-1">{chip(s["original"], mono=True)}'
            + (f'<span class="font-mono-data text-mono-data text-on-surface-variant" '
               f'style="word-break:break-all">{esc(h)}</span>' if h
               else '<span class="text-error text-body-sm">파일 없음</span>')
            + "</div>",
            chip(f"변경 {s['changes']}건 추출" if s["changes"] else "인용 근거로 사용",
                 tone="good" if s["changes"] else "neutral"),
        ])

    pol_rows = []
    for p in policies:
        pol_rows.append([
            chip(p.policy_id, tone="primary", mono=True),
            f'<div class="max-w-md">{esc(p.title)}</div>',
            chip(p.effective_from.isoformat(), mono=True),
            chip("확정" if p.status.value == "CONFIRMED" else "초안(DRAFT)",
                 tone="good" if p.status.value == "CONFIRMED" else "warn"),
        ])

    upload_panel = (
        '<div class="grid grid-cols-2 gap-4" style="align-items:start">'
        # 좌: 실제 동작하는 해시 계산
        '<div class="flex flex-col gap-4">'
        '<label class="flex flex-col gap-2 border border-outline-variant rounded-xl p-5 '
        'bg-surface-container-low" style="cursor:pointer" id="drop">'
        + icon("upload_file", 22)
        + '<span class="font-medium">공문 파일 선택 (PDF · HWP · TXT)</span>'
        '<span class="text-body-sm text-on-surface-variant">'
        "브라우저 안에서만 읽는다 — 어디로도 전송되지 않는다.</span>"
        '<input type="file" id="file" style="position:absolute;opacity:0;width:0;height:0">'
        "</label>"
        '<div class="f-row flex flex-col gap-2">'
        '<label class="flex items-center gap-2 text-body-md">'
        '<input type="radio" name="kind" value="new" checked> 새 규제 (시행 예정·신규 공문)</label>'
        '<label class="flex items-center gap-2 text-body-md">'
        '<input type="radio" name="kind" value="past"> 과거 규제 (소급 등록 — 타임라인 보강)</label>'
        "</div></div>"
        # 우: 결과
        '<div id="out" class="flex flex-col gap-3">'
        '<div class="text-body-sm text-on-surface-variant">파일을 선택하면 '
        "SHA-256 스냅샷 해시가 여기 표시된다.</div></div>"
        "</div>"
    )

    next_steps = (
        '<ol class="steps flex flex-col gap-2" style="list-style:decimal;padding-left:20px">'
        '<li><b>스냅샷</b> — 위에서 계산한 해시를 <code>docs/sources/SOURCES.md</code> 레지스트리에 '
        "기록한다 (원문 위·변조 탐지 기준).</li>"
        "<li><b>추출</b> — LLM이 필요하므로 정적 페이지가 아니라 CLI에서 실행한다:"
        '<pre class="cmd">python examples/run_extractor.py --provider cli --per-document</pre></li>'
        "<li><b>정책 버전 등록</b> — 새 규제든 과거 규제든 항상 DRAFT로 태어난다:"
        '<pre class="cmd">python tools/seed_policies.py   # draft_policy() → confirm()</pre></li>'
        "<li><b>사람 확정</b> — 룰 값 확정은 사람의 일이다(LOCKED §4). "
        "확정 전에는 판정에 쓰이지 않는다.</li></ol>"
    )

    body = (
        page_title(
            "규제 문서 등록",
            "새 공문이 파이프라인에 들어오는 입구 — 스냅샷(해시) → 추출 → 정책 버전 → 사람 확정.",
        )
        + top
        + card("새 문서 등록 — 스냅샷 해시 만들기", upload_panel,
               note="이 정적 데모에서 실제로 실행되는 것은 해시 계산까지다. "
                    "추출(LLM)·확정(사람)은 아래 절차로 이어진다 — 하는 척하지 않는다")
        + card("등록 후 절차", next_steps,
               note="추출·확정을 화면에서 실행하는 척하면 그게 곧 환각이다 — 실제 명령을 안내한다")
        + card(
            f"등록된 원문 스냅샷 ({len(snapshots)}건)",
            table(["doc_id", "문서", "원본 · SHA-256", "추출 실적"], snap_rows),
            note="해시는 빌드 시점에 저장소의 실제 파일에서 계산된다 — 레지스트리와 어긋나면 빌드가 실패한다",
        )
        + card(
            f"정책 버전 타임라인 ({len(policies)}건)",
            table(["policy_id", "정책", "시행일", "상태"], pol_rows),
            note="과거 규제(예: 2016·2017·2025년 지정)는 소급 등록돼 시점 판정의 기준이 된다",
        )
    )

    script = """<script>
const file = document.getElementById("file"), out = document.getElementById("out");
document.getElementById("drop").addEventListener("click", () => file.click());
file.addEventListener("change", async () => {
  const f = file.files[0];
  if (!f) return;
  if (!(crypto && crypto.subtle)) {
    out.textContent = "이 브라우저 컨텍스트에서는 WebCrypto를 쓸 수 없다 — CLI의 sha256sum을 사용하세요.";
    return;
  }
  const kind = document.querySelector('input[name="kind"]:checked').value;
  const buf = await f.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  const hex = [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
  out.innerHTML = "";
  const box = document.createElement("div");
  box.className = "border border-outline-variant rounded-xl p-5 bg-surface-container-lowest flex flex-col gap-2";
  const add = (label, value, mono) => {
    const row = document.createElement("div");
    const l = document.createElement("div");
    l.className = "font-mono-label text-mono-label uppercase text-on-surface-variant";
    l.textContent = label;
    const v = document.createElement("div");
    v.className = mono ? "font-mono-data text-mono-data" : "font-medium";
    v.style.wordBreak = "break-all";
    v.textContent = value;
    row.append(l, v); box.append(row);
  };
  add("파일", f.name + " (" + f.size.toLocaleString() + " bytes)", false);
  add("SHA-256 (스냅샷 해시)", hex, true);
  add("등록 유형", kind === "new" ? "새 규제 — 시행 예정 공문" : "과거 규제 — 타임라인 소급 등록", false);
  add("상태", "스냅샷 준비됨 — 추출·확정은 '등록 후 절차'의 CLI로 진행", false);
  out.append(box);
});
</script>"""

    extra_css = """
.cmd{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12px;line-height:19px;
  background:var(--surface-container);border:1px solid var(--outline-variant);border-radius:4px;
  padding:8px 12px;margin:6px 0 2px;overflow-x:auto;white-space:pre}
.steps li{line-height:24px}
@media (max-width:1023px){main .grid-cols-2{grid-template-columns:minmax(0,1fr)}}
"""

    return page(title="규제 문서 등록", active="sources.html", scenario=SCENARIO,
                status="스냅샷 무결성 확인됨", body=body,
                extra_script=script, extra_css=extra_css)
