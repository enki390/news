# NewPaper (뉴스 브리핑 서비스) 에이전트 가이드

## 프로젝트 개요
NewPaper는 주요 언론사의 공식 RSS 피드 및 웹 크롤링을 통해 최신 뉴스를 수집하고, 형태소 분석기(Kiwipiepy) 기반의 카테고리 무관 클러스터링을 거친 후 Gemini AI를 활용하여 자연스러운 종합 요약(Humanize 적용) 및 복수 카테고리 태깅을 수행하여 GitHub Pages로 서비스하는 뉴스 큐레이션 웹 애플리케이션입니다.

## 아키텍처 & 기술 스택
- **Backend / Collector**: Python 3.x (`scripts/collector.py`)
  - RSS & 본문 크롤링: `feedparser`, `beautifulsoup4`, `requests` (`scripts/sources/`)
  - 형태소 분석 & 동일 뉴스 클러스터링: `kiwipiepy` (`scripts/processors/clustering.py`)
  - AI 요약 & 복수 카테고리 태깅: `google-genai` (Gemini API) (`scripts/processors/summarizer.py`)
  - 4대 핵심 카테고리: `경제`, `글로벌`, `비즈니스`, `IT/과학`
  - 데이터 저장 & 보존: `data/` 경로 하위 JSON 파일 (기본 30일 보관, `scripts/storage/`)
- **Frontend**: Vanilla Web Stack (`index.html`, `index.css`, `app.js`)
  - 순수 HTML/CSS/JS (반응형 모던 UI, 다크/라이트 테마, 커스텀 캘린더 날짜 선택기)
  - 복수 카테고리 뱃지 렌더링 및 동적 필터링
- **CI/CD**: GitHub Actions (`.github/workflows/daily_news.yml`), GitHub Pages

## 주요 개발 규칙 & 지침

### 1. 뉴스 카테고리 정의
- **4대 지원 카테고리**: `경제`, `글로벌`, `비즈니스`, `IT/과학`
- **복수 카테고리(Multi-Category)**:
  - 하나의 뉴스는 여러 카테고리에 동시에 속할 수 있습니다 (`categories: ["경제", "비즈니스"]`).
  - 클러스터 내 기사들의 출처 카테고리와 AI가 분석한 카테고리를 병합하여 다중 카테고리를 할당합니다.
  - 하위 호환성을 위해 `category` (대표 1차 카테고리) 필드도 동시 유지합니다.

### 2. 동일 뉴스 비교 (클러스터링) 규칙
- **카테고리 무관 비교**: 기사의 수집 출처 카테고리와 상관없이 모든 기사를 상호 비교합니다.
- **Kiwipiepy 형태소 분석**: 기사 제목(`title`)에서 2글자 이상의 일반명사(`NNG`) 및 고유명사(`NNP`)를 추출합니다.
- **판정 기준**: 두 기사 제목의 명사 교집합이 **2개 이상**일 때 동일 이슈로 묶습니다.
- **보도량 랭킹**: 포함된 기사 수가 많은 클러스터 순으로 내림차순 정렬합니다.

### 3. 뉴스 출력 & 요약 규칙
- **출력 개수**: 최대 20개 뉴스 (`MAX_CLUSTERS = 20`) 출력.
- **AI 종합 요약 (`overview`)**: 클러스터 내 본문이 가장 충실한 대표 기사를 기반으로 Gemini AI가 5~10문장 내외의 자연스러운 한국어 종합 요약을 생성합니다 (Humanize 원칙: AI 상투어 금지, 단락 분리).
- **상세 모달 구성**: 복수 카테고리 태그 + 헤드라인 + AI 종합 요약 + 언론사별 원문 링크 목록.

### 4. 보안 & 환경 변수
- Gemini API 키는 코드에 하드코딩하지 않고 `GEMINI_API_KEY` 환경 변수 또는 GitHub Secrets로 관리합니다.

### 5. Git 커밋 메시지 컨벤션
- `feat:` 새로운 기능 추가
- `fix:` 버그 수정
- `docs:` 문서 수정 (AGENTS.md, README.md, docs 등)
- `style:` 코드 포맷팅, CSS/UI 스타일 변경
- `refactor:` 리팩토링 (기능 변경 없음)
- `chore:` 빌드, 액션 설정, 데이터 갱신 등 잡무
