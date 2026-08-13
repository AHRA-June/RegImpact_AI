# 기능단위: RAG / Retrieval 층

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). BM25 어휘 검색(순수 stdlib) + 검색 평가(recall@k) + grounding 보존 컨텍스트
  + 임베딩 검색(주입식). 구현: `src/regimpact/retrieval/`.

---

## 1. 목적·책임
규제 원문에서 **근거 문단(passage)을 검색**해 하류 추출(E)에 공급한다(스케일 대비). 이 프로젝트의
원칙대로 검색층도 **평가**한다: 검색이 정답 근거를 놓치면 하류 완전성(Change Completeness·Exception
Recall)이 함께 떨어지므로, **recall@k로 "근거를 놓치지 않는 k"를 고른다.**

## 2. 입력/출력 인터페이스
- `chunk_documents(sources, max_lines=8) -> list[Chunk]` — 원본 doc_id·줄 위치 보존.
- `LexicalRetriever(chunks)` — **BM25, 순수 stdlib·결정론·무료(기본).**
- `EmbeddingRetriever(chunks, embed)` — 임베딩 함수 주입식(무료/로컬 Ollama 등). 순수 파이썬 코사인.
- `retrieve_context(retriever, query, k) -> {doc_id: text}` — **원본 doc_id로 묶어 grounding 체인 보존.**
- `recall_at_k(retriever, gold, k)` / `recall_curve(...)` — 검색 평가.
- `Retriever` Protocol — `retrieve(query, k) -> [(Chunk, score)]`.

## 3. 핵심 로직·설계 결정
- **의존성 0·결정론:** BM25는 표준 라이브러리만. 벡터DB·numpy·API 불필요 → 무료·오프라인·재현 가능.
- **한국어 대응:** 어절 토큰 + 한글 문자 bigram으로 부분 매칭 recall 향상.
- **주입식(Extractor와 동일 철학):** 검색기·임베딩 함수를 교체 가능. 임베딩은 무료 로컬(Ollama)로 주입.
- **grounding 보존:** 검색 결과를 chunk_id가 아니라 **원본 doc_id로 묶어** 반환 → 인용이 원문에 매핑,
  Assurance(citation grounding)가 그대로 작동.
- **검색을 평가:** recall@k. 검색이 하류 Assurance 완전성을 훼손하지 않을 k를 근거로 고른다.

## 4. 관련 파일
- `src/regimpact/retrieval/` — `chunk.py` `lexical.py` `retriever.py` `evaluate.py`
- `tests/test_retrieval.py` · `examples/demo_retrieval.py`
- 리포트: `docs/reports/retrieval_stats.md`

## 5. 검증 상태 (6·30)
- 문서 3건 → 청크 62개. **recall@k = 100%(k=1,3,5,8)** — 골드 근거 문단 전부 회수(작은 코퍼스+강한
  키워드 신호). 검색이 근거를 놓치지 않음을 확인 → 하류 완전성 안전.
- 테스트: `test_retrieval.py`(8) — 청킹 결정론·BM25 랭킹·recall@k·grounding 보존·임베딩 주입. 전체 128 통과.

## 6. 알려진 제약·모호성
- 현 코퍼스는 3건(소규모)이라 검색 없이 전량 주입도 가능 — 검색층은 **스케일 대비 + 평가 프레임워크**.
  recall@k 100%는 소규모·강한 키워드 특성. 대형 코퍼스에서 degradation을 이 지표가 포착한다.
- 임베딩 검색 라이브 실행은 사용자 환경(무료 로컬 Ollama 임베딩 등). 현 검증은 어휘(BM25) 기준.
- 기본 파이프라인(demo_e2e)은 전량 컨텍스트 사용(완전성 우선); 검색은 선택 경로로 제공·평가.
