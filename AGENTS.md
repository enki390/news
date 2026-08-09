# NewPaper (뉴스 브리핑 서비스) 에이전트 가이드

## 프로젝트 개요
NewPaper는 주요 언론사의 RSS 피드에서 최신 뉴스를 수집하고, AI(Gemini API)를 활용하여 요약 및 분류한 뒤 GitHub Pages를 통해 실시간/데일리 브리핑을 제공하는 웹 서비스입니다.

## 아키텍처 & 기술 스택
- **Backend / Collector**: Python 3.x (`scripts/collector.py`)
  - RSS 수집: `feedparser`, `beautifulsoup4`
  - AI 요약: `google-genai` (Gemini API)
  - 데이터 저장: `data/` 경로 하위 JSON 파일
- **Frontend**: Vanilla Web Stack (`index.html`, `index.css`, `app.js`)
  - 프레임워크 없는 순수 HTML/CSS/JS (반응형 모던 UI, 다크 모드 지원)
- **CI/CD**: GitHub Actions (`.github/workflows/daily_news.yml`), GitHub Pages

## 주요 개발 규칙 & 지침

### 1. 코드 스타일 & 프레임워크
- **Python**: PEP 8 준수, 예외 처리(Try-Except) 시 무음 예외 처리 금지 및 로깅 명확화.
- **Frontend**: 
  - 외부 Heavy 프레임워크(React, Vue 등) 무단 도입 금지 (Vanilla JS / CSS 유지).
  - UI 변경 시 모던 웹 디자인 트렌드(CSS 변수, 반응형 레이아웃, 다크모드 대응) 준수.
- **데이터 구조**: `data/` 하위 JSON 스키마 변경 시 `collector.py`와 `app.js` 간의 하위 호환성 유지.

### 2. 보안 & 환경 변수
- Gemini API 키 등 비밀 정보는 절대 코드에 하드코딩하지 않으며, `GEMINI_API_KEY` 환경 변수 또는 GitHub Secrets로 관리.

### 3. Git 커밋 메시지 컨벤션
- `feat:` 새로운 기능 추가
- `fix:` 버그 수정
- `docs:` 문서 수정 (AGENTS.md, README.md 등)
- `style:` 코드 포맷팅, CSS/UI 스타일 변경
- `refactor:` 리팩토링 (기능 변경 없음)
- `chore:` 빌드, 액션 설정, 기타 잡무
