# SOURCES — Source Snapshot Store (§6)

> 공식 원문 스냅샷 레지스트리. 원본(`original/`) + 추출 텍스트(`raw/`) + 해시.
> ⚠️ 공개 보도자료/FAQ만 사용 (LOCKED §8). 실제 회사 문서·고객데이터 아님.

| doc_id | 문서명 | 기관 | 발표일 | 원본 | source_hash (sha256) | retrieved_at |
|---|---|---|---|---|---|---|
| FSC_PRESS_20260630 | 규제지역 추가 지정 관련 「긴급 가계부채 점검회의」 개최 (보도참고자료) | 금융위원회 | 2026-06-30 | `original/fsc_press_20260630.pdf` | `403fb8fb…e8f39d23` | 2026-08-10 |
| MOLIT_PRESS_20260630 | 투기과열지구 및 조정대상지역 추가 지정 (보도참고자료) | 국토교통부 | 2026-06-30 | `original/molit_press_20260630.pdf` | `6115271b…66c11edd` | 2026-08-10 |
| FAQ_20260630 | 규제지역 추가 지정 관련 FAQ | 관계기관 합동 | 2026-06-30 | `original/faq_20260630.hwp` | `ef3dad7b…14ea7c9a` | 2026-08-10 |

## 전체 해시 (재현용)
```
403fb8fbf8bb1d68cadc7524d1b6631abe11dd2a4c2f62550c9d2873e8f39d23  fsc_press_20260630.pdf
6115271bf81d487e752ccc1315585018e89ed6c5d4137f7ecca271cb66c11edd  molit_press_20260630.pdf
ef3dad7b55b5781027393f6114fcb656db618962b627535d6a8da3bf14ea7c9a  faq_20260630.hwp
```

## 비고
- **발행기관 공식출처(확정):** 금융위 `www.fsc.go.kr`(보도자료), 국토부 `www.molit.go.kr`(보도자료). FAQ는 두 기관 배포자료 첨부.
- **기사 permalink:** ⬜ 사용자 확인 필요 — 위 게시판에서 문서명으로 검색해 확정. AI가 임의 생성하지 않음(citation integrity). 파일 스냅샷+sha256으로 무결성은 확보.
- 추출 방법: PDF=pymupdf, HWP=olefile+zlib(BodyText 파싱). 추출 텍스트는 `raw/`.
- FAQ 추출은 본문 텍스트 레코드(tag=67)만 → 표 셀은 순서가 원문과 다를 수 있으니 수치는 원본 대조 권장.
