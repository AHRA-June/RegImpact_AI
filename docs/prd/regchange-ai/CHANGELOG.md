# CHANGELOG — PRD: RegChange AI

> 최신이 위. 각 항목은 해당 버전 파일(`regchange-ai_vN.md`)의 변경 요약이다.
> 규칙: `docs/features/_VERSIONING.md`.

## v3 (2026-08-13)
- Audit(Logger·event) `⬜ 계획/부분` → `✅ 구현`(해시 체인 감사로그, 변조 탐지) 반영. §5·§6·§10·§13·§15.
  ✅ 완료 목록에 Audit Trail 추가. Risk Register R-GOV-01 잔여 6→3 연동.
- 이전(v2) 대비 상세: `regchange-ai_v3.md` 상단 "변경 이력" 참고.

## v2 (2026-08-13)
- RAG/retrieval `⬜ 계획` → `✅ 구현`(BM25+recall@k+grounding 보존) 반영. §5·§6·§13·§15 갱신.
  ✅ 완료 목록에 무료 LLM 지원·정식 17쪽 서사·Card·Risk Register 추가.
- 이전(v1) 대비 상세: `regchange-ai_v2.md` 상단 "변경 이력" 참고.

## v1 (2026-08-13)
- 최초 작성 (신규). 브리프 §25 필수 항목 구체화 + 현행 구현 상태(구현됨/부분/계획) 명시.
- 포함: 사용자·Use Case, MVP 범위, 아키텍처/파이프라인, 데이터·컴포넌트 스키마 상태표,
  평가 프로토콜(3계층·error taxonomy), Assurance 4 dimension 확정 임계값, Human Review·Audit,
  배포·재현성, 성공 기준, 구현 상태 요약, 리스크, 로드맵.
- 이전 버전 없음.
