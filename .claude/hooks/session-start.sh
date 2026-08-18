#!/bin/bash
# RegImpact AI — 세션 시작 셋업
#
# 이 저장소는 런타임 의존성이 없다(표준 라이브러리만 사용). 무과금 실행 경로도 마찬가지다.
# 따라서 여기서 하는 일은 사실상 하나뿐이다: **테스트를 돌릴 수 있게 만드는 것.**
# pytest가 없으면 새 세션의 첫 명령(`python -m pytest -q`)부터 막힌다.
set -euo pipefail

# 웹(원격) 세션에서만 실행 — 로컬 개발자의 환경을 건드리지 않는다.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

# editable 설치로 `import regimpact`가 어디서든 되게 한다(examples의 sys.path 조작과 무관하게).
# 이미 설치돼 있어도 안전하다.
python -m pip install --quiet --disable-pip-version-check -e ".[dev]"

echo "RegImpact AI 셋업 완료 — python -m pytest -q 로 확인하세요"
