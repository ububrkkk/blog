# 블로그 키워드 분석기 (Naver/Tistory)

수익형 블로그(네이버, 티스토리)에 특화된 키워드 발굴/확장/점수화 CLI 도구입니다. 네이버/구글 자동완성 기반으로 롱테일 키워드를 뽑고, 경쟁/수요를 근사한 ‘기회 점수’를 계산하여 우선순위를 추천합니다. 선택한 키워드에 대해 제목/아웃라인/FAQ 템플릿도 생성합니다. 선택적으로 Naver SearchAd / Naver OpenAPI / Google CSE를 연동해 실제 볼륨/경쟁 신호를 반영할 수 있습니다.

## 주요 기능
- 시드 키워드로부터 네이버/구글 자동완성 확장 (1~2단계)
- 한국어 롱테일 패턴(방법, 후기, 비교, 가격, 추천 등) 자동 부가
- 도메인 프로필 확장(`--profile travel|food`)으로 여행/맛집 특화 키워드 빠른 확장
- 중복/유사 키워드 정규화 및 정리
- 간단한 수요/경쟁 근사치로 `기회 점수` 산출(가중치 조절 가능)
- CSV로 결과 저장, 상위 N개 터미널 표시
- 키워드별 제목/소제목/FAQ 아웃라인 자동생성
- (선택) 네이버 검색광고 API 연동을 위한 훅 제공(환경변수 설정 시 실제 볼륨/입찰가 반영 가능)

## 설치
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## 사용법
- 가장 쉬운 방법(윈도우):
  - GUI 실행(더 쉬움): 탐색기에서 `scripts\run_gui.bat` 더블클릭
    - 또는 PowerShell: `./scripts/run_gui.ps1`
  - Streamlit 웹앱: 탐색기에서 `scripts\run_streamlit.bat` 더블클릭 (브라우저 열림)
    - 또는 PowerShell: `./scripts/run_streamlit.ps1`
  - CLI 한 줄: PowerShell `./scripts/bka.ps1 analyze --seeds "제주 여행" --profile travel --enrich --output results.csv`, CMD `scripts\bka.bat ...`
  - 최초 실행 시 자동으로 가상환경 생성/설치 후 실행합니다.

### 진짜 앱(EXE)처럼 만들기
- 빌드: PowerShell `./scripts/build_exe.ps1` 또는 CMD `scripts\build_exe.bat`
- 실행: `dist\BlogKeywordAnalyzer.exe` 더블클릭 (바탕화면 바로가기 만들기 권장)
- 참고: 최초 빌드 시 PyInstaller가 설치됩니다. 이후 재빌드는 빠릅니다.

## API 키 넣는 방법(.env 권장)
1) 레포 루트에 `.env` 파일 생성 후 아래 형식으로 붙여넣기(샘플: `.env.example` 참고)
```
NAVER_AD_CUSTOMER_ID=your_id
NAVER_AD_API_KEY=your_key
NAVER_AD_SECRET_KEY=your_secret
NAVER_OPENAPI_CLIENT_ID=your_client_id
NAVER_OPENAPI_CLIENT_SECRET=your_client_secret
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_CX=your_cse_cx
```
2) GUI/CLI/EXE 실행 시 자동으로 `.env`를 로드합니다.
3) 보안: `.env`는 이미 `.gitignore`에 포함되어 있어 Git에 올라가지 않습니다.

## 배포(Streamlit Cloud)
1) GitHub에 올리기
   - `git init && git add . && git commit -m "feat: blog keyword analyzer"`
   - GitHub 새 리포 생성 후 `git remote add origin <repo-url>` → `git push -u origin main`
2) 배포
   - 접속: https://share.streamlit.io/deploy (또는 https://streamlit.io/cloud)
   - Pick a repo: 방금 푸시한 GitHub 리포 선택
   - Branch: `main` (또는 사용중인 브랜치)
   - App file path(둘 중 하나 선택):
     - 간편: `streamlit_app.py` (루트의 실행용 shim)
     - 원본: `src/blog_keyword_analyzer/streamlit_platform.py`
   - Python version: 기본값 사용(요구사항은 `requirements.txt`에 명시됨)
3) Secrets 설정(필요 시)
   - Settings -> Secrets에 `.streamlit/secrets.toml.example` 참고해 키를 입력
   - 평문 예시(Flat):
     NAVER_AD_CUSTOMER_ID="..."
     NAVER_AD_API_KEY="..."
     NAVER_AD_SECRET_KEY="..."
     NAVER_OPENAPI_CLIENT_ID="..."
     NAVER_OPENAPI_CLIENT_SECRET="..."
     GOOGLE_API_KEY="..."
     GOOGLE_CSE_CX="..."
   - 또는 [api] 섹션에 중첩으로 입력해도 자동 인식됩니다.
4) Deploy 클릭 → 빌드 완료 후 URL에서 앱 사용

주의
- `.env`는 Cloud에서 사용되지 않으며, Secrets에 키를 넣어야 합니다.
- 네트워크 정책/요청 한도에 따라 Naver/Google 제안이 일시적으로 빈 값일 수 있습니다.

- 기본 분석:
```bash
python -m blog_keyword_analyzer.cli analyze --seeds "제주 여행" "부산 맛집" --providers naver,google --depth 2 --profile travel --limit 300 --enrich --output results.csv
```

### 네이버/티스토리 분리 결과
- CLI에서 플랫폼별 CSV 자동 저장:
  - `--platforms naver,tistory --output results.csv` → `results.naver.csv`, `results.tistory.csv`
- Streamlit에서는 좌측 사이드바에서 플랫폼 선택 → 탭으로 각각 결과/CSV 다운로드 제공
- GUI에서도 플랫폼 체크(네이버/티스토리) 후 실행하면 각 플랫폼별 상위 결과 미리보기와 `...naver.csv`, `...tistory.csv`가 저장됩니다.

- 파일 입력(줄 단위 시드):
```bash
python -m blog_keyword_analyzer.cli analyze --seed-file seeds.txt --providers naver --limit 300
```

- 아웃라인 생성:
```bash
python -m blog_keyword_analyzer.cli outline --keyword "제주 2박3일 여행 코스 추천"
```

## 환경변수(선택: API 연동)
- Naver SearchAd(키워드 도구): `NAVER_AD_CUSTOMER_ID`, `NAVER_AD_API_KEY`, `NAVER_AD_SECRET_KEY`
- Naver OpenAPI(블로그 검색 총량): `NAVER_OPENAPI_CLIENT_ID`, `NAVER_OPENAPI_CLIENT_SECRET`
- Google CSE(검색 총량): `GOOGLE_API_KEY`, `GOOGLE_CSE_CX`
  - 위 값이 유효하면 `--enrich` 시 자동 사용. 상위 N개(`--enrich-limit`)만 조회.

## 개발 가이드
- 소스: `src/` | 테스트: `tests/`
- 스타일: PEP 8 + 타입힌트, 작은 순수 함수 위주
- 테스트: `pytest -q`

## 한계와 안내
- 자동완성/스크래핑은 서비스 정책에 따라 차단될 수 있습니다. 적절한 요청 간격과 사용자 에이전트 설정을 권장합니다.
- 본 도구는 수익을 보장하지 않으며, 키워드 선정과 콘텐츠 품질, 내부/외부 링크, 페이지 체류와 전환 등 운영 역량이 핵심입니다.

## 여행/맛집 프로필 예시
- 여행(`--profile travel`): 일정(2박3일, 3박4일), 루트, 근교/당일치기, 숙소/렌터카, 야경/노을/포토스팟, 성/비수기, 예산/팁 등 자동 확장
- 맛집(`--profile food`): 메뉴/가격/가성비, 예약/웨이팅/영업시간, 분위기/데이트/단체, 브런치/런치/디너, 주차/포장/배달 등 자동 확장
