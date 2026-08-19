# SOURCES — Source Snapshot Store (§6)

> 공식 원문 스냅샷 레지스트리. 원본(`original/`) + 추출 텍스트(`raw/`) + 해시.
> ⚠️ 공개 보도자료/FAQ만 사용 (LOCKED §8). 실제 회사 문서·고객데이터 아님.

| doc_id | 문서명 | 기관 | 발표일 | 원본 | source_hash (sha256) | retrieved_at |
|---|---|---|---|---|---|---|
| FSC_PRESS_20260630 | 규제지역 추가 지정 관련 「긴급 가계부채 점검회의」 개최 (보도참고자료) | 금융위원회 | 2026-06-30 | `original/fsc_press_20260630.pdf` | `403fb8fb…e8f39d23` | 2026-08-10 |
| MOLIT_PRESS_20260630 | 투기과열지구 및 조정대상지역 추가 지정 (보도참고자료) | 국토교통부 | 2026-06-30 | `original/molit_press_20260630.pdf` | `6115271b…66c11edd` | 2026-08-10 |
| FAQ_20260630 | 규제지역 추가 지정 관련 FAQ | 관계기관 합동 | 2026-06-30 | `original/faq_20260630.hwp` | `ef3dad7b…14ea7c9a` | 2026-08-10 |
| FSC_PRESS_20251015 | 주택시장 안정화 대책 이행 관련 「긴급 가계부채 점검회의」 개최 (보도참고자료) | 금융위원회 | 2025-10-15 | `original/fsc_press_20251015.pdf` | `4a7d1f8c…4bc51374` | 2026-08-19 |
| FAQ_20251015 | 대출수요 관리 방안 FAQ | 관계기관 합동 | 2025-10-15 | `original/faq_20251015.pdf` | `26a826fc…e6f24613` | 2026-08-19 |
| MOLIT_PRESS_20200617 | 주택시장 안정을 위한 관리방안 (6·17 대책 보도자료) | 관계부처 합동 | 2020-06-17 | `original/molit_press_20200617.pdf` | `67070527…4b99b04f` | 2026-08-19 |
| QNA_20200617 | 주택시장 안정을 위한 관리방안 외부용 Q&A | 관계부처 합동 | 2020-06-17 | `original/qna_20200617.pdf` | `0eaa30c2…2c82a356` | 2026-08-19 |

## 전체 해시 (재현용)
```
403fb8fbf8bb1d68cadc7524d1b6631abe11dd2a4c2f62550c9d2873e8f39d23  fsc_press_20260630.pdf
6115271bf81d487e752ccc1315585018e89ed6c5d4137f7ecca271cb66c11edd  molit_press_20260630.pdf
ef3dad7b55b5781027393f6114fcb656db618962b627535d6a8da3bf14ea7c9a  faq_20260630.hwp
4a7d1f8c5c90f8b4c2a01669f5d668d127eb9119194905ab27c2134f4bc51374  fsc_press_20251015.pdf
26a826fcaea1dcaecabcc4ee79b991bfa5522cdf15b3a053893c78d0e6f24613  faq_20251015.pdf
67070527922c671c7db7a81750d3a8ae0508f488a9cbe3c7d1e239634b99b04f  molit_press_20200617.pdf
0eaa30c203a4beb82e5756e93acabed9a1a8b084180934efd752f3122c82a356  qna_20200617.pdf
```

## 비고
- **원문 URL:** ⬜ 사용자 확인 필요 (금융위·국토부 보도자료 페이지 링크). 현재는 파일 스냅샷+해시로 무결성 확보.
- 추출 방법: PDF=pymupdf, HWP=olefile+zlib(BodyText 파싱). 추출 텍스트는 `raw/`.
- FAQ 추출은 본문 텍스트 레코드(tag=67)만 → 표 셀은 순서가 원문과 다를 수 있으니 수치는 원본 대조 권장.
