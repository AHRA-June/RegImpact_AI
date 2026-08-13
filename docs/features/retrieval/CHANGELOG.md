# CHANGELOG — RAG / Retrieval 층

> 최신이 위. 각 항목은 해당 버전 파일(`retrieval_vN.md`)의 변경 요약이다.

## v1 (2026-08-13)
- 최초 작성 (신규). 기능단위 문서화 시작.
- 대상 구현: BM25 어휘 검색(순수 stdlib·결정론·무료), 청킹(원본 doc_id 보존), 검색 평가(recall@k),
  grounding 보존 컨텍스트(retrieve_context), 임베딩 검색(주입식). 6·30 recall@k 100%. 테스트 8건(총 128).
- 이전 버전 없음.
