# 온라인 테스트 환경 — 배포 가이드

이 프로젝트는 **직접 만져볼 수 있는 온라인 표면 2개**를 갖는다. 성격이 다르니 둘 다 유지한다.

| | Artifact 샌드박스 | 검증보고서 페이지 | Streamlit 검증 콘솔 |
|---|---|---|---|
| 파일 | `web/sandbox.html` | `web/impact.html` | `app/streamlit_app.py` |
| 성격 | 만져보는 **도구** | 읽는 **산출물** | 실물 데모 |
| Vercel | ✅ | ✅ | ❌ (아래 참고) |
| 엔진 | Python 엔진을 **JS로 포팅** | 저장소의 **Python 엔진 그대로** |
| 서버 | 불필요 (정적) | 필요 (Streamlit) |
| LLM(Extractor) | 불가 | 가능 (API 키 필요) |
| 용도 | 링크 하나로 즉시 시연 · 모바일 | 실물 데모 · 지표 산출 · 포트폴리오 URL |

---

## 1. Artifact 샌드박스 (정적)

빌드는 2단계다. **골든 기대값을 사람이 손으로 적지 않는 것**이 핵심이다.

```bash
# 샌드박스 (엔진 JS 포팅본)
python tools/export_fixtures.py     # Python 엔진 실행 → web/fixtures.json
python tools/build_sandbox.py       # 템플릿 + 픽스처 인라인 → web/sandbox.html
node tools/verify_js_port.mjs       # JS 포팅본 ↔ Python 엔진 전 케이스 대조

# 검증보고서 (E2E 결과 — 페이지는 계산하지 않고 싣기만 한다)
python tools/export_impact.py       # E2E 파이프라인 실행 → web/impact.json
python tools/build_impact.py        # 템플릿 + 결과 인라인 → web/impact.html
```

`web/sandbox.html`은 외부 요청이 없는 자체완결 파일이라(웹폰트 제외) Artifact·GitHub Pages·
어떤 정적 호스팅에도 그대로 올라간다.

> **룰 변경 시 반드시**: 엔진을 고쳤으면 위 3개 명령을 다시 돌린다.
> `verify_js_port.mjs`가 실패하면 JS 포팅본이 Python 엔진과 어긋난 것이므로,
> 템플릿의 `룰엔진 JS 포팅` 구간을 맞춰 고친 뒤 다시 빌드한다.

### ⚠️ 정적 호스팅에는 `web/dist/` 를 쓴다 (그냥 `web/*.html` 이 아니다)

`web/sandbox.html` · `web/impact.html` 은 **Artifact 용 조각(fragment)** 이다. Artifact 플랫폼이
게시 시점에 `<!doctype html><head>…</head><body>` 를 씌워 주므로 파일 자체에는 doctype·head 가 없다.

그대로 정적 호스팅하면 **휴대폰에서 깨진다** — `<meta name="viewport">` 가 없어 브라우저가
980px 데스크톱 뷰포트로 렌더한 뒤 축소한다(글씨가 깨알만 해진다). 그래서 별도 빌드가 있다:

```bash
python tools/build_static.py     # 조각 → 온전한 HTML 문서 → web/dist/
```

`web/dist/` 에는 `index.html`(랜딩) · `sandbox.html` · `impact.html` 이 들어간다.
390px 뷰포트에서 가로 스크롤 없이 렌더되는 것을 확인했다.

---

## 2. Vercel 배포 (정적 2종 — 휴대폰용 공개 URL)

**Streamlit 은 Vercel 에 올릴 수 없다.** Streamlit 은 WebSocket 을 유지하는 상주 서버라
서버리스 함수 모델과 맞지 않는다. Vercel 에는 정적 페이지 2종만 올리고, Streamlit 은
Community Cloud 를 쓴다(아래 §3).

저장소 루트의 `vercel.json` 이 이미 설정돼 있다(`outputDirectory: web/dist`, 빌드 스텝 없음).

### 방법 A — GitHub 연동 (권장, 푸시하면 자동 재배포)
1. https://vercel.com → **Add New… → Project**
2. `AHRA-June/RegImpact_AI` 선택 → Import
3. 설정은 건드리지 않는다 — `vercel.json` 이 Framework `Other`, Output Directory `web/dist` 를 지정한다
4. **Deploy** → `https://<프로젝트명>.vercel.app` 발급
5. 브랜치가 `main` 이 아니면 Settings → Git → **Production Branch** 를 배포할 브랜치로 지정

### 방법 B — CLI (1회성)
```bash
npm i -g vercel
vercel login
vercel --prod          # 저장소 루트에서. vercel.json 을 읽는다
```

### 콘텐츠가 바뀌면
정적 페이지는 **빌드 산출물이 커밋되어 있다**(Vercel 에서 Python 을 돌리지 않기 위해).
룰·정책을 고쳤으면 아래를 돌리고 `web/dist/` 까지 함께 커밋해야 배포에 반영된다.

```bash
python tools/export_fixtures.py && python tools/build_sandbox.py
python tools/export_impact.py   && python tools/build_impact.py
python tools/build_static.py
node tools/verify_js_port.mjs          # 커밋 전 필수
```

### GitHub Pages 로 올리려면
`web/dist/` 를 `gh-pages` 브랜치나 `docs/` 경로에 두고 Settings → Pages 에서 소스를 지정한다.
역시 빌드 파이프라인이 필요 없다.

---

## 3. Streamlit 검증 콘솔 (서버 필요)

### 로컬
```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

### Streamlit Community Cloud (무료)

1. https://share.streamlit.io 접속 → GitHub 계정으로 로그인
2. **New app** → 저장소 `AHRA-June/RegImpact_AI` 선택
3. 설정값:
   - **Branch**: `claude/online-testing-plan-8k0xmx` (또는 병합 후 `main`)
   - **Main file path**: `app/streamlit_app.py`
   - **App URL**: 원하는 서브도메인
4. **Advanced settings → Python version**: 3.11 이상
5. **Deploy** 클릭

> 저장소가 비공개면 Streamlit Cloud에 해당 저장소 접근 권한을 승인해야 한다.
> (배포 화면에서 GitHub 권한 재요청 링크가 뜬다.)

### Extractor(LLM) 탭을 켜려면

앱 대시보드 → **Settings → Secrets** 에 아래를 넣는다.

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

키가 없으면 Extractor 탭만 안내 메시지를 띄우고, **나머지 탭(LTV 판정·회귀 콘솔)은 전부 정상 동작**한다.
키를 넣으면 공문 3건에 대해 실제 추출을 돌리고 Citation Correctness · Unsupported Claim Rate ·
Change Completeness · Exception Recall 을 화면에서 산출한다. **호출당 비용이 발생**하므로
버튼을 눌러야만 실행되게 해두었다.

### 대안 호스팅
Vercel 은 불가(상주 서버가 필요하다). Hugging Face Spaces(SDK: streamlit)는 동일하게 동작한다. `requirements.txt`와
`app/streamlit_app.py`를 그대로 쓰고, `app_file: app/streamlit_app.py`를 Space 설정에 지정하면 된다.

---

## 검증

```bash
python -m pytest          # 149개 — 엔진 · 지역 레지스트리 · Extractor · TC · Impact · Streamlit
node tools/verify_js_port.mjs
python examples/demo_impact_e2e.py    # 6·30 E2E 10/11 단계 (LLM 없이)
```

Streamlit 스모크 테스트(`tests/test_streamlit_app.py`)는 AppTest로 앱을 실제 실행해
화면에 뜨는 LTV·상태가 엔진 판정과 일치하는지 확인한다. streamlit 미설치 환경에서는 자동 skip.
