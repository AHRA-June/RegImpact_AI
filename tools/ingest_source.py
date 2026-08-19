"""원문 스냅샷 인제스트 — 문서 등록 화면(sources.html)이 안내하는 절차의 CLI 구현.

    python tools/ingest_source.py --file <pdf> --doc-id FAQ_20251015 \
        --title "대출수요 관리 방안 FAQ" --issuer "관계기관 합동" --published 2025-10-15

하는 일 (전부 결정적):
  1. 원본을 docs/sources/original/<doc_id 소문자>.pdf 로 복사하고 SHA-256 봉인
  2. pymupdf 로 텍스트 추출 → docs/sources/raw/<doc_id 소문자>.txt
     (기존 6·30 스냅샷과 같은 형식 — 페이지마다 "----- pN -----" 마커)
  3. SOURCES.md 레지스트리 표와 재현용 해시 블록에 행 추가

여기까지가 기계의 일이다. 정책 버전 등록(DRAFT)과 확정은 별도 단계(LOCKED §4).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORIGINAL = REPO / "docs" / "sources" / "original"
RAW = REPO / "docs" / "sources" / "raw"
SOURCES_MD = REPO / "docs" / "sources" / "SOURCES.md"


def extract_pdf(path: Path) -> str:
    import pymupdf
    doc = pymupdf.open(path)
    parts = []
    for i, page in enumerate(doc):
        parts.append(f"----- p{i + 1} -----\n{page.get_text()}")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--doc-id", required=True, help="예: FAQ_20251015")
    ap.add_argument("--title", required=True)
    ap.add_argument("--issuer", required=True)
    ap.add_argument("--published", required=True, help="YYYY-MM-DD")
    ap.add_argument("--retrieved", required=True, help="YYYY-MM-DD (입수일)")
    args = ap.parse_args()

    src = Path(args.file)
    if not src.exists():
        sys.exit(f"파일 없음: {src}")
    if src.suffix.lower() != ".pdf":
        sys.exit("현재 이 도구는 PDF 만 다룬다 (HWP 는 기존 스냅샷 절차 참조)")
    if not re.fullmatch(r"[A-Z0-9_]+", args.doc_id):
        sys.exit("doc_id 는 대문자·숫자·언더스코어만")

    base = args.doc_id.lower()
    dst = ORIGINAL / f"{base}.pdf"
    if dst.exists():
        sys.exit(f"이미 등록된 원본: {dst.relative_to(REPO)} — 덮어쓰지 않는다(스냅샷 불변)")
    shutil.copyfile(src, dst)
    digest = hashlib.sha256(dst.read_bytes()).hexdigest()

    raw_path = RAW / f"{base}.txt"
    raw_path.write_text(extract_pdf(dst), encoding="utf-8")

    md = SOURCES_MD.read_text(encoding="utf-8")
    row = (f"| {args.doc_id} | {args.title} | {args.issuer} | {args.published} | "
           f"`original/{base}.pdf` | `{digest[:8]}…{digest[-8:]}` | {args.retrieved} |")
    lines = md.splitlines()
    # 표의 마지막 데이터 행 뒤에 삽입
    last_row = max(i for i, ln in enumerate(lines) if ln.startswith("| ") and "`original/" in ln)
    lines.insert(last_row + 1, row)
    # 재현용 해시 블록에도 추가
    for i, ln in enumerate(lines):
        if ln.strip() == "```" and i > 0 and lines[i - 1].strip().endswith((".pdf", ".hwp")):
            lines.insert(i, f"{digest}  {base}.pdf")
            break
    SOURCES_MD.write_text("\n".join(lines) + ("\n" if not md.endswith("\n") else ""),
                          encoding="utf-8")

    print(f"등록: {args.doc_id}")
    print(f"  원본  {dst.relative_to(REPO)}  sha256={digest[:8]}…{digest[-8:]}")
    print(f"  추출  {raw_path.relative_to(REPO)}  ({len(raw_path.read_text(encoding='utf-8')):,}자)")
    print("  SOURCES.md 갱신 완료 — 다음: sources.py CORPUS_FILES 등록 → 정책 버전(DRAFT) 연결")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
