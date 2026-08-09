# NewPaper (뉴스 브리핑 서비스) 에이전트 가이드

## 프로젝트 개요
NewPaper는 네이버 뉴스 검색 API를 통해 최신 뉴스 데이터를 수집하고, AI(Gemini API)를 활용하여 요약 및 언론사별 보도 방식(보도 시작 및 강조점)을 비교분석한 뒤 GitHub Pages를 통해 실시간/데일리 브리핑을 제공하는 웹 서비스입니다.

## 아키텍처 & 기술 스택
- **Backend / Collector**: Python 3.x (`scripts/collector.py`)
  - 뉴스 수집: 네이버 뉴스 검색 API (`/v1/search/news.json`)
  - AI 요약 & 분석: `google-genai` (Gemini API)
  - 카테고리: `경제`, `글로벌` (2대 핵심 카테고리 한정)
  - 데이터 저장: `data/` 경로 하위 JSON 파일
- **Frontend**: Vanilla Web Stack (`index.html`, `index.css`, `app.js`)
  - 순수 HTML/CSS/JS (반응형 모던 UI, 다크/라이트 테마 지원)
- **CI/CD**: GitHub Actions (`.github/workflows/daily_news.yml`), GitHub Pages

## 주요 개발 규칙 & 지침

### 1. 뉴스 구성 & 스키마 규칙
- **요약**: 수집한 기사를 종합한 전체 요약 (`overview`)
- **랜덤 선택 본문**: 수집된 기사 중 1곳을 랜덤 지정해 해당 기사의 본문 전체 출력 (`featured_article`)
- **보도 비교**: 언론사별 보도 시작 방식(`start_point`) 및 핵심 강조점(`emphasis_point`) 비교
- **원문 링크**: 수집된 각 언론사별 기사 원본 링크 노출

### 2. 보안 & 환경 변수
- 비밀 정보는 코드에 작성하지 않고 환경 변수/GitHub Secrets로 관리합니다.
  - `NAVER_CLIENT_ID`
  - `NAVER_CLIENT_SECRET`
  - `GEMINI_API_KEY`

### 3. Git 커밋 메시지 컨벤션
- `feat:` 새로운 기능 추가
- `fix:` 버그 수정
- `docs:` 문서 수정 (AGENTS.md, README.md 등)
- `style:` 코드 포맷팅, CSS/UI 스타일 변경
- `refactor:` 리팩토링 (기능 변경 없음)
- `chore:` 빌드, 액션 설정, 기타 잡무
